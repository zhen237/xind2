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
