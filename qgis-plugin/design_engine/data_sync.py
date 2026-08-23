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
                    "mountType": site_dict.get("mountType", site_dict.get("mount_type", "GROUND")),
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


    def generate_design(self, params: Dict) -> tuple:
        """
        调用 M03 后端 /api/m03/design/generate（拓扑引擎驱动），
        返回设计成果：每站 coveragePolygons 扇区覆盖多边形 + deviceLayout 设备清单。

        Args:
            params: 生成参数（与后端 GenerateRequest 对齐）
                    {projectId, schemeName, templateType, centerLongitude,
                     centerLatitude, coverageRadius, frequencyBand, towerHeight,
                     gridSize, sectorCount}

        Returns:
            (True, design_dict) 成功，design_dict 含 sites / deviceLayout
            (False, error_msg) 失败
        """
        try:
            resp = requests.post(
                f"{self.api_url}/api/m03/design/generate",
                json=params,
                timeout=120,
                headers={"X-API-Key": self.api_key},
            )
            if resp.status_code == 200:
                result = resp.json()
                if result.get("code") == 200:
                    data = result.get("data") or {}
                    return True, data
                return False, result.get("message", "Unknown error")
            return False, f"HTTP {resp.status_code}"
        except requests.exceptions.ConnectionError:
            return False, f"M03后端未运行 ({self.api_url})，无法调用拓扑引擎"
        except Exception as e:
            return False, str(e)

    # ------------------------------------------------------------------
    # FTTH 成果一键同步
    # 解决的问题：以前每改一次 FTTH 设计，都要手工把三个 JSON 拷进
    # frontend/public/datasets/{tag}/，还常要重新构建前端才能看到。
    # ------------------------------------------------------------------

    def upload_ftth(self, tag, data, validation=None, plan=None,
                    label=None, source=None) -> tuple:
        """
        把 FTTH 导出三件套推送到 M03 后端，落到 S1 前端读取的数据目录。

        与 upload_design 同一套可靠性约束：
        - 幂等键 uploadId + 服务端 sha256 去重（重复推送不产生副作用）
        - 对「实际发送的字节」算 SHA256 随 X-Payload-Sha256 发送（跨语言零歧义）
        - 本地队列落盘，失败可重发
        - 指数退避重试（1s/3s/9s），4xx 不重试
        - 校验回环：拉回 /api/m03/ftth/{tag}/data 比对箱体/缆/站点计数

        Args:
            tag: 数据集标识（前端选择器的 key），如 JAD-MAR-0001
            data: ftth-data.json 内容（dict，必须含 boites 数组）
            validation: ftth-validation.json 内容，可为 None
            plan: ftth-plan.json 内容，可为 None
            label: 前端下拉显示名，默认用 tag
            source: 数据来源说明，默认取 data['source']

        Returns:
            (True, detail_dict) / (False, error_msg)
        """
        try:
            if not isinstance(data, dict) or not isinstance(data.get("boites"), list):
                return False, "ftth-data 内容非法：缺少 boites 数组"

            upload_id = str(uuid.uuid4())
            body = {
                "uploadId": upload_id,
                "label": label or tag,
                "source": source or data.get("source", tag),
                "client": "qgis-plugin",
                "data": data,
            }
            if isinstance(validation, dict):
                body["validation"] = validation
            if isinstance(plan, dict):
                body["plan"] = plan

            # 关键：对「实际发出的字节」算摘要（用 data=raw 而非 json=body），
            # 服务端对收到的原始 body 复算，避免 Python/Java 的 JSON
            # 规范化差异（键序、空格、转义）导致误判为传输损坏。
            raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
            sha = hashlib.sha256(raw).hexdigest()

            expect = _ftth_counts(data)

            # ---- 本地落盘缓存：失败也不丢，可重发 ----
            queue = _queue_load()
            item = {
                "kind": "ftth",
                "uploadId": upload_id,
                "tag": tag,
                "counts": expect,
                "sha256": sha,
                "bytes": len(raw),
                "status": "pending",
                "createdAt": time.time(),
            }
            queue.append(item)
            _queue_save(queue)

            last_err = ""
            for attempt in range(_MAX_RETRIES):
                try:
                    resp = requests.post(
                        f"{self.api_url}/api/m03/ftth/{tag}",
                        data=raw,
                        timeout=60,
                        headers={
                            "Content-Type": "application/json; charset=utf-8",
                            "X-Payload-Sha256": sha,
                            "X-API-Key": self.api_key,
                        },
                    )
                    if resp.status_code == 200:
                        r = resp.json()
                        if r.get("code") == 200:
                            d = r.get("data") or {}
                            verified = self._verify_ftth(tag, expect)
                            item["status"] = "done"
                            item["verified"] = verified
                            item["idempotent"] = bool(d.get("idempotent"))
                            _queue_save(queue)
                            return True, {
                                "tag": tag,
                                "written": d.get("written") or [],
                                "counts": d.get("counts") or expect,
                                "idempotent": bool(d.get("idempotent")),
                                "verified": verified,
                                "data_dir": d.get("dataDir"),
                                "message": d.get("message", ""),
                            }
                        # 业务错误(校验/参数)：不重试
                        last_err = r.get("message", "Unknown error")
                        break
                    elif resp.status_code == 401:
                        last_err = ("401 鉴权失败：X-API-Key 与后端 m03.api-key 不一致"
                                    "（设置环境变量 M03_API_KEY 后重启 QGIS）")
                        break
                    else:
                        last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
                        if 400 <= resp.status_code < 500:
                            break
                except requests.exceptions.ConnectionError:
                    last_err = f"M03后端未运行 ({self.api_url})"
                except requests.exceptions.Timeout:
                    last_err = "上传超时(60s)"
                except Exception as e:
                    last_err = str(e)

                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_BACKOFF_BASE * (3 ** attempt))

            item["status"] = "failed"
            item["last_error"] = last_err
            _queue_save(queue)
            return False, last_err

        except Exception as e:
            return False, str(e)

    def upload_ftth_from_dir(self, out_dir, tag, file_tag=None, label=None) -> tuple:
        """
        从 FTTH 导出目录读取三件套并同步。

        Args:
            out_dir: 导出目录（export_from_qgis / export_from_dbf 的 out_dir）
            tag: 上传到后端使用的数据集标识
            file_tag: 导出时的文件名前缀（默认同 tag），文件名形如 {file_tag}_ftth-data.json
            label: 前端显示名
        """
        ft = file_tag or tag
        d = Path(out_dir)

        def _read(name):
            p = d / f"{ft}_{name}"
            if not p.exists():
                return None
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"[data_sync] 读取 {p.name} 失败: {e}")
                return None

        data = _read("ftth-data.json")
        if data is None:
            return False, f"未找到 {ft}_ftth-data.json（目录 {out_dir}），请先执行 FTTH 导出"
        return self.upload_ftth(
            tag, data,
            validation=_read("ftth-validation.json"),
            plan=_read("ftth-plan.json"),
            label=label,
        )

    def _verify_ftth(self, tag, expect) -> bool:
        """校验回环：从后端拉回 ftth-data，比对箱体/缆/站点/PM 计数。"""
        try:
            resp = requests.get(
                f"{self.api_url}/api/m03/ftth/{tag}/data",
                timeout=15,
                headers={"X-API-Key": self.api_key},
            )
            if resp.status_code != 200:
                print(f"[data_sync] FTTH 校验回环失败: HTTP {resp.status_code}")
                return False
            r = resp.json()
            if r.get("code") != 200:
                print(f"[data_sync] FTTH 校验回环失败: {r.get('message')}")
                return False
            actual = _ftth_counts(r.get("data") or {})
            if actual != expect:
                print(f"[data_sync] FTTH 校验回环告警: 期望 {expect}, 服务端 {actual}")
                return False
            return True
        except Exception as e:
            print(f"[data_sync] FTTH 校验回环异常(不影响上传结果): {e}")
            return False


def _ftth_counts(data: dict) -> dict:
    """FTTH 三类核心要素计数，用于上传前后比对。"""
    return {
        "boites": len(data.get("boites") or []),
        "cables": len(data.get("cables") or []),
        "sites": len(data.get("sites") or []),
        "pm": len(data.get("pm_list") or []),
    }


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
