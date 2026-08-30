package com.comm.m03.s3.client;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.util.Map;

/**
 * S3 审查请求体中的设备对象，对应契约 /api/v1/s3/review/s1/receive。
 *
 * 字段命名与契约保持一致；deviceType 为自由字符串（S3 规则按实际参数触发，
 * 不按枚举锁死）。未提供的字段不传，S3 自动标记为 pending。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class S3ReviewDevice {

    /** 设备唯一 ID */
    private String deviceId;

    /** 设备真实语义类型，如 communication_cable / rru / bbu / antenna / site 等 */
    private String deviceType;

    /** 设备名称 */
    private String deviceName;

    /** 材质，如 copper / aluminum / fiber */
    private String material;

    /** 弯曲半径（mm） */
    private BigDecimal bendingRadius;

    /** 缆径（mm） */
    private BigDecimal cableDiameter;

    /** 导体截面积（mm²） */
    private BigDecimal crossSection;

    /** 工作电流（A） */
    private BigDecimal actualCurrent;

    /** 额定容量（芯/端口） */
    private BigDecimal capacity;

    /** 已用光纤数 */
    private BigDecimal fibreUsed;

    /** 接地电阻（Ω） */
    private BigDecimal groundingResistance;

    /** 埋深（m） */
    private BigDecimal burialDepth;

    /** 坐标 JSON 字符串，如 "[114.052,30.601,0]" */
    private String coordinates;

    /** 其他业务参数（接触电阻、保护定值、油位等），原样透传 */
    private Map<String, Object> params;
}
