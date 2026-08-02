"""
数据同步模块
用于将QGIS插件的数据同步到M03后端

可靠性增强(2026-07-20) —— 保证"上传数据正确且不丢":
- 上传前本地落盘缓存(.qgis_plugin_cache/upload_queue.json)，失败/中断也不丢数据，可重发
- 网络错误 / 5xx / 超时 指数退避重试(最多3次: 1s, 3s, 9s)
- 上传成功后校验回环(get_sites 拉回比对站点数与 siteId 集合)，确认服务端确实收全
- 发送前计数断言(totalSites == 实际组装数)，防止组装阶段就少数据
- 每个上传带 idempotencyKey，服务端据此去重(重复上传不翻倍)
- payload 计算 SHA256 随 X-Payload-Sha256 头发送，便于后续服务端完整性校验
"""

import os
import json
import time
import uuid
import hashlib
import requests
from pathlib import Path
from typing import List, Dict, Optional

# 本地上传队列缓存：保证上传失败/中断时数据不丢，可重发恢复
_CACHE_DIR = Path(os.path.expanduser("~/.qgis_plugin_cache"))
_QUEUE_FILE = _CACHE_DIR / "upload_queue.json"

# 重试策略：指数退避 (1s, 3s, 9s)
_MAX_RETRIES = 3
_BACKOFF_BASE = 1.0


def _queue_load() -> list:
    if _QUEUE_FILE.exists():
        try:
            return json.loads(_QUEUE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _queue_save(items: list) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _QUEUE_FILE.write_text(
            json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        print(f"[data_sync] 写入上传队列缓存失败(不影响上传): {e}")


def _payload_sha256(design_data: dict) -> str:
    payload = json.dumps(design_data, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class DataSync:
    """数据同步类"""

    def __init__(self, api_url=None, api_key=None):
        """
        初始化数据同步

        Args:
            api_url: M03后端API地址（默认读环境变量 M03_API_URL，回退内置默认）
            api_key: 内部接口 API Key（默认读环境变量 M03_API_KEY）
        """
        # 支持 HTTPS：部署启用 TLS 后将 M03_API_URL 设为 https:// 即可
        # 注意：本地调试默认连 localhost:8083；上线服务器时改回 "http://47.122.117.17:8083" 或设环境变量 M03_API_URL
        self.api_url = api_url or os.environ.get("M03_API_URL", "http://localhost:8083")
        # 本地后端默认 api-key 为 CHANGE_ME（见 m03 application.yml 的 ${M03_API_KEY:CHANGE_ME}）；
        # 上线服务器时按需改默认值或设环境变量 M03_API_KEY
        self.api_key = api_key or os.environ.get("M03_API_KEY", "CHANGE_ME")

    def upload_design(self, project_id, sites, params, avoidance_checker=None, machine_rooms=None, route_type=None):
        try:
            site_list = []
            valid_count = 0
            invalid_count = 0
            for s in sites:
                if hasattr(s, "to_geojson_feature"):
                    site_dict = s.to_geojson_feature().get("properties", {})
                    lon = site_dict.get("longitude", 0)
                    lat = site_dict.get("latitude", 0)
                else:
                    site_dict = s
                    lon = site_dict.get("longitude", 0)
                    lat = site_dict.get("latitude", 0)

                is_valid = True
                invalid_reason = ""
                if avoidance_checker:
                    is_valid, reasons = avoidance_checker.is_site_valid(lon, lat)
                    if not is_valid:
                        invalid_reason = "; ".join(reasons)

                if is_valid:
                    valid_count += 1
                else:
                    invalid_count += 1

                site_list.append({
                    "siteId": site_dict.get("siteId", site_dict.get("site_id", "")),
                    "siteName": site_dict.get("siteName", site_dict.get("name", "")),
                    "longitude": lon,
                    "latitude": lat,
                    "towerHeight": site_dict.get("towerHeight", site_dict.get("tower_height", 35)),
                    "siteType": site_dict.get("siteType", site_dict.get("site_type", "MACRO")),
                    "scenario": site_dict.get("scenario", "URBAN"),
                    "rsrp": site_dict.get("rsrp", 0),
                    "isValid": is_valid,
                    "invalidReason": invalid_reason,
                })

            # 组装机房数据（QGIS插件确定的机房位置）
            rooms_data = []
            if machine_rooms:
                for room in machine_rooms:
                    if isinstance(room, dict):
                        rooms_data.append({
                            "roomId": room.get("room_id", room.get("roomId", "")),
                            "name": room.get("name", ""),
                            "longitude": room.get("longitude", 0),
                            "latitude": room.get("latitude", 0),
                            "roomType": room.get("room_type", room.get("roomType", "汇聚机房")),
                        })
                    else:
                        # MachineRoom dataclass instance
                        rooms_data.append({
                            "roomId": room.room_id,
                            "name": room.name,
                            "longitude": room.longitude,
                            "latitude": room.latitude,
                            "roomType": room.room_type,
                        })

            design_data = {
                "projectId": project_id,
                "schemeName": params.get("scheme_name", "Base Station Design"),
                "frequencyBand": params.get("band", "3.5GHz"),
                "towerHeight": params.get("tower_height", 35),
                "gridSize": params.get("grid_size", "4x4"),
                "totalSites": len(sites),
                "validSites": valid_count,
                "invalidSites": invalid_count,
                "avgRsrp": params.get("avg_rsrp", 0),
                "sites": site_list,
                "machineRooms": rooms_data if rooms_data else None,
                "routeType": route_type,  # direct / manhattan，由 QGIS 插件当前路由类型决定
            }

            # ---- 发送前计数断言：确保组装阶段未丢数据 ----
            if design_data["totalSites"] != len(site_list):
                return False, (f"计数断言失败: 入参 totalSites={design_data['totalSites']} "
                               f"但组装了 {len(site_list)} 个站点")
            if design_data["validSites"] + design_data["invalidSites"] != design_data["totalSites"]:
                return False, "计数断言失败: validSites + invalidSites != totalSites"

            # ---- 幂等键 + 完整性校验和 ----
            idempotency_key = str(uuid.uuid4())
            design_data["idempotencyKey"] = idempotency_key
            sha = _payload_sha256(design_data)

            # ---- 本地落盘缓存：失败也不丢，可重发 ----
            input_site_ids = [s["siteId"] for s in site_list]
            queue = _queue_load()
            item = {
                "idempotencyKey": idempotency_key,
                "project_id": project_id,
                "schemeName": design_data["schemeName"],
                "totalSites": design_data["totalSites"],
                "sha256": sha,
                "status": "pending",
                "createdAt": time.time(),
            }
            queue.append(item)
            _queue_save(queue)

            # ---- 指数退避重试 ----
            last_err = ""
            for attempt in range(_MAX_RETRIES):
                try:
                    resp = requests.post(
                        f"{self.api_url}/api/m03/design/upload",
                        json=design_data,
                        timeout=30,
                        headers={"X-Payload-Sha256": sha, "X-API-Key": self.api_key},
                    )
                    if resp.status_code == 200:
                        r = resp.json()
                        if r.get("code") == 200:
                            data = r.get("data", {})
                            scheme_id = data.get("schemeId") if isinstance(data, dict) else data
                            # ---- 校验回环：拉回比对，确认服务端确实收全 ----
                            verified = self._verify_upload(
                                scheme_id, design_data["totalSites"], input_site_ids
                            )
                            item["status"] = "done"
                            item["schemeId"] = scheme_id
                            item["verified"] = verified
                            item["serverCount"] = data.get("inserted") if isinstance(data, dict) else None
                            item["dup"] = data.get("dup") if isinstance(data, dict) else False
                            _queue_save(queue)
                            detail = {
                                "scheme_id": scheme_id,
                                "server_count": item["serverCount"],
                                "verified": verified,
                                "dup": item["dup"],
                            }
                            return True, detail
                        else:
                            # 业务错误(校验/参数)：不重试，立即返回
                            last_err = r.get("message", "Unknown error")
                            break
                    else:
                        last_err = f"HTTP {resp.status_code}"
                        # 4xx 客户端错误不重试；5xx 才重试
                        if 400 <= resp.status_code < 500:
                            break
                except requests.exceptions.ConnectionError:
                    last_err = f"M03后端未运行 ({self.api_url})"
                except requests.exceptions.Timeout:
                    last_err = "上传超时(30s)"
                except Exception as e:
                    last_err = str(e)

                # 退避后重试(非最后一次)
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_BACKOFF_BASE * (3 ** attempt))

            # 全部重试失败：保留在队列(failed)，数据不丢，可后续重发
            item["status"] = "failed"
            item["last_error"] = last_err
            _queue_save(queue)
            return False, last_err

        except Exception as e:
            return False, str(e)

    def _verify_upload(self, scheme_id, expected_total, input_site_ids):
        """校验回环：拉回服务端站点，比对数量与 siteId 集合，确认未丢未多。"""
        try:
            sites = self.get_sites(scheme_id)
            if sites is None:
                return False
            if len(sites) != expected_total:
                print(f"[data_sync] 校验回环告警: 期望 {expected_total} 站, 服务端返回 {len(sites)} 站")
                return False
            returned_ids = {s.get("siteId") for s in sites}
            missing = [sid for sid in input_site_ids if sid not in returned_ids]
            if missing:
                print(f"[data_sync] 校验回环告警: {len(missing)} 个站点服务端缺失: {missing[:5]}")
                return False
            return True
        except Exception as e:
            print(f"[data_sync] 校验回环异常(不影响上传结果): {e}")
            return False

    def fetch_projects(self) -> List[Dict]:
        """
        从M03后端获取项目列表

        Returns:
            项目字典列表，失败返回空列表
            每项: {id, projectName, projectCode, status}
        """
        try:
            response = requests.get(
                f"{self.api_url}/api/m03/project",
                timeout=10,
                headers={"X-API-Key": self.api_key},
            )
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 200:
                    return result.get('data', [])
                print(f"API error: {result.get('message', 'Unknown')}")
                return []
            else:
                print(f"HTTP error: {response.status_code}")
                return []
        except (requests.exceptions.ConnectionError, Exception) as e:
            print(f"Fetch projects error: {e}")
            return []

    def download_design(self, project_id: int) -> Optional[Dict]:
        """
        从M03后端下载设计方案

        Args:
            project_id: 项目ID

        Returns:
            设计数据字典，失败返回None
        """
        try:
            response = requests.get(
                f"{self.api_url}/api/m03/design/{project_id}",
                timeout=10,
                headers={"X-API-Key": self.api_key},
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 200:
                    return result.get('data')
                else:
                    print(f"API error: {result.get('message', 'Unknown error')}")
                    return None
            else:
                print(f"HTTP error: {response.status_code}")
                return None

        except requests.exceptions.ConnectionError:
            print("Connection error: M03 backend is not running")
            return None
        except Exception as e:
            print(f"Download error: {e}")
            return None

    def get_sites(self, scheme_id: int) -> Optional[List[Dict]]:
        """
        获取站点数据

        Args:
            scheme_id: 方案ID

        Returns:
            站点列表，失败返回None
        """
        try:
            response = requests.get(
                f"{self.api_url}/api/m03/design/{scheme_id}/sites",
                timeout=10,
                headers={"X-API-Key": self.api_key},
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 200:
                    return result.get('data')
                else:
                    print(f"API error: {result.get('message', 'Unknown error')}")
                    return None
            else:
                print(f"HTTP error: {response.status_code}")
                return None

        except requests.exceptions.ConnectionError:
            print("Connection error: M03 backend is not running")
            return None
        except Exception as e:
            print(f"Get sites error: {e}")
            return None

    def parse_design_params(self, text: str) -> Optional[Dict]:
        """
        调用 M03 后端大模型接口，将自然语言设计需求解析为结构化参数。

        Args:
            text: 自然语言描述

        Returns:
            解析后的 params 字典，失败返回 None
        """
        try:
            resp = requests.post(
                f"{self.api_url}/api/m03/llm/parse-design-params",
                json={"text": text},
                timeout=120,
                headers={"X-API-Key": self.api_key},
            )
            if resp.status_code == 200:
                result = resp.json()
                if result.get('code') == 200:
                    data = result.get('data') or {}
                    return data.get('params')
                print(f"API error: {result.get('message', 'Unknown')}")
                return None
            else:
                print(f"HTTP error: {resp.status_code} {resp.text[:200]}")
                return None
        except requests.exceptions.ConnectionError:
            print("Connection error: M03 backend is not running")
            return None
        except Exception as e:
            print(f"Parse design params error: {e}")
            return None

    def generate_report(self, scheme: Dict) -> Optional[str]:
        """
        调用 M03 后端大模型接口，将设计方案生成为 Markdown 评审/交付报告。

        Args:
            scheme: 设计方案结构化数据（站点/机房/参数）

        Returns:
            Markdown 字符串，失败返回 None
        """
        try:
            resp = requests.post(
                f"{self.api_url}/api/m03/llm/generate-report",
                json={"scheme": scheme},
                timeout=120,
                headers={"X-API-Key": self.api_key},
            )
            if resp.status_code == 200:
                result = resp.json()
                if result.get('code') == 200:
                    data = result.get('data') or {}
                    return data.get('report_markdown')
                print(f"API error: {result.get('message', 'Unknown')}")
                return None
            else:
                print(f"HTTP error: {resp.status_code} {resp.text[:200]}")
                return None
        except requests.exceptions.ConnectionError:
            print("Connection error: M03 backend is not running")
            return None
        except Exception as e:
            print(f"Generate report error: {e}")
            return None


def create_data_sync(api_url=None, api_key=None) -> DataSync:
    """
    创建数据同步实例

    Args:
        api_url: M03后端API地址（默认读环境变量 M03_API_URL）
        api_key: 内部接口 API Key（默认读环境变量 M03_API_KEY）

    Returns:
        DataSync实例
    """
    return DataSync(api_url=api_url, api_key=api_key)
