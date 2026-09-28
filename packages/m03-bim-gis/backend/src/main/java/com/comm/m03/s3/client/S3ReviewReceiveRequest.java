package com.comm.m03.s3.client;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

/**
 * S3 智能审查接收接口请求体，对应 POST /api/v1/s3/review/s1/receive。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class S3ReviewReceiveRequest {

    /** 设计任务唯一 ID（建议使用 S1 自身 taskNo 或格式化字符串） */
    private String designTaskId;

    /** 设计任务名称 */
    private String designTaskName;

    /** 设计类型，如 communication / ftth / macro / mixed */
    private String designType;

    /** 设备/线缆数组 */
    private List<S3ReviewDevice> devices;

    /** 管线埋深数组（GD-001 用），可选 */
    private List<S3ReviewPipeline> pipeline;

    /** 其他扩展参数，原样透传 */
    private Map<String, Object> extraData;

    // ===== S3 设计智能审查引擎合同字段（对应 S3 S1DesignDataDTO 顶层字段）=====
    // 说明：以下字段由 S3 侧在 2026-09-24 的 feat/s3-review-engine-20260924 分支约定。
    // S1 只做 FTTH/基站几何与路由设计，不产出电源/接地工程量，因此这些字段缺省为 null，
    // S3 侧按契约标记 pending（待核查），绝不臆造违规。能推导的字段（siteType）在此映射。

    /** 站点场景类型（S3-T3 人工审核例外）：rooftop/quick/ground/mountain 等，从首个站点推导 */
    private String siteType;

    // —— S3-T1 蓄电池容量与运营商设备负载匹配（通信电源新域）——
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

    // —— S3-T4 国标参数提取完整性（GB 50061 拉线对地夹角 / GB 50057 接地）——
    /** 拉线半径(m) */
    private Double guyWireRadius;
    /** 接地电阻类型：垂直接地极/水平接地极/铜覆钢/镀锌钢/环形/复合 */
    private String resistanceType;
    /** 塔高(m)（S3 顶层；逐站点值仍随 devices[].params 透传） */
    private Double towerHeight;
}
