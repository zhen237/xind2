"""BOM (Bill of Materials) 自动生成器

从设计方案中提取 BOM 清单，包括站点设备、管线材料、机房设备等。
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
import csv
import os

from ..utils.log_util import get_plugin_logger

_logger = get_plugin_logger(__name__)


@dataclass
class BOMItem:
    """BOM 物料项"""
    category: str          # 类别：站点设备 / 管线材料 / 机房设备 / 其他
    item_code: str         # 物料编码
    item_name: str         # 物料名称
    specification: str     # 规格型号
    quantity: float        # 数量
    unit: str             # 单位：台/根/米/套
    unit_price: float     # 单价（元）
    remark: str = ""      # 备注


@dataclass
class BOMReport:
    """BOM 报告"""
    project_name: str
    scheme_name: str
    items: List[BOMItem] = field(default_factory=list)
    total_cost: float = 0.0

    def calculate_total(self):
        self.total_cost = sum(
            item.quantity * item.unit_price for item in self.items
        )

    def to_csv(self, output_path: str) -> bool:
        """导出为 CSV 文件"""
        try:
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(["类别", "物料编码", "物料名称", "规格型号", "数量", "单位", "单价(元)", "小计(元)", "备注"])
                for item in self.items:
                    subtotal = round(item.quantity * item.unit_price, 2)
                    writer.writerow([
                        item.category, item.item_code, item.item_name,
                        item.specification, item.quantity, item.unit,
                        f"{item.unit_price:.2f}", f"{subtotal:.2f}", item.remark
                    ])
                writer.writerow([])
                writer.writerow(["合计", "", "", "", "", "", "", f"{self.total_cost:.2f}", ""])
            return True
        except Exception as e:
            _logger.error("BOM CSV 导出失败: %s", e, exc_info=True)
            return False

    def summary(self) -> str:
        """生成 BOM 汇总文本"""
        self.calculate_total()
        lines = [
            f"BOM 汇总表",
            f"{'='*60}",
            f"项目名称: {self.project_name}",
            f"方案名称: {self.scheme_name}",
            f"总物料项数: {len(self.items)}",
            f"总预算: ¥{self.total_cost:,.2f}",
            f"",
            f"按类别汇总:",
            f"{'-'*60}",
        ]
        categories = {}
        for item in self.items:
            if item.category not in categories:
                categories[item.category] = {'count': 0, 'cost': 0.0}
            categories[item.category]['count'] += 1
            categories[item.category]['cost'] += item.quantity * item.unit_price

        for cat, stats in categories.items():
            lines.append(f"  {cat}: {stats['count']} 项, ¥{stats['cost']:,.2f}")

        return "\n".join(lines)


# ============================================================================
#  物料价格配置
# ============================================================================

ANTENNA_PRICE = {
    "AAU5313": {"unit_price": 8500.0, "specification": "3.5GHz/4.9GHz Massive MIMO AAU"},
    "AAU5639": {"unit_price": 6800.0, "specification": "2.6GHz Massive MIMO AAU"},
    "RRU5301": {"unit_price": 4500.0, "specification": "700MHz/900MHz RRU"},
}

PIPELINE_PRICE = {
    "PIPE_SUBTERRANEAN": {
        "category": "管线材料",
        "unit_price": 85.0,
        "specification": "子管（Φ32 PE 双壁波纹管）",
        "unit": "米",
    },
    "PIPE_AERIAL": {
        "category": "管线材料",
        "unit_price": 120.0,
        "specification": "钢管 Φ89×4.5",
        "unit": "米",
    },
    "TOWERS_LINE": {
        "category": "管线材料",
        "unit_price": 45.0,
        "specification": "电杆（Φ190×12m 水泥杆）",
        "unit": "根",
    },
}

TOWER_PRICE = {
    "TOW_GUYED": {"unit_price": 35000.0, "specification": "拉线铁塔"},
    "TOW_SELF_SUPPORT": {"unit_price": 55000.0, "specification": "自立塔"},
    "TOW_MONITOR_POLE": {"unit_price": 12000.0, "specification": "仿生监控塔"},
    "TOW_ROOF_MOUNT": {"unit_price": 8000.0, "specification": "屋顶抱杆"},
}

MACHINE_ROOM_PRICE = {
    "ROOM_STANDARD": {"unit_price": 25000.0, "specification": "标准机房（2×3m）"},
    "ROOM_OUTDOOR_CABINET": {"unit_price": 18000.0, "specification": "户外机柜"},
}


# ============================================================================
#  BOM 提取器
# ============================================================================

class BOMExtractor:
    """从设计方案提取 BOM"""

    @classmethod
    def extract(cls, sites: List[Dict], pipelines: Optional[List[Dict]] = None,
                machine_rooms: Optional[List[Dict]] = None,
                project_name: str = "通信基站设计方案",
                scheme_name: str = "默认方案") -> BOMReport:
        """
        提取 BOM 报告

        Args:
            sites: 站点列表
            pipelines: 管线列表（可选）
            machine_rooms: 机房列表（可选）
            project_name: 项目名称
            scheme_name: 方案名称

        Returns:
            BOMReport 对象
        """
        report = BOMReport(project_name=project_name, scheme_name=scheme_name)

        # 站点设备 BOM
        antenna_counts = {}
        tower_types = {}
        for site in sites:
            ant_type = site.get('antenna_type', 'AAU5639')
            antenna_counts[ant_type] = antenna_counts.get(ant_type, 0) + 1

            tower_type = site.get('tower_type', 'TOW_SELF_SUPPORT')
            tower_types[tower_type] = tower_types.get(tower_type, 0) + 1

        for ant_type, count in antenna_counts.items():
            info = ANTENNA_PRICE.get(ant_type, {"unit_price": 5000.0, "specification": "默认天线"})
            report.items.append(BOMItem(
                category="站点设备",
                item_code=f"ANT-{ant_type}",
                item_name="射频单元" if "RRU" in ant_type else "有源天线",
                specification=info["specification"],
                quantity=count,
                unit="台",
                unit_price=info["unit_price"],
            ))

        for tower_type, count in tower_types.items():
            info = TOWER_PRICE.get(tower_type, {"unit_price": 30000.0, "specification": "默认塔型"})
            report.items.append(BOMItem(
                category="站点设备",
                item_code=f"TWR-{tower_type}",
                item_name="铁塔/杆塔",
                specification=info["specification"],
                quantity=count,
                unit="座",
                unit_price=info["unit_price"],
            ))

        # 管线材料 BOM
        if pipelines:
            total_pipe_len = 0.0
            total_tower_len = 0.0
            total_subterranean_len = 0.0
            total_aerial_len = 0.0

            for pipe in pipelines:
                length = pipe.get('length_m', 0)
                pipe_type = pipe.get('pipe_type', 'PIPE_SUBTERRANEAN')
                if pipe_type in PIPELINE_PRICE:
                    price_info = PIPELINE_PRICE[pipe_type]
                    total_cost = length * price_info["unit_price"]
                    # 累计
                    if "TOWERS_LINE" in pipe_type:
                        total_tower_len += length
                    elif "SUBTERRANEAN" in pipe_type:
                        total_subterranean_len += length
                    elif "AERIAL" in pipe_type:
                        total_aerial_len += length
                    else:
                        total_pipe_len += length

            # 汇总管线材料
            if total_subterranean_len > 0:
                info = PIPELINE_PRICE["PIPE_SUBTERRANEAN"]
                report.items.append(BOMItem(
                    category="管线材料",
                    item_code="PIPE-SUB",
                    item_name="子管",
                    specification=info["specification"],
                    quantity=round(total_subterranean_len, 0),
                    unit=info["unit"],
                    unit_price=info["unit_price"],
                ))

            if total_aerial_len > 0:
                info = PIPELINE_PRICE["PIPE_AERIAL"]
                report.items.append(BOMItem(
                    category="管线材料",
                    item_code="PIPE-AIR",
                    item_name="钢管",
                    specification=info["specification"],
                    quantity=round(total_aerial_len, 0),
                    unit=info["unit"],
                    unit_price=info["unit_price"],
                ))

            if total_tower_len > 0:
                info = PIPELINE_PRICE["TOWERS_LINE"]
                report.items.append(BOMItem(
                    category="管线材料",
                    item_code="TWR-LINE",
                    item_name="电杆",
                    specification=info["specification"],
                    quantity=round(total_tower_len, 0),
                    unit=info["unit"],
                    unit_price=info["unit_price"],
                ))

        # 机房设备 BOM
        if machine_rooms:
            for room in machine_rooms:
                room_type = room.get('room_type', 'ROOM_STANDARD')
                info = MACHINE_ROOM_PRICE.get(room_type, {"unit_price": 20000.0, "specification": "标准机房"})
                report.items.append(BOMItem(
                    category="机房设备",
                    item_code=f"RM-{room_type}",
                    item_name="机房/机柜",
                    specification=info["specification"],
                    quantity=1,
                    unit="套",
                    unit_price=info["unit_price"],
                ))

        report.calculate_total()
        return report
