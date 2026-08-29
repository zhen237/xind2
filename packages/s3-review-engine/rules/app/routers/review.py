from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from app.schemas.review import ReviewCheckRequest, ReviewCheckResponse, ReviewResultItem, ApiResponse
from app.utils.rule_engine import ReviewRuleEngine
from datetime import datetime
import logging
import time
import traceback

router = APIRouter()

# 初始化规则引擎
rule_engine = ReviewRuleEngine()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

RULES_DATA = {
    'EL-001': {'rule_id': 1, 'rule_name': '电缆敷设弯曲半径检查', 'category': '电力', 'threshold': '弯曲半径>=15倍电缆直径', 'risk_level': 'critical', 'suggestion': '电缆弯曲半径不足会导致绝缘层破裂，需重新敷设保证最小弯曲半径要求'},
    'EL-002': {'rule_id': 2, 'rule_name': '电缆截面选型校验', 'category': '电力', 'threshold': '载流量>=计算电流的1.25倍', 'risk_level': 'error', 'suggestion': '电缆截面偏小会导致过热，需根据负载计算重新选型'},
    'EL-003': {'rule_id': 3, 'rule_name': '接地电阻测量', 'category': '电力', 'threshold': '接地电阻<=4欧姆', 'risk_level': 'critical', 'suggestion': '接地电阻超标会影响防雷效果和设备安全，需增加接地极或降低土壤电阻率'},
    'EL-004': {'rule_id': 4, 'rule_name': '绝缘子污秽等级匹配', 'category': '电力', 'threshold': '污秽等级与环境匹配', 'risk_level': 'warning', 'suggestion': '绝缘子污秽等级不匹配可能导致闪络，建议定期清扫或更换'},
    'EL-005': {'rule_id': 5, 'rule_name': '开关设备耐压试验', 'category': '电力', 'threshold': '耐压值>=1.5倍额定电压', 'risk_level': 'critical', 'suggestion': '耐压试验不合格说明设备绝缘存在缺陷，需检修或更换'},
    'EL-006': {'rule_id': 6, 'rule_name': '变压器油位检查', 'category': '电力', 'threshold': '油位在标准刻度范围内', 'risk_level': 'warning', 'suggestion': '油位异常可能影响散热或存在渗漏，需检查并处理'},
    'EL-007': {'rule_id': 7, 'rule_name': '继电保护定值校验', 'category': '电力', 'threshold': '定值与计算书一致', 'risk_level': 'error', 'suggestion': '保护定值错误会导致误动或拒动，需重新核算并整定'},
    'EL-008': {'rule_id': 8, 'rule_name': '母线搭接面检查', 'category': '电力', 'threshold': '接触电阻<=200微欧', 'risk_level': 'error', 'suggestion': '接触电阻过大会导致发热，需重新处理接触面'},
    'LP-001': {'rule_id': 9, 'rule_name': '避雷针高度校验', 'category': '防雷', 'threshold': '保护范围覆盖所有保护对象', 'risk_level': 'critical', 'suggestion': '避雷针高度不足会导致保护范围不够，需加高避雷针或增加数量'},
    'LP-002': {'rule_id': 10, 'rule_name': '防雷引下线连续性', 'category': '防雷', 'threshold': '引下线连续无断点', 'risk_level': 'critical', 'suggestion': '引下线断裂会导致雷电流无法入地，需修复断点'},
    'LP-003': {'rule_id': 11, 'rule_name': 'SPD选型匹配', 'category': '防雷', 'threshold': 'SPD参数与系统匹配', 'risk_level': 'error', 'suggestion': 'SPD选型不当会导致保护失效或误动作，需重新选型'},
    'LP-004': {'rule_id': 12, 'rule_name': '接地网网格尺寸', 'category': '防雷', 'threshold': '网格尺寸<=5m×5m', 'risk_level': 'warning', 'suggestion': '网格尺寸偏大影响散流效果，建议减小网格尺寸'},
    'LP-005': {'rule_id': 13, 'rule_name': '等电位连接完整性', 'category': '防雷', 'threshold': '所有金属构件可靠连接', 'risk_level': 'error', 'suggestion': '等电位连接不完整会形成电位差，需补充连接'},
    'ST-001': {'rule_id': 14, 'rule_name': '基础承载力验算', 'category': '结构', 'threshold': '承载力>=设计荷载的1.2倍', 'risk_level': 'critical', 'suggestion': '基础承载力不足会导致沉降，需加固基础或减小荷载'},
    'ST-002': {'rule_id': 15, 'rule_name': '钢结构焊缝探伤', 'category': '结构', 'threshold': '焊缝探伤合格率>=98%', 'risk_level': 'error', 'suggestion': '焊缝缺陷会影响结构强度，需补焊或更换'},
    'ST-003': {'rule_id': 16, 'rule_name': '混凝土强度检测', 'category': '结构', 'threshold': '强度>=设计等级', 'risk_level': 'error', 'suggestion': '混凝土强度不足会影响结构安全，需加固或重建'},
    'ST-004': {'rule_id': 17, 'rule_name': '构件变形监测', 'category': '结构', 'threshold': '变形量<=允许值', 'risk_level': 'warning', 'suggestion': '构件变形超限需分析原因并采取加固措施'},
    'EM-001': {'rule_id': 18, 'rule_name': '电磁辐射强度测量', 'category': '电磁', 'threshold': '辐射强度<=国家标准限值', 'risk_level': 'warning', 'suggestion': '电磁辐射超标可能影响人员健康，需采取屏蔽措施'},
    'EM-002': {'rule_id': 19, 'rule_name': '无线电干扰测试', 'category': '电磁', 'threshold': '干扰值<=允许限值', 'risk_level': 'warning', 'suggestion': '无线电干扰超标会影响通信质量，需排查干扰源'},
    'EM-003': {'rule_id': 20, 'rule_name': '静电放电防护', 'category': '电磁', 'threshold': '静电电位<=1000V', 'risk_level': 'error', 'suggestion': '静电电位过高可能损坏电子设备，需增加防静电措施'},
    'CM-001': {'rule_id': 21, 'rule_name': '消防安全设施检查', 'category': '通用', 'threshold': '消防设施完好有效', 'risk_level': 'critical', 'suggestion': '消防设施失效会影响应急处理能力，需修复或更换'},
    'CM-002': {'rule_id': 22, 'rule_name': '通风系统检查', 'category': '通用', 'threshold': '通风量>=设计要求', 'risk_level': 'warning', 'suggestion': '通风不足会导致室内空气质量下降，需优化通风系统'},
    'CM-003': {'rule_id': 23, 'rule_name': '照明照度检测', 'category': '通用', 'threshold': '照度>=国家标准', 'risk_level': 'warning', 'suggestion': '照度不足影响工作效率，需增加照明设备'},
    'GD-001': {'rule_id': 24, 'rule_name': '管线埋深检查', 'category': '管线', 'threshold': '直埋(城区≥0.8m/郊外≥1.0m)；管道(城区≥0.8m/郊外≥0.5m)', 'risk_level': 'warning', 'suggestion': '管线埋深不足会导致外力破坏、冻胀或腐蚀损伤，需加深覆土或加保护套管后重新敷设'},
}

# ============================================================================
# 规则库口径说明（重要）
# RULES_DATA 为「行业规范审查规则库」，共 24 条，与数据库 s3_safety_rule 完全一致：
#   电力 EL-001~008(8)、防雷 LP-001~005(5)、结构 ST-001~004(4)、电磁 EM-001~003(3)、通用 CM-001~003(3)、管线 GD-001(1)
# FT-001（光缆/分纤箱容量校验）是「基于真实工程数据的附加校验项」：
#   - 对应真实数据具备的光纤容量字段(capacity / fibreUsed)，由 Java 侧以内存附加项形式下发引擎；
#   - 不写入本规则库（故本库严格保持 23 条，与数据库对齐），其校验映射见 REAL_CHECK_MAP，
#     校验实现见 rule_engine.check_fibre_capacity。
#   - 保留真实违规产出能力（如光分纤箱已用光纤数 > 额定容量），绝不随机造假。
# ============================================================================

# ==================== 规则与真实参数化校验的接线映射 ====================
# 仅对具备可量化设计参数、可由公式比对的规则进行真实校验（见 REAL_CHECK_MAP 与下方 B5_RULES）。
# B-5 已为库内其余 20 条规则（EL-004~008/LP-001~005/ST-001~004/EM-001~003/CM-001~003）补齐真实参数化模型，
# 参数取自 device['params']（S1DesignDataDTO 既有 Map 兜底字段，无需改动 S1 对接代码），缺参一律标记 pending，绝不造假。
REAL_CHECK_MAP = {
    'EL-001': 'bending_radius',        # 电缆敷设弯曲半径检查
    'EL-002': 'current_rating',        # 电缆截面选型校验（载流量）
    'EL-003': 'grounding_resistance',  # 接地电阻测量
    'FT-001': 'fibre_capacity',         # 光缆/分纤箱容量校验（真实通信数据可比对项）
    'GD-001': 'buried_depth',           # 管线埋深检查（直埋/管道 × 城区/郊外，依据 GB 51158/GB 50373）

    # ===== B-5 规则库扩充（增量新增，20 条库内规则）：真实参数化校验映射 =====
    # 校验实现见下方 _real_engine_check_b5 / B5_RULES；参数取自 device['params']，缺参标记 pending。
    'EL-004': 'b5_insulator_pollution',
    'EL-005': 'b5_switch_withstand',
    'EL-006': 'b5_transformer_oil',
    'EL-007': 'b5_protection_setting',
    'EL-008': 'b5_busbar_contact',
    'LP-001': 'b5_lightning_rod_height',
    'LP-002': 'b5_down_conductor',
    'LP-003': 'b5_spd_matching',
    'LP-004': 'b5_ground_grid',
    'LP-005': 'b5_equipotential',
    'ST-001': 'b5_foundation_bearing',
    'ST-002': 'b5_weld_inspection',
    'ST-003': 'b5_concrete_strength',
    'ST-004': 'b5_member_deformation',
    'EM-001': 'b5_em_radiation',
    'EM-002': 'b5_radio_interference',
    'EM-003': 'b5_static_discharge',
    'CM-001': 'b5_fire_facility',
    'CM-002': 'b5_ventilation',
    'CM-003': 'b5_illumination',
}

# 设备 deviceType -> 接地电阻 grounding_type 枚举
# 修复原实现中直接把 deviceType(如 cable/transformer) 当作 grounding_type 传入，
# 导致落入 unknown 分支产生虚假违规的问题。
GROUNDING_TYPE_MAP = {
    'tower': 'tower',
    'lightning_rod': 'lightning_rod',
    'transformer': 'distribution_room',
    'substation': 'power_substation',
    'power_substation': 'power_substation',
    'distribution_room': 'distribution_room',
    'communication_room': 'communication_room',
    'computer_room': 'computer_room',
    'equipment': 'equipment',
    # 电缆、管道等无独立接地要求，不参与接地电阻判定
    'cable': None,
    'pipe': None,
    'power_cable': None,
    'communication_cable': None,
}

# 设备 deviceType -> 线缆类型枚举（供弯曲半径校验使用）
CABLE_TYPE_MAP = {
    'power_cable': 'power_cable',
    'cable': 'power_cable',
    'copper_cable': 'power_cable',
    'communication_cable': 'communication_cable',
    'comm_cable': 'communication_cable',
    'optical': 'communication_cable',
}

# 材质映射（供载流量校验使用）
MATERIAL_MAP = {
    'copper': 'copper',
    '铜': 'copper',
    'Cu': 'copper',
    'aluminum': 'aluminum',
    '铝': 'aluminum',
    'Al': 'aluminum',
}


def _parse_coordinates(device):
    """解析设备坐标（兼容 list 或 JSON 字符串），最多取3个值"""
    if not isinstance(device, dict):
        return []
    raw = device.get('coordinates')
    if isinstance(raw, list):
        try:
            return [float(x) for x in raw][:3]
        except (ValueError, TypeError):
            return []
    if isinstance(raw, str):
        try:
            s = raw.strip()
            if s.startswith('['):
                s = s[1:]
            if s.endswith(']'):
                s = s[:-1]
            parts = [float(x) for x in s.split(',') if x.strip() != '']
            return parts[:3]
        except (ValueError, TypeError):
            return []
    return []


def _safe_float(value):
    """安全转 float：None/空串/非数字返回 None；合法数值原样返回（符号合法性交由调用方判断）"""
    if value is None or value == '':
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _to_result(item, rule_config, detail, device):
    """将引擎校验详情转换为统一结果项（违规）"""
    value_keys = {
        '接地电阻检查': ('measured_resistance_ohm', 'standard_resistance_ohm'),
        '线缆弯曲半径检查': ('actual_radius_mm', 'required_radius_mm'),
        '线缆载流量检查': ('actual_current_a', 'rated_current_a'),
        '线缆容量校验': ('used_fibres', 'capacity'),
        '管线埋深检查': ('actual_depth_m', 'standard_depth_m'),
    }
    check_name = detail.get('rule_name', '')
    actual_key, standard_key = value_keys.get(check_name, (None, None))

    if check_name == '线缆容量校验':
        # 容量校验：直观呈现"已用/额定"对比，便于报告页直接展示国标阈值比对
        # 依据 GB 51158《通信线路工程设计规范》——已用光纤(端口)数不得超过额定容量
        actual_value = f"已用 {detail.get('used_fibres')} 芯"
        standard_value = f"额定容量 {detail.get('capacity')} 芯"
        checked_value = detail.get('used_fibres')
    elif check_name == '管线埋深检查':
        # 埋深校验：标注敷设方式 + 场景 + 实测/国标标准值，便于报告页直接呈现
        # 依据 GB 51158(直埋)/GB 50373(管道) 差异化最小埋深阈值
        lt_cn = detail.get('laying_type_cn', '')
        sc_cn = detail.get('scenario_cn', '')
        actual_value = f"{lt_cn}({sc_cn}) 实测 {detail.get('actual_depth_m')}m"
        standard_value = f"标准 ≥{detail.get('standard_depth_m')}m"
        checked_value = detail.get('actual_depth_m')
    else:
        actual_value = str(detail.get(actual_key)) if (actual_key and detail.get(actual_key) is not None) else ''
        standard_value = str(detail.get(standard_key)) if (standard_key and detail.get(standard_key) is not None) else ''
        checked_value = detail.get(actual_key) if actual_key else None

    rule_name = item.rule_name or (rule_config['rule_name'] if rule_config else check_name)
    category = item.category or (rule_config['category'] if rule_config else '')
    # 风险等级以规则管理页面定义的业务风险为准
    risk_level = item.risk_level or (rule_config['risk_level'] if rule_config else 'warning')
    suggestion = detail.get('suggestion') or (rule_config['suggestion'] if rule_config else '')

    return ReviewResultItem(
        rule_id=item.rule_id,
        rule_code=item.rule_code,
        rule_name=rule_name,
        category=category,
        actual_value=actual_value,
        standard_value=standard_value,
        coordinates=_parse_coordinates(device),
        risk_level=risk_level,
        suggestion=suggestion,
        standard_param=detail.get('standard_reference', ''),
        device_type=device.get('deviceType') if isinstance(device, dict) else None,
        checked_value=checked_value,
        passed=False,
        check_time=datetime.now().isoformat(),
    )


def _to_pending_result(item, rule_config, message, related_count):
    """
    生成「待核查」结果项：规则应具备可量化参数，但 S1 设计数据缺失 / 异常，
    无法依据行业规范做出通过或违规的判定，故标记为 pending（待核查），
    写入审查报告，提示人工复核设计图纸，而非静默跳过、亦不伪造违规。

    注意：pending 不计入 critical/error/warning 违规统计（Java 侧仅对这三种枚举计数），
    仅作为数据可用性缺口的如实呈现。
    """
    rule_name = item.rule_name or (rule_config['rule_name'] if rule_config else '')
    category = item.category or (rule_config['category'] if rule_config else '')
    threshold = rule_config['threshold'] if rule_config else ''

    return ReviewResultItem(
        rule_id=item.rule_id,
        rule_code=item.rule_code,
        rule_name=rule_name,
        category=category,
        actual_value='参数缺失/异常',
        standard_value='—',
        coordinates=[],
        risk_level='pending',
        suggestion=f"【待核查】{message}（涉及设备 {related_count} 个）",
        standard_param=threshold,
        device_type=None,
        checked_value=None,
        passed=None,
        check_time=datetime.now().isoformat(),
    )


def _check_buried_depth(item, rule_config, design_data):
    """
    管线埋深真实校验：数据源为 design_data['pipeline'] 数组（与 devices 分离）。
    从每条管线提取 敷设方式(layingType)/场景(scenario)/实测埋深(burialDepth)；
    缺失关键参数 → 计入 missing，全部缺失则标记 pending（待核查），不伪造违规。
    """
    pipeline = design_data.get('pipeline')
    if not pipeline or not isinstance(pipeline, list):
        return None

    related = 0
    missing = 0
    for pipe in pipeline:
        if not isinstance(pipe, dict):
            continue
        related += 1
        laying = pipe.get('layingType') if pipe.get('layingType') is not None else pipe.get('laying_type')
        scenario = pipe.get('scenario') if pipe.get('scenario') is not None else pipe.get('burialScenario')
        depth = _safe_float(pipe.get('burialDepth') if pipe.get('burialDepth') is not None else pipe.get('burial_depth'))
        if laying is None or scenario is None or depth is None or depth <= 0:
            missing += 1
            continue
        passed, detail = rule_engine.check_pipeline_buried_depth(
            laying_type=laying,
            burial_depth=depth,
            scenario=scenario,
        )
        if not passed:
            return _to_result(item, rule_config, detail, pipe)

    if related > 0 and missing == related:
        return _to_pending_result(
            item, rule_config,
            f"共 {related} 条管线记录，未提供埋深(burialDepth)/敷设方式(layingType)/场景(scenario)参数，"
            f"依据 GB 51158(直埋)/GB 50373(管道) 管线最小埋深应≥0.5~1.0m，参数缺失无法判定合规性",
            related)
    return None


# ============================================================================
# B-5 规则库扩充：为库内其余 20 条规则补齐真实参数化校验模型
# （EL-004~008 / LP-001~005 / ST-001~004 / EM-001~003 / CM-001~003）
# 设计要点：
#   1) 严格增量新增，不改动已有 5 条真实校验(EL-001/002/003/FT-001)与埋深校验(GD-001)；
#   2) 参数取自 device['params']（S1DesignDataDTO 既有 Map 兜底字段，无需改动 S1 对接代码），
#      站点级规则(LP-004)取自 design_data['groundGrid']；
#   3) 设计数据缺少对应参数字段 → 标记 pending(待核查)，绝不生成虚假违规；
#   4) 阈值依据通信/电力/建筑等行业现行国标（GB 50057/GB 50205/GB 50016/GB 50034 等），
#      为可复核的硬性技术条款；缺参不造假。
# 运算符：ge(实测≥阈值) / le(实测≤阈值) / rel(相对偏差) / enum(枚举) / compound(复合)
# 阈值因子：limit = base × factor（如 EL-005 耐压=1.5×额定电压，ST-001 承载力=1.2×设计荷载）
# ============================================================================
B5_RULES = {
    'EL-004': {'name': '绝缘子污秽等级匹配', 'gb': 'GB/T 26218.1-2010', 'kind': 'ge',
               'actual': 'insulatorLevel', 'base': 'requiredPollutionLevel', 'factor': 1.0,
               'unit': '级', 'actual_label': '绝缘子污秽等级', 'std_desc': '污秽等级应≥所处环境污区等级',
               'fix': '建议按污区等级提高绝缘配置或加强清扫'},
    'EL-005': {'name': '开关设备耐压试验', 'gb': 'GB 50150-2016', 'kind': 'ge',
               'actual': 'withstandVoltage', 'base': 'ratedVoltage', 'factor': 1.5,
               'unit': 'kV', 'actual_label': '耐压试验值', 'std_desc': '耐压值应≥1.5倍额定电压',
               'fix': '需检修绝缘缺陷或更换设备'},
    'EL-006': {'name': '变压器油位检查', 'gb': 'GB/T 6451-2015', 'kind': 'ge',
               'actual': 'oilLevelPercent', 'limit_const': 20,
               'unit': '%', 'actual_label': '油位', 'std_desc': '油位应≥标准下限(20%)',
               'fix': '需检查渗漏并补油至标准刻度'},
    'EL-007': {'name': '继电保护定值校验', 'gb': 'DL/T 587-2016', 'kind': 'rel',
               'actual': 'protectionSettingActual', 'base': 'protectionSettingComputed', 'tol': 0.05},
    'EL-008': {'name': '母线搭接面检查', 'gb': 'GB 50149-2010', 'kind': 'le',
               'actual': 'contactResistance', 'limit_const': 200,
               'unit': 'μΩ', 'actual_label': '母线接触电阻', 'std_desc': '接触电阻应≤200μΩ',
               'fix': '需重新处理搭接面降低接触电阻'},
    'LP-001': {'name': '避雷针高度校验', 'gb': 'GB 50057-2010', 'kind': 'ge',
               'actual': 'rodHeight', 'base': 'requiredRodHeight', 'factor': 1.0,
               'unit': 'm', 'actual_label': '避雷针高度', 'std_desc': '保护高度应≥被保护物要求高度',
               'fix': '需加高避雷针或增补接闪装置'},
    'LP-002': {'name': '防雷引下线连续性', 'gb': 'GB 50057-2010', 'kind': 'le',
               'actual': 'downConductorResistance', 'limit_const': 0.2,
               'unit': 'Ω', 'actual_label': '引下线回路电阻', 'std_desc': '引下线连续性电阻应≤0.2Ω',
               'fix': '需修复断点恢复电气连通'},
    'LP-003': {'name': 'SPD选型匹配', 'gb': 'GB 50057-2010', 'kind': 'compound'},
    'LP-004': {'name': '接地网网格尺寸', 'gb': 'GB 50057-2010', 'kind': 'le_site',
               'limit_const': 5, 'unit': 'm', 'actual_label': '接地网网格边长',
               'std_desc': '接地网网格尺寸应≤5m×5m', 'fix': '需减小网格尺寸改善散流'},
    'LP-005': {'name': '等电位连接完整性', 'gb': 'GB 50057-2010', 'kind': 'le',
               'actual': 'equipotentialResistance', 'limit_const': 0.1,
               'unit': 'Ω', 'actual_label': '等电位联结电阻', 'std_desc': '等电位联结电阻应≤0.1Ω',
               'fix': '需补充等电位联结消除电位差'},
    'ST-001': {'name': '基础承载力验算', 'gb': 'GB 50007-2011', 'kind': 'ge',
               'actual': 'bearingCapacity', 'base': 'designLoad', 'factor': 1.2,
               'unit': 'kPa', 'actual_label': '地基承载力', 'std_desc': '承载力应≥1.2倍设计荷载',
               'fix': '需加固基础或减小上部荷载'},
    'ST-002': {'name': '钢结构焊缝探伤', 'gb': 'GB 50205-2020', 'kind': 'ge',
               'actual': 'weldPassRate', 'limit_const': 98,
               'unit': '%', 'actual_label': '焊缝探伤合格率', 'std_desc': '焊缝探伤合格率应≥98%',
               'fix': '需对不合格焊缝补焊或更换'},
    'ST-003': {'name': '混凝土强度检测', 'gb': 'GB 50204-2015', 'kind': 'ge',
               'actual': 'concreteStrengthActual', 'base': 'concreteStrengthDesign', 'factor': 1.0,
               'unit': 'MPa', 'actual_label': '混凝土强度', 'std_desc': '强度应≥设计等级',
               'fix': '需加固或重建不合格构件'},
    'ST-004': {'name': '构件变形监测', 'gb': 'GB 50205-2020', 'kind': 'le',
               'actual': 'deformationActual', 'base': 'deformationLimit', 'factor': 1.0,
               'unit': 'mm', 'actual_label': '构件变形量', 'std_desc': '变形量应≤允许值',
               'fix': '需分析原因并加固'},
    'EM-001': {'name': '电磁辐射强度测量', 'gb': 'GB 8702-2014', 'kind': 'le',
               'actual': 'emRadiation', 'base': 'emLimit', 'factor': 1.0,
               'unit': '', 'actual_label': '电磁辐射强度', 'std_desc': '辐射强度应≤国标限值',
               'fix': '需采取屏蔽/隔离措施'},
    'EM-002': {'name': '无线电干扰测试', 'gb': 'GB 7349-2002', 'kind': 'le',
               'actual': 'radioInterference', 'base': 'radioLimit', 'factor': 1.0,
               'unit': 'dBμV/m', 'actual_label': '无线电干扰', 'std_desc': '干扰值应≤允许限值',
               'fix': '需排查并消除干扰源'},
    'EM-003': {'name': '静电放电防护', 'gb': 'GB 50054-2011', 'kind': 'le',
               'actual': 'staticPotential', 'limit_const': 1000,
               'unit': 'V', 'actual_label': '静电电位', 'std_desc': '静电电位应≤1000V',
               'fix': '需增加防静电接地与措施'},
    'CM-001': {'name': '消防安全设施检查', 'gb': 'GB 50016-2014', 'kind': 'enum', 'actual': 'fireFacilityStatus'},
    'CM-002': {'name': '通风系统检查', 'gb': 'GB 50019-2015', 'kind': 'ge',
               'actual': 'ventilationRateActual', 'base': 'ventilationRateRequired', 'factor': 1.0,
               'unit': '', 'actual_label': '通风量', 'std_desc': '通风量应≥设计要求',
               'fix': '需优化通风系统提高风量'},
    'CM-003': {'name': '照明照度检测', 'gb': 'GB 50034-2013', 'kind': 'ge',
               'actual': 'illuminanceActual', 'base': 'illuminanceStandard', 'factor': 1.0,
               'unit': 'lx', 'actual_label': '照度', 'std_desc': '照度应≥国家标准',
               'fix': '需增加或调整照明设备'},
}


def _b5_param_hint(rule_code, cfg):
    """生成该规则「缺失参数」提示文案，供 pending 说明使用。"""
    kind = cfg['kind']
    if kind == 'compound':
        return 'spdUc/systemVoltage/spdIn'
    if kind == 'enum':
        return cfg['actual']
    if kind == 'rel':
        return f"{cfg['actual']}/{cfg['base']}"
    if rule_code == 'LP-004':
        return 'groundGrid.gridX/gridY'
    keys = cfg['actual']
    if cfg.get('base'):
        keys += '/' + cfg['base']
    return keys


def _b5_detail(rule_code, cfg, actual_text, standard_text, standard_reference, suggestion, checked_value):
    """组装 B-5 校验详情字典。"""
    return {
        'rule_name': cfg['name'],
        'actual_text': actual_text,
        'standard_text': standard_text,
        'standard_reference': standard_reference,
        'suggestion': suggestion,
        'checked_value': checked_value,
    }


def _eval_b5(rule_code, params):
    """
    B-5 单规则求值：返回 (passed, detail) 或 None(参数缺失/异常)。
    阈值全部依据行业国标，缺参返回 None（由调用方标记 pending），绝不造假。
    """
    cfg = B5_RULES[rule_code]
    kind = cfg['kind']

    # 枚举型：消防设施状态
    if kind == 'enum':
        val = params.get(cfg['actual'])
        if val is None:
            return None
        ok_set = ('normal', 'intact', 'ok', '有效', '正常')
        passed = str(val).strip().lower() in ok_set
        return passed, _b5_detail(
            rule_code, cfg,
            actual_text=f"消防设施状态={val}",
            standard_text="依据 GB 50016 消防设施应完好有效",
            standard_reference="GB 50016《建筑设计防火规范》",
            suggestion=(f"消防设施状态为「{val}」非完好有效，影响应急处置，需修复或更换"
                        if not passed else "消防设施完好有效"),
            checked_value=None)

    # 相对偏差型：继电保护定值（实测与计算书偏差≤5%）
    if kind == 'rel':
        base = _safe_float(params.get(cfg['base']))
        actual = _safe_float(params.get(cfg['actual']))
        if actual is None or base is None or base == 0:
            return None
        passed = abs(actual - base) / abs(base) <= cfg['tol']
        pct = int(cfg['tol'] * 100)
        return passed, _b5_detail(
            rule_code, cfg,
            actual_text=f"定值实测 {actual} / 计算书 {base}",
            standard_text=f"依据 DL/T 587 定值偏差应≤{pct}%",
            standard_reference="DL/T 587《继电保护定值管理规定》",
            suggestion=(f"保护定值实测 {actual} 与计算书 {base} 偏差超 {pct}%，会导致误动/拒动，需重新整定"
                        if not passed else "定值与计算书一致"),
            checked_value=actual)

    # 复合型：SPD 选型（Uc≥1.15×系统电压 且 In≥5kA）
    if kind == 'compound':
        uc = _safe_float(params.get('spdUc'))
        usys = _safe_float(params.get('systemVoltage'))
        inn = _safe_float(params.get('spdIn'))
        if uc is None or usys is None or inn is None:
            return None
        passed = (uc >= 1.15 * usys) and (inn >= 5.0)
        return passed, _b5_detail(
            rule_code, cfg,
            actual_text=f"SPD Uc={uc}V / In={inn}kA；系统电压={usys}V",
            standard_text="依据 GB 50057 SPD 应选 Uc≥1.15Uac 且 In≥5kA",
            standard_reference="GB 50057《建筑物防雷设计规范》",
            suggestion=(f"SPD 参数不匹配（Uc 应≥{1.15 * usys:.1f}V 且 In≥5kA），保护可能失效，需重新选型"
                        if not passed else "SPD 选型与系统匹配"),
            checked_value=uc)

    # 数值比较型：ge(≥阈值) / le(≤阈值)
    actual = _safe_float(params.get(cfg['actual']))
    if actual is None:
        return None
    limit = cfg.get('limit_const')
    if limit is None:
        base = _safe_float(params.get(cfg['base']))
        if base is None:
            return None
        limit = base * cfg.get('factor', 1.0)
    if kind == 'ge':
        passed = actual >= limit
        op_sym = '≥'
    else:  # le / le_site
        passed = actual <= limit
        op_sym = '≤'
    unit = cfg.get('unit', '')
    actual_text = f"{cfg['actual_label']}实测 {actual}{unit}"
    std_text = f"依据 {cfg['gb']} {cfg['std_desc']}（{op_sym}{limit}{unit}）"
    suggestion = (f"{cfg['actual_label']}实测 {actual}{unit} 不满足 {cfg['gb']} 要求（应{op_sym}{limit}{unit}），{cfg.get('fix', '需整改')}"
                  if not passed else f"{cfg['actual_label']}满足 {cfg['gb']} 要求")
    return passed, _b5_detail(
        rule_code, cfg,
        actual_text=actual_text,
        standard_text=std_text,
        standard_reference=f"{cfg['gb']}：{cfg['std_desc']}",
        suggestion=suggestion,
        checked_value=actual)


def _to_result_b5(item, rule_config, detail, device):
    """将 B-5 校验详情转换为统一结果项（违规）。"""
    rule_name = item.rule_name or (rule_config['rule_name'] if rule_config else detail.get('rule_name', ''))
    category = item.category or (rule_config['category'] if rule_config else '')
    risk_level = item.risk_level or (rule_config['risk_level'] if rule_config else 'warning')
    suggestion = detail.get('suggestion') or (rule_config['suggestion'] if rule_config else '')
    return ReviewResultItem(
        rule_id=item.rule_id,
        rule_code=item.rule_code,
        rule_name=rule_name,
        category=category,
        actual_value=detail.get('actual_text', ''),
        standard_value=detail.get('standard_text', ''),
        coordinates=_parse_coordinates(device) if device else [],
        risk_level=risk_level,
        suggestion=suggestion,
        standard_param=detail.get('standard_reference', ''),
        device_type=device.get('deviceType') if isinstance(device, dict) else None,
        checked_value=detail.get('checked_value'),
        passed=False,
        check_time=datetime.now().isoformat(),
    )


def _real_engine_check_b5(item, rule_config, design_data):
    """
    B-5 规则真实校验调度：站点级(LP-004)与设备级分别处理；
    参数齐全→真实国标比对；缺参→pending(待核查)；绝不生成虚假违规。
    """
    rule_code = item.rule_code
    cfg = B5_RULES.get(rule_code)
    if not cfg:
        return None

    # 站点级：接地网网格尺寸（取自 design_data['groundGrid']；缺省回退 design_data['extraData']['groundGrid']）
    if rule_code == 'LP-004':
        grid = design_data.get('groundGrid')
        # 注：design_data 可能含 groundGrid 键但值为空 dict（上游未真正提供），
        # 此时应回退到 extraData.groundGrid，而非把空 dict 当成合法输入（否则会误判 pending）。
        if not isinstance(grid, dict) or not grid:
            extra = design_data.get('extraData') or {}
            grid = extra.get('groundGrid') or {}
        gx = _safe_float(grid.get('gridX'))
        gy = _safe_float(grid.get('gridY'))
        candidates = [v for v in (gx, gy) if v is not None]
        if not candidates:
            hint = _b5_param_hint(rule_code, cfg)
            return _to_pending_result(
                item, rule_config,
                f"设计数据未提供「{cfg['name']}」所需参数（如 {hint}），依据 {cfg['gb']} 无法判定合规性", 1)
        actual = max(candidates)
        limit = cfg['limit_const']
        passed = actual <= limit
        detail = _b5_detail(
            rule_code, cfg,
            actual_text=f"接地网网格边长实测 {actual}{cfg['unit']}",
            standard_text=f"依据 {cfg['gb']} {cfg['std_desc']}（≤{limit}{cfg['unit']}）",
            standard_reference=f"{cfg['gb']}：{cfg['std_desc']}",
            suggestion=(f"接地网网格边长 {actual}{cfg['unit']} 超过 {limit}{cfg['unit']}，影响散流效果，需减小网格尺寸"
                        if not passed else f"接地网网格尺寸满足 {cfg['gb']} 要求"),
            checked_value=actual)
        return None if passed else _to_result_b5(item, rule_config, detail, None)

    # 设备级：遍历全部设备，提取 device['params'] 中的专属参数
    devices = design_data.get('devices')
    if not devices or not isinstance(devices, list):
        return None
    related = 0
    missing = 0
    for device in devices:
        if not isinstance(device, dict):
            continue
        related += 1
        params = device.get('params') or {}
        res = _eval_b5(rule_code, params)
        if res is None:
            missing += 1
            continue
        passed, detail = res
        if not passed:
            return _to_result_b5(item, rule_config, detail, device)

    # 规则适用设备存在，但全部缺失/异常参数 → 待核查（不计入违规，如实呈现数据缺口）
    if related > 0 and missing == related:
        hint = _b5_param_hint(rule_code, cfg)
        msg = f"设计数据未提供「{cfg['name']}」所需参数（如 {hint}），依据 {cfg['gb']} 无法判定合规性"
        return _to_pending_result(item, rule_config, msg, related)
    return None


def real_engine_check(item, rule_config, design_data=None):
    """
    真实参数化校验：根据规则编号调用对应的引擎校验函数，
    仅当设计参数不满足行业规范阈值时才产生违规项，绝不随机生成。
    """
    if design_data is None or not isinstance(design_data, dict):
        return None

    rule_code = item.rule_code
    check_type = REAL_CHECK_MAP.get(rule_code)
    if not check_type:
        # 该规则当前无对应可量化校验函数，不产生违规（杜绝随机造假）
        return None

    # B-5 规则库扩充（增量新增）：库内其余 20 条规则补齐真实参数化校验，
    # 不改动已有 5 条真实校验(EL-001/002/003/FT-001)与埋深校验(GD-001)的任何逻辑。
    if rule_code in B5_RULES:
        return _real_engine_check_b5(item, rule_config, design_data)

    # 管线埋深：数据源为 pipeline 数组（与 devices 分离），单独处理
    if check_type == 'buried_depth':
        return _check_buried_depth(item, rule_config, design_data)

    devices = design_data.get('devices')
    if not devices or not isinstance(devices, list):
        return None

    # 数据可用性计数器：记录「规则适用的设备数」与「参数缺失/异常的设备数」
    related = 0
    missing = 0

    for device in devices:
        if not isinstance(device, dict):
            continue
        try:
            if check_type == 'fibre_capacity':
                # 真实通信光纤数据可比对项：光缆/分纤箱容量校验
                cap = device.get('capacity')
                used = device.get('fibreUsed')
                if cap is None or used is None:
                    continue
                try:
                    cap_f = float(cap)
                    used_f = float(used)
                except (ValueError, TypeError):
                    continue
                if cap_f <= 0:
                    continue
                passed, detail = rule_engine.check_fibre_capacity(used_f, cap_f)
                if not passed:
                    return _to_result(item, rule_config, detail, device)

            elif check_type == 'grounding_resistance':
                # 异常数据处理：仅对「应接地」设备(映射非 None)做核验；
                # 无独立接地要求的设备(电缆/分纤箱等)如实跳过，不计入待核查。
                gtype = GROUNDING_TYPE_MAP.get(device.get('deviceType'))
                if gtype is None:
                    continue
                related += 1
                gr = device.get('groundingResistance')
                gr_f = _safe_float(gr)
                # 缺失或非法(≤0)接地电阻 → 计入缺失，待核查，不崩溃
                if gr_f is None or gr_f <= 0:
                    missing += 1
                    continue
                passed, detail = rule_engine.check_grounding_resistance(
                    grounding_type=gtype,
                    measured_resistance=gr_f,
                )
                if not passed:
                    return _to_result(item, rule_config, detail, device)

            elif check_type == 'bending_radius':
                # 异常数据处理：仅对线缆类设备核验；缆径缺失/异常(=0)、弯曲半径缺失均计入缺失
                cable_type = CABLE_TYPE_MAP.get(device.get('deviceType'))
                if cable_type is None:
                    continue
                related += 1
                dia = _safe_float(device.get('cableDiameter'))
                bend = _safe_float(device.get('bendingRadius'))
                # 缆径非法(≤0，真实 FTTH 数据 DIAMETRE 多为 0) 或弯曲半径缺失 → 缺失
                if dia is None or dia <= 0 or bend is None:
                    missing += 1
                    continue
                passed, detail = rule_engine.check_bending_radius(
                    cable_type=cable_type,
                    cable_diameter=dia,
                    actual_radius=bend,
                )
                if not passed:
                    return _to_result(item, rule_config, detail, device)

            elif check_type == 'current_rating':
                # 异常数据处理：仅对线缆类设备核验；截面积/电流缺失或非法计入缺失
                cable_type = CABLE_TYPE_MAP.get(device.get('deviceType'))
                if cable_type is None:
                    continue
                related += 1
                cs = _safe_float(device.get('crossSection'))
                cur = _safe_float(device.get('actualCurrent'))
                if cs is None or cur is None or cs <= 0 or cur < 0:
                    missing += 1
                    continue
                material = MATERIAL_MAP.get(device.get('material'), 'copper')
                passed, detail = rule_engine.check_cable_current_rating(
                    conductor_material=material,
                    cross_section_mm2=cs,
                    actual_current_a=cur,
                )
                if not passed:
                    return _to_result(item, rule_config, detail, device)

        except (ValueError, TypeError, KeyError) as e:
            logger.warning(f"Device param parse error for {rule_code}: {str(e)}")
            continue

    # 待核查逻辑：规则对应设备存在，但全部缺失/异常参数，无法判定合规性 → 标记待核查
    # （不计入违规统计，仅如实呈现数据可用性缺口，提示人工复核）
    if related > 0 and missing == related:
        if check_type == 'grounding_resistance':
            return _to_pending_result(
                item, rule_config,
                f"共 {related} 个应接地设备（杆塔/配电室等）未提供接地电阻实测值，"
                f"依据 GB 50169/DL/T 621 接地电阻应≤4~10Ω，参数缺失无法判定合规性",
                related)
        if check_type == 'bending_radius':
            return _to_pending_result(
                item, rule_config,
                f"共 {related} 条线缆记录，均未提供弯曲半径(bendingRadius)实测值或缆径异常(=0)，"
                f"依据 GB 50217 电缆最小弯曲半径应≥缆径15~20倍，参数缺失无法判定合规性",
                related)
        if check_type == 'current_rating':
            return _to_pending_result(
                item, rule_config,
                f"共 {related} 条线缆记录，未提供导体截面积(crossSection)/工作电流(actualCurrent)参数，"
                f"依据 GB 50217 载流量需按截面积与导体材质查表比对并预留1.25倍裕度，参数缺失无法判定",
                related)

    return None


@router.post("/check", response_model=ReviewCheckResponse)
async def check_review(request: Request, review_request: ReviewCheckRequest):
    start_time = time.time()

    # 请求日志
    logger.info(f"===== Review Check Request =====")
    logger.info(f"task_id: {review_request.task_id}")
    logger.info(f"design_task_id: {review_request.design_task_id}")
    logger.info(f"task_name: {review_request.task_name}")
    logger.info(f"item_count: {len(review_request.items)}")
    logger.info(f"has_design_data: {review_request.design_data is not None}")
    if review_request.design_data:
        devices_count = len(review_request.design_data.get('devices', [])) if isinstance(review_request.design_data, dict) else 0
        logger.info(f"design_devices_count: {devices_count}")
    logger.info(f"===============================")

    # 重置规则引擎统计
    rule_engine.reset_statistics()

    processed_count = 0
    error_count = 0

    try:
        results = []
        design_data = review_request.design_data

        for item in review_request.items:
            processed_count += 1
            try:
                # 真实参数化校验（无设计数据或无对应参数则本规则不产生违规，不做随机模拟）
                result = real_engine_check(item, RULES_DATA.get(item.rule_code), design_data)
                if result:
                    results.append(result)
            except Exception as e:
                # 单条数据出错不中断整体审查
                error_count += 1
                logger.warning(f"Error processing rule {item.rule_code}: {str(e)}")
                continue

        duration = round(time.time() - start_time, 2)
        engine_stats = rule_engine.get_statistics()

        # 构建响应消息
        message = f"success, found {len(results)} violations by real computation"
        if error_count > 0:
            message += f", {error_count} rules skipped due to errors"

        # 响应日志
        logger.info(f"===== Review Check Response =====")
        logger.info(f"task_id: {review_request.task_id}")
        logger.info(f"violations_found: {len(results)}")
        logger.info(f"processed: {processed_count}, errors: {error_count}")
        logger.info(f"engine_stats: {engine_stats}")
        logger.info(f"duration: {duration}s")
        logger.info(f"===============================")

        return ReviewCheckResponse(
            code=200,
            message=message,
            data=results
        )

    except Exception as e:
        duration = round(time.time() - start_time, 2)

        # 错误日志
        logger.error(f"===== Review Check Error =====")
        logger.error(f"task_id: {review_request.task_id}")
        logger.error(f"error: {str(e)}")
        logger.error(f"duration: {duration}s")
        logger.error(f"stack: {traceback.format_exc()}")
        logger.error(f"===============================")

        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"审查校验失败: {str(e)}",
                "data": []
            }
        )


@router.post("/parse-real")
async def parse_real(request: Request):
    """解析真实工程 Shapefile 目录，返回系统可识别的 design_data（供 Java 侧拉取后导入审查）"""
    try:
        from app.utils.real_data_parser import parse_real_data
        body = {}
        try:
            body = await request.json()
        except Exception:
            body = {}
        shape_dir = body.get('dir') if isinstance(body, dict) else None
        design_data = parse_real_data(shape_dir)
        return ApiResponse(code=200, message="real data parsed", data=design_data)
    except Exception as e:
        logger.error(f"parse-real failed: {str(e)}")
        return JSONResponse(status_code=500, content={"code": 500, "message": f"真实数据解析失败: {str(e)}", "data": None})


@router.get("/health")
async def health_check(request: Request):
    logger.info(f"Health check request from {request.client.host if request.client else 'unknown'}")
    return ApiResponse(code=200, message="S3 Review Python Engine is running", data=None)


@router.get("/rules")
async def get_rules(request: Request):
    logger.info(f"Get rules request from {request.client.host if request.client else 'unknown'}")

    rules_list = []
    for code, rule in RULES_DATA.items():
        rules_list.append({
            "rule_id": rule['rule_id'],
            "rule_code": code,
            "rule_name": rule['rule_name'],
            "category": rule['category'],
            "risk_level": rule['risk_level'],
            "threshold": rule['threshold']
        })

    return ApiResponse(code=200, message="success", data=rules_list)


@router.get("/stats")
async def get_stats(request: Request):
    """获取规则统计信息"""
    logger.info(f"Get stats request from {request.client.host if request.client else 'unknown'}")

    stats = {
        "total_rules": len(RULES_DATA),
        "category_distribution": {},
        "risk_distribution": {'critical': 0, 'error': 0, 'warning': 0}
    }

    for rule in RULES_DATA.values():
        category = rule['category']
        risk_level = rule['risk_level']

        stats['category_distribution'][category] = stats['category_distribution'].get(category, 0) + 1
        stats['risk_distribution'][risk_level] += 1

    return ApiResponse(code=200, message="success", data=stats)
