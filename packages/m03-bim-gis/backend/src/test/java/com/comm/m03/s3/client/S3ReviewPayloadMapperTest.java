package com.comm.m03.s3.client;

import com.comm.m03.design.entity.DesignData;
import com.comm.m03.design.entity.DesignTask;
import com.comm.m03.design.entity.SiteData;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

/**
 * TDD 红阶段：锁定 S1→S3 合同字段映射行为。
 * - 顶层 siteType 应从首个站点推导（S1 可提供的场景类型）；
 * - 电源/接地等 S1 不设计的字段必须为 null，S3 侧按契约标 pending，绝不臆造。
 */
class S3ReviewPayloadMapperTest {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    void mapsTopLevelSiteTypeFromFirstSite_andLeavesPowerFieldsNull() {
        DesignTask task = new DesignTask();
        task.setTaskNo("T-1");
        task.setTaskName("测试任务");
        // paramsJson 为 null -> designType 默认 communication

        SiteData site = new SiteData();
        site.setSiteId("S1");
        site.setSiteName("站点1");
        site.setLongitude(new BigDecimal("120.1"));
        site.setLatitude(new BigDecimal("30.2"));
        site.setSiteType("rooftop");

        DesignData designData = new DesignData();
        designData.setSites(List.of(site));

        S3ReviewReceiveRequest req = S3ReviewPayloadMapper.map(task, designData, objectMapper);

        assertEquals("T-1", req.getDesignTaskId());
        // 新增顶层字段：从首个站点推导
        assertEquals("rooftop", req.getSiteType());
        // S1 不做电源/接地设计，这些字段应为 null，S3 侧标 pending（不臆造）
        assertNull(req.getBatteryCapacityAh());
        assertNull(req.getPrimaryLoadW());
        assertNull(req.getResistanceType());
        assertNull(req.getTowerHeight());
    }
}
