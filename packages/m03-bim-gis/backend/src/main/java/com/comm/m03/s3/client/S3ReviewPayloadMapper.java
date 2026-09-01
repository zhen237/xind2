package com.comm.m03.s3.client;

import com.comm.m03.design.entity.DesignData;
import com.comm.m03.design.entity.DesignTask;
import com.comm.m03.design.entity.DevicePositionData;
import com.comm.m03.design.entity.GenerateRequest;
import com.comm.m03.design.entity.SiteData;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * 将 S1 设计任务/设计数据映射为 S3 审查请求体。
 *
 * 映射原则：
 * - deviceType 为自由字符串，传真实语义值（communication_cable / site / rru / antenna 等）。
 * - 规则触发按 S3 实际参数，因此把 extraParams / site 属性中能对应到 S3 字段的参数尽量外提。
 * - 不臆造数据：缺少的字段直接不传，S3 自动标记 pending。
 */
public final class S3ReviewPayloadMapper {

    private static final Logger log = LoggerFactory.getLogger(S3ReviewPayloadMapper.class);

    private S3ReviewPayloadMapper() {
    }

    /**
     * 把设计任务 + 设计数据映射为 S3 接收请求体。
     *
     * @param task       S1 设计任务
     * @param designData S1 设计结果（executeDesignTask 返回值）
     * @param objectMapper 用于解析任务参数 JSON
     * @return S3 请求体
     */
    public static S3ReviewReceiveRequest map(DesignTask task, DesignData designData, ObjectMapper objectMapper) {
        String designTaskId = resolveDesignTaskId(task);
        String designTaskName = resolveDesignTaskName(task, designData);
        String designType = resolveDesignType(task, objectMapper);

        List<S3ReviewDevice> devices = new ArrayList<>();
        if (designData.getSites() != null) {
            int idx = 0;
            for (SiteData site : designData.getSites()) {
                devices.add(mapSite(site, idx++));
            }
        }
        if (designData.getDeviceLayout() != null) {
            for (DevicePositionData dev : designData.getDeviceLayout()) {
                devices.add(mapDevice(dev));
            }
        }

        return S3ReviewReceiveRequest.builder()
                .designTaskId(designTaskId)
                .designTaskName(designTaskName)
                .designType(designType)
                .devices(devices.isEmpty() ? Collections.emptyList() : devices)
                .build();
    }

    private static String resolveDesignTaskId(DesignTask task) {
        if (task == null) {
            return "S1-UNKNOWN";
        }
        if (task.getTaskNo() != null && !task.getTaskNo().isBlank()) {
            return task.getTaskNo();
        }
        return "S1-" + task.getId();
    }

    private static String resolveDesignTaskName(DesignTask task, DesignData designData) {
        if (task != null && task.getTaskName() != null && !task.getTaskName().isBlank()) {
            return task.getTaskName();
        }
        if (designData != null && designData.getSchemeName() != null && !designData.getSchemeName().isBlank()) {
            return designData.getSchemeName();
        }
        if (task != null && task.getTaskNo() != null) {
            return task.getTaskNo();
        }
        return "S1 设计任务";
    }

    private static String resolveDesignType(DesignTask task, ObjectMapper objectMapper) {
        if (task == null || task.getParamsJson() == null || task.getParamsJson().isBlank()) {
            return "communication";
        }
        try {
            GenerateRequest request = objectMapper.readValue(task.getParamsJson(), GenerateRequest.class);
            String templateType = request.getTemplateType();
            if (templateType != null && !templateType.isBlank()) {
                return templateType;
            }
        } catch (Exception e) {
            log.debug("解析任务参数 JSON 失败，使用默认 designType: taskId={}", task.getId());
        }
        return "communication";
    }

    private static S3ReviewDevice mapSite(SiteData site, int index) {
        String deviceId = site.getSiteId() != null ? site.getSiteId() : "SITE-" + index;
        String deviceName = site.getSiteName() != null ? site.getSiteName() : deviceId;
        S3ReviewDevice.S3ReviewDeviceBuilder builder = S3ReviewDevice.builder()
                .deviceId(deviceId)
                .deviceName(deviceName)
                .deviceType("site")
                .coordinates(coordinates(site.getLongitude(), site.getLatitude(), BigDecimal.ZERO));

        // 把站点属性放入 params，供 S3 规则按实际参数触发
        if (site.getTowerHeight() != null || site.getScenario() != null || site.getRsrp() != null) {
            builder.params(Map.of(
                    "towerHeight", site.getTowerHeight() != null ? site.getTowerHeight().toString() : "",
                    "siteType", site.getSiteType() != null ? site.getSiteType() : "",
                    "scenario", site.getScenario() != null ? site.getScenario() : "",
                    "rsrp", site.getRsrp() != null ? site.getRsrp().toString() : ""
            ));
        }
        return builder.build();
    }

    private static S3ReviewDevice mapDevice(DevicePositionData dev) {
        String deviceId = dev.getPositionId() != null ? dev.getPositionId()
                : (dev.getDeviceName() != null ? dev.getDeviceName() : "DEV-UNKNOWN");
        String deviceType = dev.getDeviceType() != null ? dev.getDeviceType() : "equipment";
        S3ReviewDevice.S3ReviewDeviceBuilder builder = S3ReviewDevice.builder()
                .deviceId(deviceId)
                .deviceName(dev.getDeviceName())
                .deviceType(deviceType)
                .coordinates(coordinates(dev.getLongitude(), dev.getLatitude(), dev.getAltitude()));

        // 优先把能识别为 S3 标准字段的参数外提；其余保留在 params 透传
        Map<String, Object> extra = dev.getExtraParams();
        if (extra != null) {
            builder.bendingRadius(decimal(extra.get("bendingRadius")))
                    .cableDiameter(decimal(extra.get("cableDiameter")))
                    .crossSection(decimal(extra.get("crossSection")))
                    .actualCurrent(decimal(extra.get("actualCurrent")))
                    .capacity(decimal(extra.get("capacity")))
                    .fibreUsed(decimal(extra.get("fibreUsed")))
                    .groundingResistance(decimal(extra.get("groundingResistance")))
                    .burialDepth(decimal(extra.get("burialDepth")))
                    .material(string(extra.get("material")))
                    .params(extra);
        }
        return builder.build();
    }

    private static String coordinates(BigDecimal lon, BigDecimal lat, BigDecimal alt) {
        double longitude = lon != null ? lon.doubleValue() : 0.0;
        double latitude = lat != null ? lat.doubleValue() : 0.0;
        double altitude = alt != null ? alt.doubleValue() : 0.0;
        return String.format("[%.6f,%.6f,%.1f]", longitude, latitude, altitude);
    }

    private static BigDecimal decimal(Object value) {
        if (value == null) {
            return null;
        }
        if (value instanceof Number) {
            return BigDecimal.valueOf(((Number) value).doubleValue());
        }
        try {
            return new BigDecimal(value.toString());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private static String string(Object value) {
        return value != null ? value.toString() : null;
    }
}
