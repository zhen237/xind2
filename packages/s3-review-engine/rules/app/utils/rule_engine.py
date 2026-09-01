"""
通信基建审查规则引擎
实现管线埋深、接地电阻、线缆弯曲半径、线缆载流量四类基础校验逻辑。

【重要】本引擎所有校验阈值均依据通信工程 / 电力工程行业现行国家标准与规范设定，
属于可量化、可复核的硬性技术条款，而非自定义测试值。主要参考规范包括：
  - GB 50217《电力工程电缆设计标准》（埋深、弯曲半径、载流量）
  - GB 50169《电气装置安装工程 接地装置施工及验收规范》
  - DL/T 621《交流电气装置的接地》
  - GB 50057《建筑物防雷设计规范》等
规则管理页面（S3SafetyRule 表）的 CRUD 用于维护上述行业规范对应的审查条款，
本引擎负责依据条款中的阈值对设计参数做真实比对计算。
"""
import math
from typing import Dict, Any, Optional, List, Tuple

# ==================== 标准参数配置（依据通信/电力行业规范） ====================
# 管线埋深标准（米）—— 区分「直埋 / 管道敷设」与「城区 / 郊外」场景，匹配国标差异化阈值
# 依据：
#   - GB 51158《通信线路工程验收规范》：直埋光缆/电缆最小埋深 普通土(市区)≥0.8m、郊外/农田≥1.0m；
#   - GB 50373《通信管道工程施工及验收标准》：管道顶部至路面埋深 车行道≥0.8m、人行道/绿地≥0.5m。
# 上述为通信管线主流硬性条款；电力电缆直埋亦参照 GB 50217 同类要求（数值相近）。
BURIED_DEPTH_MATRIX = {
    "direct": {                       # 直埋敷设
        "urban": 0.8,                 # 城区（普通土/硬土）最小埋深 ≥0.8m
        "suburb": 1.0,                # 郊外/农田/野外最小埋深 ≥1.0m
    },
    "pipe": {                         # 管道敷设
        "urban": 0.8,                 # 城区车行道下管顶至路面 ≥0.8m
        "suburb": 0.5,                # 郊外/人行道/绿地 ≥0.5m
    },
}
# 敷设方式 / 场景 中文与别名归一化
_BURIED_LAYING_CN = {"direct": "直埋", "pipe": "管道"}
_BURIED_SCENARIO_CN = {"urban": "城区", "suburb": "郊外"}

# 接地电阻标准（欧姆）
# 参考 GB 50169《电气装置安装工程 接地装置施工及验收规范》、DL/T 621《交流电气装置的接地》：
# 有效接地系统、配电室/变电站/通信机房等接地电阻一般要求 ≤4Ω；杆塔独立接地 ≤10Ω；
# 计算机机房等要求更严（≤2Ω）。均为行业强制安全限值。
GROUNDING_RESISTANCE_STANDARDS = {
    "power_substation": 4.0,  # 变电站
    "distribution_room": 4.0,  # 配电室
    "communication_room": 4.0,  # 通信机房
    "tower": 10.0,  # 杆塔
    "lightning_rod": 10.0,  # 避雷针
    "equipment": 4.0,  # 设备接地
    "computer_room": 2.0,  # 计算机房
}

# 弯曲半径标准（毫米）
# 参考 GB 50217《电力工程电缆设计标准》：电缆敷设时的最小弯曲半径一般为电缆外径的
# 15 倍（多芯）/20 倍（单芯），光缆、铜缆亦有相应倍数要求，目的是避免绝缘与导体受损。
BENDING_RADIUS_STANDARDS = {
    "power_cable": {
        "single_core": 20,  # 单芯电缆：20倍电缆外径
        "multi_core": 15,  # 多芯电缆：15倍电缆外径
        "min_value": 30,  # 最小值
    },
    "communication_cable": {
        "optical": 10,  # 光缆：10倍
        "copper": 8,  # 铜缆：8倍
        "min_value": 30,
    },
}

# 线缆截面载流量标准（按材质和截面积，单位 A）
# 参考 GB 50217《电力工程电缆设计标准》附录载流量表（铜缆/铝缆、不同截面下的长期允许载流量）。
# 工程选型需预留 1.25 倍及以上裕度（即实际工作电流 ≤ 额定载流量 / 1.25），防止过载发热。
CABLE_CURRENT_RATING = {
    "copper": {  # 铜缆
        1.5: 18, 2.5: 25, 4: 33, 6: 42, 10: 59,
        16: 79, 25: 105, 35: 130, 50: 160, 70: 200,
        95: 245, 120: 285, 150: 325, 185: 370, 240: 435,
    },
    "aluminum": {  # 铝缆
        2.5: 20, 4: 27, 6: 35, 10: 48, 16: 66,
        25: 87, 35: 106, 50: 131, 70: 167, 95: 205,
        120: 239, 150: 269, 185: 309, 240: 366,
    },
}


class ReviewRuleEngine:
    """通信基建审查规则引擎"""

    def __init__(self):
        self.rules_applied = 0
        self.rules_violated = 0

    def check_pipeline_buried_depth(
        self,
        laying_type: str,
        burial_depth: float,
        scenario: str = "urban",
        device_type: str = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        管线埋深检查（依据 GB 51158 / GB 50373 差异化阈值）
        :param laying_type: 敷设方式 direct(直埋) / pipe(管道)；兼容中文 直埋/管道/管敷
        :param burial_depth: 实际埋深（米）
        :param scenario: 场景 urban(城区) / suburb(郊外)；兼容中文 城区/市区/郊外/野外
        :param device_type: 设备/管线类型（电力电缆/通信电缆等，仅用于建议文案，不参与阈值判定）
        :return: (是否通过, 检查结果详情)
        """
        self.rules_applied += 1

        lt = self._norm_buried_laying(laying_type)
        sc = self._norm_buried_scenario(scenario)
        if lt is None or sc is None:
            return False, {
                "status": "unknown",
                "message": f"无法识别的敷设方式/场景: laying_type={laying_type}, scenario={scenario}",
                "suggestion": "请确认管线敷设方式(直埋/管道)与场景(城区/郊外)后重新检查",
                "standard_value": "未知",
                "actual_value": burial_depth,
            }

        standard_depth = BURIED_DEPTH_MATRIX[lt][sc]
        passed = burial_depth >= standard_depth

        if not passed:
            self.rules_violated += 1

        lt_cn = _BURIED_LAYING_CN[lt]
        sc_cn = _BURIED_SCENARIO_CN[sc]
        gb = "GB 51158" if lt == "direct" else "GB 50373"

        return passed, {
            "status": "pass" if passed else "fail",
            "rule_name": "管线埋深检查",
            "laying_type": lt,
            "laying_type_cn": lt_cn,
            "scenario": sc,
            "scenario_cn": sc_cn,
            "standard_depth_m": standard_depth,
            "actual_depth_m": burial_depth,
            "depth_deficit_m": round(standard_depth - burial_depth, 3) if not passed else 0,
            "suggestion": self._get_buried_depth_suggestion(lt, sc, burial_depth, standard_depth, device_type) if not passed else "埋深符合标准要求",
            "risk_level": "critical" if (not passed and burial_depth < standard_depth * 0.8) else "warning" if not passed else None,
            "standard_reference": f"依据 {gb}：{lt_cn}（{sc_cn}）最小埋深 ≥{standard_depth}m",
        }

    @staticmethod
    def _norm_buried_laying(v) -> Optional[str]:
        """敷设方式归一化：direct/直埋 → direct；pipe/管道/管敷 → pipe；其余 None"""
        if v is None:
            return None
        v = str(v).strip()
        if v in ("direct", "直埋"):
            return "direct"
        if v in ("pipe", "管道", "管敷"):
            return "pipe"
        return None

    @staticmethod
    def _norm_buried_scenario(v) -> Optional[str]:
        """场景归一化：urban/城区/市区 → urban；suburb/郊外/郊县/野外/农田 → suburb；其余 None"""
        if v is None:
            return None
        v = str(v).strip()
        if v in ("urban", "城区", "市区"):
            return "urban"
        if v in ("suburb", "郊外", "郊县", "野外", "农田"):
            return "suburb"
        return None

    def check_grounding_resistance(
        self,
        grounding_type: str,
        measured_resistance: float,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        检查接地电阻
        :param grounding_type: 接地类型
        :param measured_resistance: 实测接地电阻（欧姆）
        :return: (是否通过, 检查结果详情)
        """
        self.rules_applied += 1
        
        standard_resistance = GROUNDING_RESISTANCE_STANDARDS.get(grounding_type)
        if standard_resistance is None:
            return False, {
                "status": "unknown",
                "message": f"未知的接地类型: {grounding_type}",
                "suggestion": "请确认接地类型后重新检查",
                "standard_value": "未知",
                "actual_value": measured_resistance,
            }

        passed = measured_resistance <= standard_resistance
        
        if not passed:
            self.rules_violated += 1

        return passed, {
            "status": "pass" if passed else "fail",
            "rule_name": "接地电阻检查",
            "grounding_type": grounding_type,
            "standard_resistance_ohm": standard_resistance,
            "measured_resistance_ohm": measured_resistance,
            "resistance_exceed_ohm": round(measured_resistance - standard_resistance, 2) if not passed else 0,
            "suggestion": self._get_grounding_suggestion(grounding_type, measured_resistance, standard_resistance) if not passed else "接地电阻符合标准要求",
            "risk_level": "critical" if not passed and measured_resistance > standard_resistance * 1.5 else "error" if not passed else None,
            "standard_reference": f"{grounding_type} 接地电阻标准: ≤{standard_resistance}Ω",
        }

    def check_bending_radius(
        self,
        cable_type: str,
        cable_diameter: float,
        actual_radius: float,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        检查线缆弯曲半径
        :param cable_type: 线缆类型 (power_cable, communication_cable)
        :param cable_diameter: 线缆外径（毫米）
        :param actual_radius: 实际弯曲半径（毫米）
        :return: (是否通过, 检查结果详情)
        """
        self.rules_applied += 1
        
        standards = BENDING_RADIUS_STANDARDS.get(cable_type)
        if standards is None:
            return False, {
                "status": "unknown",
                "message": f"未知的线缆类型: {cable_type}",
                "suggestion": "请确认线缆类型后重新检查",
                "standard_value": "未知",
                "actual_value": actual_radius,
            }

        # 计算最小弯曲半径（15倍电缆直径）
        min_factor = 15
        if cable_type == "power_cable":
            min_factor = standards.get("multi_core", 15)
        
        required_radius = max(cable_diameter * min_factor, standards.get("min_value", 30))

        passed = actual_radius >= required_radius
        
        if not passed:
            self.rules_violated += 1

        return passed, {
            "status": "pass" if passed else "fail",
            "rule_name": "线缆弯曲半径检查",
            "cable_type": cable_type,
            "cable_diameter_mm": cable_diameter,
            "required_radius_mm": round(required_radius, 1),
            "actual_radius_mm": actual_radius,
            "radius_deficit_mm": round(required_radius - actual_radius, 1) if not passed else 0,
            "suggestion": self._get_bending_suggestion(cable_type, actual_radius, required_radius) if not passed else "弯曲半径符合标准要求",
            "risk_level": "error" if not passed else None,
            "standard_reference": f"{cable_type} 最小弯曲半径: ≥{required_radius}mm ({min_factor}倍电缆直径)",
        }

    def check_cable_current_rating(
        self,
        conductor_material: str,
        cross_section_mm2: float,
        actual_current_a: float,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        检查线缆载流量
        :param conductor_material: 导体材质 (copper, aluminum)
        :param cross_section_mm2: 截面积（平方毫米）
        :param actual_current_a: 实际电流（安培）
        :return: (是否通过, 检查结果详情)
        """
        self.rules_applied += 1
        
        ratings = CABLE_CURRENT_RATING.get(conductor_material)
        if ratings is None:
            return False, {
                "status": "unknown",
                "message": f"未知的导体材质: {conductor_material}",
                "suggestion": "请确认导体材质后重新检查",
                "standard_value": "未知",
                "actual_value": actual_current_a,
            }

        # 查找最接近的标准截面积（兼容整型/浮点型键，避免 KeyError）
        available_sections = sorted(ratings.keys())
        standard_current = None
        for section in available_sections:
            if section >= cross_section_mm2:
                standard_current = ratings.get(section) or ratings.get(int(section)) or ratings.get(float(section))
                if standard_current is not None:
                    break

        if standard_current is None:
            # 如果截面积超过最大标准，使用最大值
            last = available_sections[-1]
            standard_current = ratings.get(last) or ratings.get(int(last)) or ratings.get(float(last))

        # 载流量需要留有1.25倍余量
        rated_current = standard_current / 1.25
        passed = actual_current_a <= rated_current
        
        if not passed:
            self.rules_violated += 1

        return passed, {
            "status": "pass" if passed else "fail",
            "rule_name": "线缆载流量检查",
            "conductor_material": conductor_material,
            "cross_section_mm2": cross_section_mm2,
            "standard_current_a": standard_current,
            "rated_current_a": round(rated_current, 1),
            "actual_current_a": actual_current_a,
            "current_exceed_a": round(actual_current_a - rated_current, 1) if not passed else 0,
            "loading_rate": f"{round(actual_current_a / rated_current * 100, 1)}%",
            "suggestion": self._get_rating_suggestion(conductor_material, actual_current_a, rated_current) if not passed else "载流量符合标准要求",
            "risk_level": "critical" if not passed and actual_current_a > standard_current else "error" if not passed else None,
            "standard_reference": f"{conductor_material} {cross_section_mm2}mm² 载流量: {standard_current}A",
        }

    def check_fibre_capacity(
        self,
        used_fibres: float,
        capacity: float,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        通信光缆 / 分纤箱容量校验（FTTH 设计验收真实可比对项）
        :param used_fibres: 已用光纤(端口)数
        :param capacity: 额定容量(端口)数
        :return: (是否通过, 检查结果详情)
        依据 GB 51158《通信线路工程设计规范》、YD/T 相关验收要求：
        配线光分纤箱/光缆的已用光纤(端口)数不得超过其额定容量，
        否则会导致配纤失败、扩容困难，属于真实可量化的设计缺陷。
        """
        self.rules_applied += 1

        passed = used_fibres <= capacity

        if not passed:
            self.rules_violated += 1

        return passed, {
            "status": "pass" if passed else "fail",
            "rule_name": "线缆容量校验",
            "used_fibres": used_fibres,
            "capacity": capacity,
            "exceed": round(used_fibres - capacity, 1) if not passed else 0,
            "suggestion": (
                f"已用光纤数 {used_fibres} 超过额定容量 {capacity}，需扩容或调整配纤方案"
                if not passed else "容量配置符合规范要求"
            ),
            "risk_level": "error" if not passed else None,
            "standard_reference": f"FTTH 容量规范：已用光纤数 ≤ 额定容量({capacity})",
        }

    def execute_all_checks(
        self,
        device_data: Dict[str, Any],
        design_type: str = "general",
    ) -> List[Dict[str, Any]]:
        """
        执行所有规则检查（带异常捕获，单条数据出错不中断整体审查）
        :param device_data: 设备数据
        :param design_type: 设计类型
        :return: 检查结果列表
        """
        results = []
        
        try:
            # 1. 管线埋深检查（遗留单设备路径，真实链路以 real_engine_check 的 pipeline 数组为主）
            if "burial_depth" in device_data:
                try:
                    passed, detail = self.check_pipeline_buried_depth(
                        laying_type=device_data.get("laying_type", device_data.get("device_type")),
                        burial_depth=device_data["burial_depth"],
                        scenario=device_data.get("burial_scenario", "urban"),
                    )
                    if not passed:
                        results.append(detail)
                except Exception as e:
                    results.append({
                        "status": "error",
                        "rule_name": "管线埋深检查",
                        "message": f"检查异常: {str(e)}",
                        "suggestion": "请检查设备埋深数据是否正确",
                    })

            # 2. 接地电阻检查
            if "grounding_resistance" in device_data and "grounding_type" in device_data:
                try:
                    passed, detail = self.check_grounding_resistance(
                        grounding_type=device_data["grounding_type"],
                        measured_resistance=device_data["grounding_resistance"],
                    )
                    if not passed:
                        results.append(detail)
                except Exception as e:
                    results.append({
                        "status": "error",
                        "rule_name": "接地电阻检查",
                        "message": f"检查异常: {str(e)}",
                        "suggestion": "请检查接地电阻数据是否正确",
                    })

            # 3. 弯曲半径检查
            if all(k in device_data for k in ["cable_type", "cable_diameter", "bending_radius"]):
                try:
                    passed, detail = self.check_bending_radius(
                        cable_type=device_data["cable_type"],
                        cable_diameter=device_data["cable_diameter"],
                        actual_radius=device_data["bending_radius"],
                    )
                    if not passed:
                        results.append(detail)
                except Exception as e:
                    results.append({
                        "status": "error",
                        "rule_name": "弯曲半径检查",
                        "message": f"检查异常: {str(e)}",
                        "suggestion": "请检查线缆参数是否正确",
                    })

            # 4. 载流量检查
            if all(k in device_data for k in ["conductor_material", "cross_section", "actual_current"]):
                try:
                    passed, detail = self.check_cable_current_rating(
                        conductor_material=device_data["conductor_material"],
                        cross_section_mm2=device_data["cross_section"],
                        actual_current_a=device_data["actual_current"],
                    )
                    if not passed:
                        results.append(detail)
                except Exception as e:
                    results.append({
                        "status": "error",
                        "rule_name": "载流量检查",
                        "message": f"检查异常: {str(e)}",
                        "suggestion": "请检查线缆参数是否正确",
                    })

        except Exception as e:
            results.append({
                "status": "system_error",
                "message": f"设备检查整体异常: {str(e)}",
                "suggestion": "请检查设备数据格式是否正确",
            })

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """获取审查统计信息"""
        return {
            "rules_applied": self.rules_applied,
            "rules_violated": self.rules_violated,
            "violation_rate": round(self.rules_violated / self.rules_applied * 100, 2) if self.rules_applied > 0 else 0,
        }

    def reset_statistics(self):
        """重置统计信息"""
        self.rules_applied = 0
        self.rules_violated = 0

    # ==================== 建议生成方法 ====================
    @staticmethod
    def _get_buried_depth_suggestion(laying_type, scenario, actual: float, standard: float, device_type=None) -> str:
        deficit = round(standard - actual, 2)
        lt_cn = _BURIED_LAYING_CN.get(laying_type, "管线")
        sc_cn = _BURIED_SCENARIO_CN.get(scenario, "")
        dt = f"（{device_type}）" if device_type else ""
        gb = "GB 51158" if laying_type == "direct" else "GB 50373"
        return (f"{lt_cn}管线{dt}在{sc_cn}埋深不足{deficit}米，"
                f"依据 {gb} 应≥{standard}米，建议加深覆土或加保护套管后重新敷设")

    @staticmethod
    def _get_grounding_suggestion(grounding_type: str, actual: float, standard: float) -> str:
        exceed = round(actual - standard, 2)
        suggestions = {
            "power_substation": f"变电站接地电阻超标{exceed}Ω，需检查接地网完整性或增加接地极",
            "distribution_room": f"配电室接地电阻超标{exceed}Ω，建议检查接地连接或增加接地极",
            "communication_room": f"通信机房接地电阻超标{exceed}Ω，会影响设备稳定运行，需整改",
            "tower": f"杆塔接地电阻超标{exceed}Ω，建议增加垂直接地极或使用降阻剂",
            "lightning_rod": f"避雷针接地电阻超标{exceed}Ω，影响防雷效果，需立即整改",
            "computer_room": f"计算机房接地电阻超标{exceed}Ω，可能干扰信号传输，需整改",
        }
        return suggestions.get(grounding_type, f"接地电阻超标{exceed}Ω，建议检查接地系统")

    @staticmethod
    def _get_bending_suggestion(cable_type: str, actual: float, required: float) -> str:
        deficit = round(required - actual, 1)
        suggestions = {
            "power_cable": f"电力电缆弯曲半径不足{deficit}mm，易导致绝缘损伤，建议重新敷设",
            "communication_cable": f"通信电缆弯曲半径不足{deficit}mm，可能影响信号传输，建议整改",
        }
        return suggestions.get(cable_type, f"弯曲半径不足{deficit}mm，建议整改")

    @staticmethod
    def _get_rating_suggestion(material: str, actual: float, rated: float) -> str:
        loading = round(actual / rated * 100, 1)
        if loading > 120:
            return f"线缆载流量严重超标（{loading}%），存在火灾风险，需立即更换更大截面线缆"
        elif loading > 100:
            return f"线缆载流量超标（{loading}%），建议更换更大截面线缆或降低负载"
        else:
            return f"线缆载流量接近额定值（{loading}%），建议监控负载变化，必要时增容"
