# -*- coding: utf-8 -*-
"""管线数据模型"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from enum import Enum


class PipelineType(Enum):
    """管线类型"""
    DIRECT_BURIED = "直埋"  # 直埋管线
    DUCT = "管道"          # 管道管线
    AERIAL = "架空"        # 架空管线


@dataclass
class Pipeline:
    """管线数据模型"""
    pipeline_id: str                    # 管线编号
    start_site_id: str                  # 起始站点ID
    end_site_id: str                    # 终止站点ID
    pipeline_type: PipelineType         # 管线类型
    coordinates: List[Tuple[float, float]] = field(default_factory=list)  # 路由坐标 [(lon, lat), ...]
    length_m: float = 0.0              # 长度（米）
    depth_m: float = 1.2               # 埋深（米），架空时为0
    diameter_mm: int = 110             # 管径（毫米）
    material: str = "PE"               # 材质（PE/PVC/钢管）
    capacity: int = 4                  # 容量（孔数）
    is_shared: bool = False            # 是否共享路由
    shared_with: List[str] = field(default_factory=list)  # 共享的其他管线ID
    engineering_volume: dict = field(default_factory=dict)  # 工程量
    status: str = "planned"            # 状态（planned/installed/maintenance）

    def calculate_length(self) -> float:
        """计算管线长度（米）"""
        if len(self.coordinates) < 2:
            return 0.0

        import math
        total_length = 0.0
        for i in range(len(self.coordinates) - 1):
            lon1, lat1 = self.coordinates[i]
            lon2, lat2 = self.coordinates[i + 1]

            # Haversine公式计算两点间距离
            R = 6371000  # 地球半径（米）
            phi1 = math.radians(lat1)
            phi2 = math.radians(lat2)
            delta_phi = math.radians(lat2 - lat1)
            delta_lambda = math.radians(lon2 - lon1)

            a = (math.sin(delta_phi / 2) ** 2 +
                 math.cos(phi1) * math.cos(phi2) *
                 math.sin(delta_lambda / 2) ** 2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

            distance = R * c
            total_length += distance

        self.length_m = round(total_length, 2)
        return self.length_m

    def calculate_engineering_volume(self) -> dict:
        """计算工程量"""
        if self.length_m == 0:
            self.calculate_length()

        volume = {
            "管线长度(m)": self.length_m,
            "管线类型": self.pipeline_type.value,
            "管径(mm)": self.diameter_mm,
            "材质": self.material,
            "容量(孔)": self.capacity,
        }

        # 根据管线类型计算不同工程量
        if self.pipeline_type == PipelineType.DIRECT_BURIED:
            # 直埋：计算土方量
            trench_width = self.diameter_mm / 1000 + 0.6  # 沟宽 = 管径 + 0.6m
            trench_depth = self.depth_m + 0.1  # 沟深 = 埋深 + 0.1m垫层
            volume["沟宽(m)"] = round(trench_width, 2)
            volume["沟深(m)"] = round(trench_depth, 2)
            volume["土方量(m³)"] = round(self.length_m * trench_width * trench_depth, 2)

        elif self.pipeline_type == PipelineType.DUCT:
            # 管道：计算管道数量
            volume["管道数量"] = self.capacity
            volume["管道总长度(m)"] = round(self.length_m * self.capacity, 2)

        elif self.pipeline_type == PipelineType.AERIAL:
            # 架空：计算杆路
            pole_spacing = 50  # 杆距50米
            volume["杆距(m)"] = pole_spacing
            volume["电杆数量"] = int(self.length_m / pole_spacing) + 1

        self.engineering_volume = volume
        return volume

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "pipeline_id": self.pipeline_id,
            "start_site_id": self.start_site_id,
            "end_site_id": self.end_site_id,
            "pipeline_type": self.pipeline_type.value,
            "coordinates": self.coordinates,
            "length_m": self.length_m,
            "depth_m": self.depth_m,
            "diameter_mm": self.diameter_mm,
            "material": self.material,
            "capacity": self.capacity,
            "is_shared": self.is_shared,
            "shared_with": self.shared_with,
            "engineering_volume": self.engineering_volume,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Pipeline':
        """从字典创建"""
        return cls(
            pipeline_id=data["pipeline_id"],
            start_site_id=data["start_site_id"],
            end_site_id=data["end_site_id"],
            pipeline_type=PipelineType(data["pipeline_type"]),
            coordinates=data.get("coordinates", []),
            length_m=data.get("length_m", 0.0),
            depth_m=data.get("depth_m", 1.2),
            diameter_mm=data.get("diameter_mm", 110),
            material=data.get("material", "PE"),
            capacity=data.get("capacity", 4),
            is_shared=data.get("is_shared", False),
            shared_with=data.get("shared_with", []),
            engineering_volume=data.get("engineering_volume", {}),
            status=data.get("status", "planned"),
        )


@dataclass
class PipelineConfig:
    """管线配置"""
    # 管线类型配置
    type_configs = {
        PipelineType.DIRECT_BURIED: {
            "name": "直埋管线",
            "description": "适用于郊区、农村等空旷区域",
            "default_depth": 1.2,
            "default_diameter": 110,
            "default_material": "PE",
            "default_capacity": 4,
            "color": "#8B4513",  # 棕色
            "line_style": "solid",
        },
        PipelineType.DUCT: {
            "name": "管道管线",
            "description": "适用于城市道路、小区等区域",
            "default_depth": 1.5,
            "default_diameter": 110,
            "default_material": "PVC",
            "default_capacity": 4,
            "color": "#4169E1",  # 蓝色
            "line_style": "dash",
        },
        PipelineType.AERIAL: {
            "name": "架空管线",
            "description": "适用于山区、跨越河流等区域",
            "default_depth": 0,
            "default_diameter": 50,
            "default_material": "ADSS光缆",
            "default_capacity": 1,
            "color": "#228B22",  # 绿色
            "line_style": "dot",
        },
    }

    # 默认机房位置（如果未指定）
    default_room_location = None

    # 管线避让规则
    avoidance_rules = {
        "river": {"buffer_m": 20, "description": "河流避让20m"},
        "road": {"buffer_m": 5, "description": "道路避让5m"},
        "building": {"buffer_m": 10, "description": "建筑物避让10m"},
        "power_line": {"buffer_m": 15, "description": "电力线避让15m"},
    }

    # 成本配置（元）
    cost_configs = {
        PipelineType.DIRECT_BURIED: {
            "光缆单价(元/m)": 15,           # 光缆材料费
            "土方开挖单价(元/m³)": 50,       # 土方开挖费
            "回填单价(元/m³)": 30,           # 回填费
            "接头盒单价(元/个)": 200,        # 接头盒
            "标石单价(元/个)": 80,           # 标石
            "标石间距(m)": 100,              # 每100米一个标石
            "接头间距(m)": 2000,             # 每2公里一个接头
        },
        PipelineType.DUCT: {
            "管道单价(元/m)": 45,            # 管道材料费
            "光缆单价(元/m)": 15,            # 管道内光缆
            "土方开挖单价(元/m³)": 60,       # 城市开挖成本更高
            "回填单价(元/m³)": 40,
            "人孔单价(元/个)": 3000,         # 人孔（检查井）
            "人孔间距(m)": 100,              # 每100米一个人孔
            "接头盒单价(元/个)": 200,
            "接头间距(m)": 2000,
        },
        PipelineType.AERIAL: {
            "光缆单价(元/m)": 18,            # 架空光缆（含钢绞线）
            "电杆单价(元/根)": 1500,         # 水泥电杆
            "杆距(m)": 50,                   # 标准杆距
            "拉线单价(元/条)": 500,          # 拉线
            "拉线比例": 0.3,                 # 每公里约0.3条拉线
            "接头盒单价(元/个)": 200,
            "接头间距(m)": 2000,
        },
        # 施工附加费率
        "施工附加费率": 0.15,  # 15% 施工管理费
        "利润费率": 0.05,      # 5% 利润
        "税金费率": 0.09,      # 9% 增值税
    }
