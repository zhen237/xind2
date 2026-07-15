"""
数据同步模块
用于将QGIS插件的数据同步到M03后端
"""

import requests
import json
from typing import List, Dict, Optional


class DataSync:
    """数据同步类"""

    def __init__(self, api_url="http://localhost:8083"):
        """
        初始化数据同步

        Args:
            api_url: M03后端API地址
        """
        self.api_url = api_url

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

            response = requests.post(
                f"{self.api_url}/api/m03/design/upload",
                json=design_data,
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 200:
                    return True, result.get("data")
                return False, result.get("message", "Unknown error")
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
        try:
            response = requests.get(
                f"{self.api_url}/api/m03/design/{project_id}",
                timeout=10
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
                timeout=10
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


def create_data_sync(api_url="http://localhost:8083") -> DataSync:
    """
    创建数据同步实例

    Args:
        api_url: M03后端API地址

    Returns:
        DataSync实例
    """
    return DataSync(api_url)
