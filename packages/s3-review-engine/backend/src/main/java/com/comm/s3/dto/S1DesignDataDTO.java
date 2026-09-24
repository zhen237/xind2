package com.comm.s3.dto;

import lombok.Data;
import java.util.List;
import java.util.Map;

/**
 * 上游S1模块传来的结构化设计数据
 */
@Data
public class S1DesignDataDTO {
    private String designTaskId;
    private String designTaskName;
    private String designType; // pipe, cable, tower, substation等
    /**
     * 站点场景类型（S3-T3 人工审核例外/特殊场景）：rooftop(楼顶站)/quick(快装站)/ground(地面站)/mountain(山顶站) 等。
     * 山顶站等特殊场景下部分国标规则（如避雷针独立高度校验）不适用，由规则引擎按场景排除并交由人工审核例外入口覆盖。
     */
    private String siteType;
    // ===== S3-T1 蓄电池容量与运营商设备负载匹配（PDF 问题①，通信电源新域）=====
    // 站点级电源配置参数（与 siteType 同级，置于 design_data 顶层），
    // 由 S1 竣工图纸结构化 JSON 推送；缺失时由引擎标记"待核查(pending)"，绝不臆造违规。
    /** 配置蓄电池容量(Ah) */
    private Double batteryCapacityAh;
    /** 主要负载功率(W) */
    private Double primaryLoadW;
    /** 次要负载功率(W) */
    private Double secondaryLoadW;
    /** 配置后备时间(h) */
    private Double backupTimeH;
    /** 市电类别：一类/二类/三类 */
    private String mainsClass;
    /** 运营商：移动/电信/联通 */
    private String operator;
    /** 区域：市区/郊县/偏远/山区 */
    private String siteRegion;
    /** 蓄电池类型：铅酸/磷酸铁锂 */
    private String batteryType;
    private List<DeviceParam> devices;
    private List<PipelineParam> pipeline; // 管线埋深校验数组(B-4)：敷设方式/场景/实测埋深
    private Map<String, Object> extraData;

    @Data
    public static class DeviceParam {
        private String deviceId;
        private String deviceName;
        private String deviceType;
        private String material;
        private Double burialDepth; // 埋深
        private Double groundingResistance; // 接地电阻
        private Double cableLength;
        private Double cableDiameter;
        private Double bendingRadius; // 弯曲半径
        private String coordinates; // 坐标JSON
        private Map<String, Object> params; // 其他参数

        // ===== 以下字段为 S3 规则引擎真实校验所需的业务参数（依据 GB 50217 / GB 51158 等行业规范），
        // 由 S1 竣工图纸结构化 JSON 推送，S3 不做任何臆造，缺失时由引擎标记"待核查(pending)"。 =====

        /** 导体截面积(mm²)，供载流量校验 EL-002（check_cable_current_rating 输入） */
        private Double crossSection;
        /** 工作电流(A)，供载流量校验 EL-002（check_cable_current_rating 输入） */
        private Double actualCurrent;
        /** 额定容量(芯/端口)，供光缆/分纤箱容量校验 FT-001（check_fibre_capacity 输入） */
        private Double capacity;
        /** 已用光纤数(芯/端口)，供光缆/分纤箱容量校验 FT-001（check_fibre_capacity 输入） */
        private Double fibreUsed;

        // ===== S3-T4 国标参数提取完整性补全（PDF「模块问题及修复难度总结」问题④）=====
        // 设计图转规则审查的国标参数提取不够完整，需补充拉线半径、电阻类型等字段，
        // 使 S1 端能结构化推送、S3 端能真实校验。以下为 S3 侧明确约定的合同字段；
        // 字段缺失时引擎标记 pending（待核查），绝不臆造违规。

        /** 拉线半径(m)：拉线塔/桅杆稳定性校验（GW-001，依据 GB 50061 拉线对地夹角≤60°） */
        private Double guyWireRadius;
        /** 接地电阻类型：垂直接地极/水平接地极/铜覆钢/镀锌钢/环形/复合（RT-001，依据 GB 50057/DL/T 621） */
        private String resistanceType;
        /** 塔高(m)：配合拉线半径做对地夹角稳定性校验 */
        private Double towerHeight;
    }

    /**
     * 管线埋深校验参数(B-4 新增)
     * 由 S1 竣工图纸结构化 JSON 推送的管线数组，供管线埋深真实校验 GD-001
     * （check_pipeline_buried_depth，依据 GB 51158/GB 50373）使用；缺失时由引擎标记"待核查(pending)"。
     */
    @Data
    public static class PipelineParam {
        private String pipeId;
        private String pipeName;
        private String deviceType; // 管线类型：power_cable/communication_cable 等，仅用于建议文案
        private String layingType; // 敷设方式：direct(直埋)/pipe(管道)；兼容中文 直埋/管道/管敷
        private String scenario;   // 场景：urban(城区)/suburb(郊外)；兼容中文 城区/市区/郊外/野外
        private Double burialDepth; // 实测埋深(米)
        private String coordinates; // 坐标JSON
        private Map<String, Object> params; // 其他参数
    }
}
