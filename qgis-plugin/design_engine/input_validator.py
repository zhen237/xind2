"""输入验证器

提供参数验证和数据安全检查

作者: M03模块开发团队
日期: 2026-07-02
"""

import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from ..utils.log_util import get_plugin_logger

_logger = get_plugin_logger(__name__)


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
    
    def add_error(self, error: str):
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str):
        self.warnings.append(warning)
    
    def merge(self, other: 'ValidationResult'):
        """合并另一个验证结果"""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.is_valid:
            self.is_valid = False


class InputValidator:
    """输入参数验证器"""
    
    # 常量定义
    FREQUENCY_MIN = 100.0
    FREQUENCY_MAX = 10000.0
    
    LONGITUDE_MIN = -180.0
    LONGITUDE_MAX = 180.0
    LATITUDE_MIN = -90.0
    LATITUDE_MAX = 90.0
    
    TOWER_HEIGHT_MIN = 5.0
    TOWER_HEIGHT_MAX = 100.0
    
    COVERAGE_RADIUS_MIN = 50.0
    COVERAGE_RADIUS_MAX = 5000.0
    
    GRID_SIZE_MIN = 10.0
    GRID_SIZE_MAX = 1000.0
    
    MAX_BBOX_AREA_KM2 = 50.0
    
    @classmethod
    def validate_frequency(cls, freq: float) -> ValidationResult:
        """验证频率参数"""
        result = ValidationResult(is_valid=True)
        
        if not isinstance(freq, (int, float)):
            result.add_error(f"频率必须是数字类型，当前: {type(freq).__name__}")
            return result
        
        if freq < cls.FREQUENCY_MIN or freq > cls.FREQUENCY_MAX:
            result.add_error(
                f"频率必须在{cls.FREQUENCY_MIN}-{cls.FREQUENCY_MAX}MHz范围内，当前: {freq}MHz"
            )
        
        # 警告: 非常规频段
        common_frequencies = [700, 800, 900, 1800, 2100, 2600, 3500, 4900]
        if freq not in common_frequencies:
            result.add_warning(f"非常规频段{freq}MHz，建议使用: {common_frequencies}")
        
        return result
    
    @classmethod
    def validate_coordinates(cls, lon: float, lat: float) -> ValidationResult:
        """验证坐标参数"""
        result = ValidationResult(is_valid=True)
        
        if not isinstance(lon, (int, float)) or not isinstance(lat, (int, float)):
            result.add_error("经纬度必须是数字类型")
            return result
        
        if not (cls.LONGITUDE_MIN <= lon <= cls.LONGITUDE_MAX):
            result.add_error(f"经度必须在{cls.LONGITUDE_MIN}-{cls.LONGITUDE_MAX}范围内，当前: {lon}")
        
        if not (cls.LATITUDE_MIN <= lat <= cls.LATITUDE_MAX):
            result.add_error(f"纬度必须在{cls.LATITUDE_MIN}-{cls.LATITUDE_MAX}范围内，当前: {lat}")
        
        # 警告: 接近边界
        if lon < -170 or lon > 170:
            result.add_warning("经度接近边界，可能影响覆盖计算")
        if lat < -80 or lat > 80:
            result.add_warning("纬度接近边界，可能影响覆盖计算")
        
        return result
    
    @classmethod
    def validate_tower_height(cls, height: float) -> ValidationResult:
        """验证塔高参数"""
        result = ValidationResult(is_valid=True)
        
        if not isinstance(height, (int, float)):
            result.add_error("塔高必须是数字类型")
            return result
        
        if height < cls.TOWER_HEIGHT_MIN or height > cls.TOWER_HEIGHT_MAX:
            result.add_error(
                f"塔高必须在{cls.TOWER_HEIGHT_MIN}-{cls.TOWER_HEIGHT_MAX}米范围内，当前: {height}m"
            )
        
        return result
    
    @classmethod
    def validate_coverage_radius(cls, radius: float) -> ValidationResult:
        """验证覆盖半径参数"""
        result = ValidationResult(is_valid=True)
        
        if not isinstance(radius, (int, float)):
            result.add_error("覆盖半径必须是数字类型")
            return result
        
        if radius < cls.COVERAGE_RADIUS_MIN:
            result.add_error(f"覆盖半径不能小于{cls.COVERAGE_RADIUS_MIN}米")
        elif radius < 100:
            result.add_warning(f"覆盖半径较小({radius}m)，可能无法生成有效站点")
        
        if radius > cls.COVERAGE_RADIUS_MAX:
            result.add_warning(f"覆盖半径过大({radius}m)，建议分区域规划")
        
        return result
    
    @classmethod
    def validate_grid_size(cls, size: float) -> ValidationResult:
        """验证网格大小参数"""
        result = ValidationResult(is_valid=True)
        
        if not isinstance(size, (int, float)):
            result.add_error("网格大小必须是数字类型")
            return result
        
        if size < cls.GRID_SIZE_MIN:
            result.add_error(f"网格大小不能小于{cls.GRID_SIZE_MIN}米")
        elif size > cls.GRID_SIZE_MAX:
            result.add_warning(f"网格较大({size}m)，可能遗漏覆盖细节")
        
        return result
    
    @classmethod
    def validate_sector_count(cls, count: int) -> ValidationResult:
        """验证扇区数参数"""
        result = ValidationResult(is_valid=True)
        
        if not isinstance(count, int):
            result.add_error("扇区数必须是整数类型")
            return result
        
        if count < 0 or count > 12:
            result.add_error("扇区数必须在0-12范围内")
        elif count not in [0, 1, 3, 6]:
            result.add_warning(f"非常规扇区数({count})，建议使用0、1、3或6")
        
        return result
    
    @classmethod
    def validate_bbox(cls, bbox: Tuple[float, float, float, float]) -> ValidationResult:
        """验证边界框参数"""
        result = ValidationResult(is_valid=True)
        
        if len(bbox) != 4:
            result.add_error("边界框必须包含4个值: (min_lon, min_lat, max_lon, max_lat)")
            return result
        
        lon_min, lat_min, lon_max, lat_max = bbox
        
        # 验证坐标范围
        lon_result = cls.validate_coordinates(lon_min, lat_min)
        lat_result = cls.validate_coordinates(lon_max, lat_max)
        result.merge(lon_result)
        result.merge(lat_result)
        
        # 验证边界框有效性
        if lon_min >= lon_max:
            result.add_error("min_lon必须小于max_lon")
        
        if lat_min >= lat_max:
            result.add_error("min_lat必须小于max_lat")
        
        # 计算面积
        mid_lat = (lat_min + lat_max) / 2
        width_km = (lon_max - lon_min) * 111 * math.cos(math.radians(mid_lat))
        height_km = (lat_max - lat_min) * 111
        area_km2 = width_km * height_km
        
        if area_km2 > cls.MAX_BBOX_AREA_KM2:
            result.add_error(
                f"设计区域面积{area_km2:.2f}km²超过最大值{cls.MAX_BBOX_AREA_KM2}km²"
            )
        elif area_km2 > cls.MAX_BBOX_AREA_KM2 * 0.8:
            result.add_warning(
                f"设计区域面积较大({area_km2:.2f}km²)，生成可能需要较长时间"
            )
        
        return result
    
    @classmethod
    def validate_band_config(cls, config: Dict) -> ValidationResult:
        """验证频段配置参数"""
        result = ValidationResult(is_valid=True)
        
        if not isinstance(config, dict):
            result.add_error("频段配置必须是字典类型")
            return result
        
        required_keys = ['frequency_mhz', 'power_w', 'gain_dbi']
        for key in required_keys:
            if key not in config:
                result.add_error(f"频段配置缺少必需字段: {key}")
        
        if 'frequency_mhz' in config:
            freq_result = cls.validate_frequency(config['frequency_mhz'])
            result.merge(freq_result)
        
        return result
    
    @classmethod
    def validate_all_params(cls, params: Dict) -> ValidationResult:
        """批量验证所有参数"""
        result = ValidationResult(is_valid=True)
        
        # 验证坐标
        if 'center_longitude' in params and 'center_latitude' in params:
            coord_result = cls.validate_coordinates(
                params['center_longitude'],
                params['center_latitude']
            )
            result.merge(coord_result)
        
        # 验证频率
        if 'frequency' in params:
            freq_result = cls.validate_frequency(params['frequency'])
            result.merge(freq_result)
        
        # 验证塔高
        if 'tower_height' in params:
            height_result = cls.validate_tower_height(params['tower_height'])
            result.merge(height_result)
        
        # 验证覆盖半径
        if 'coverage_radius' in params:
            radius_result = cls.validate_coverage_radius(params['coverage_radius'])
            result.merge(radius_result)
        
        # 验证网格大小
        if 'grid_size' in params:
            size_result = cls.validate_grid_size(params['grid_size'])
            result.merge(size_result)
        
        # 验证扇区数
        if 'sector_count' in params:
            sector_result = cls.validate_sector_count(params['sector_count'])
            result.merge(sector_result)
        
        # 验证边界框
        if 'bbox' in params:
            bbox_result = cls.validate_bbox(params['bbox'])
            result.merge(bbox_result)
        
        return result


class DataSecurity:
    """数据安全保护"""
    
    @staticmethod
    def sanitize_coordinates(lon: float, lat: float) -> Tuple[float, float]:
        """清理坐标数据"""
        lon = max(-180.0, min(180.0, float(lon)))
        lat = max(-90.0, min(90.0, float(lat)))
        return (round(lon, 7), round(lat, 7))
    
    @staticmethod
    def validate_site_data(site_data: Dict) -> bool:
        """验证站点数据完整性"""
        required_fields = ['site_id', 'longitude', 'latitude']
        
        for field in required_fields:
            if field not in site_data:
                return False
        
        # 验证坐标有效性
        lon = site_data['longitude']
        lat = site_data['latitude']
        
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            return False
        
        return True
    
    @staticmethod
    def backup_project_data(project_data: Dict) -> Optional[str]:
        """备份项目数据"""
        import json
        import os
        from datetime import datetime
        
        try:
            backup_dir = "backups"
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"project_backup_{timestamp}.json")
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, ensure_ascii=False, indent=2)
            
            return backup_file
        except Exception as e:
            _logger.error("备份失败: %s", e, exc_info=True)
            return None
