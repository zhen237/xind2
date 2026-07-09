"""
数据同步模块
用于将QGIS插件的数据同步到M03后端
"""

import os
import requests
import json
import time
from typing import List, Dict, Optional

from ..utils.log_util import get_plugin_logger

_logger = get_plugin_logger(__name__)


class DataSync:
    """数据同步类"""

    def __init__(self, api_url: str = None, max_retries: int = 3, timeout: int = 30):
        """
        初始化数据同步

        Args:
            api_url: M03后端API地址，优先读取环境变量 DATA_SYNC_API_URL，其次默认为 http://localhost:8083
            max_retries: 最大重试次数
            timeout: 请求超时时间（秒）
        """
        self.api_url = api_url or os.environ.get("DATA_SYNC_API_URL", "http://localhost:8083")
        self.max_retries = max_retries
        self.timeout = timeout

    def _request_with_retry(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """带重试机制的 HTTP 请求"""
        kwargs.setdefault("timeout", self.timeout)
        for attempt in range(self.max_retries):
            try:
                resp = requests.request(method, url, **kwargs)
                return resp
            except requests.exceptions.ConnectionError:
                delay = 1.5 ** attempt  # 指数退避 1s -> 1.5s -> 2.25s
                time.sleep(delay)
                if attempt == self.max_retries - 1:
                    return None
            except requests.exceptions.Timeout:
                if attempt == self.max_retries - 1:
                    return None
        return None

    def upload_design(self, project_id, sites, params, avoidance_checker=None):
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

            design_data = {
                "projectId": project_id,
                "schemeName": params.get("scheme_name", "通信基站设计"),
                "frequencyBand": params.get("band", "3.5GHz"),
                "towerHeight": params.get("tower_height", 35),
                "gridSize": params.get("grid_size", "4x4"),
                "totalSites": len(sites),
                "validSites": valid_count,
                "invalidSites": invalid_count,
                "avgRsrp": params.get("avg_rsrp", 0),
                "sites": site_list,
            }

            response = self._request_with_retry(
                "POST",
                f"{self.api_url}/api/m03/design/upload",
                json=design_data,
            )

            if response is None:
                return False, "M03后端连接失败，请确认服务已启动"
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 200:
                    return True, result.get("data")
                return False, result.get("message", "未知错误")
            return False, f"HTTP {response.status_code}"

        except requests.exceptions.ConnectionError:
            return False, "M03后端未运行 (localhost:8083)"
        except Exception as e:
            return False, str(e)

    def download_design(self, project_id: int) -> Optional[Dict]:
        """
        从M03后端下载设计方案

        Args:
            project_id: 项目ID

        Returns:
            设计数据字典，失败返回None
        """
        response = self._request_with_retry("GET", f"{self.api_url}/api/m03/design/{project_id}")

        if response is None:
            _logger.warning("连接失败：M03后端未运行")
            return None
        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 200:
                return result.get('data')
            _logger.error("API 错误: %s", result.get('message', '未知错误'))
            return None
        _logger.error("HTTP 错误: %s", response.status_code)
        return None

    def get_sites(self, scheme_id: int) -> Optional[List[Dict]]:
        """
        获取站点数据

        Args:
            scheme_id: 方案ID

        Returns:
            站点列表，失败返回None
        """
        response = self._request_with_retry("GET", f"{self.api_url}/api/m03/design/{scheme_id}/sites")

        if response is None:
            _logger.warning("连接失败：M03后端未运行")
            return None
        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 200:
                return result.get('data')
            _logger.error("API 错误: %s", result.get('message', '未知错误'))
            return None
        _logger.error("HTTP 错误: %s", response.status_code)
        return None


def create_data_sync(api_url: str = None, max_retries: int = 3, timeout: int = 30) -> DataSync:
    """
    创建数据同步实例

    Args:
        api_url: M03后端API地址，默认从环境变量 DATA_SYNC_API_URL 读取
        max_retries: 最大重试次数
        timeout: 超时时间（秒）

    Returns:
        DataSync实例
    """
    return DataSync(api_url=api_url, max_retries=max_retries, timeout=timeout)
