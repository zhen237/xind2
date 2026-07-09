package com.comm.m03.design;

import com.comm.m03.design.controller.DesignController;
import com.comm.m03.design.service.DesignService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Java→Python→数据库完整链路集成测试
 * 验证参数化设计API的端到端调用流程
 */
@SpringBootTest
@AutoConfigureMockMvc
public class DesignIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private DesignService designService;

    @Test
    @DisplayName("测试参数化设计API完整链路")
    public void testDesignGenerationFlow() throws Exception {
        // 1. 构造请求参数
        String requestBody = "{"
                + "\"templateType\":\"macro\","
                + "\"centerLongitude\":116.4074,"
                + "\"centerLatitude\":39.9042,"
                + "\"coverageRadius\":500,"
                + "\"gridSize\":200,"
                + "\"sectorCount\":3"
                + "}";

        // 2. 调用API
        MvcResult result = mockMvc.perform(post("/api/m03/design/generate")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(requestBody))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andReturn();

        // 3. 验证响应数据
        String responseContent = result.getResponse().getContentAsString();
        assertNotNull(responseContent);
        assertTrue(responseContent.contains("\"totalSites\""));
        assertTrue(responseContent.contains("\"validSites\""));
    }

    @Test
    @DisplayName("测试模板管理API")
    public void testTemplateManagement() throws Exception {
        // 获取模板列表
        mockMvc.perform(get("/api/m03/design/templates"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.length()").value(3));
    }

    @Test
    @DisplayName("测试设计任务创建API")
    public void testDesignTaskCreation() throws Exception {
        String requestBody = "{"
                + "\"taskName\":\"集成测试任务\","
                + "\"projectId\":1,"
                + "\"paramsJson\":\"{\\\"templateType\\\":\\\"macro\\\",\\\"centerLongitude\\\":116.4074}\""
                + "}";

        mockMvc.perform(post("/api/m03/design/tasks")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(requestBody))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    @DisplayName("测试设计任务查询API")
    public void testDesignTaskQuery() throws Exception {
        mockMvc.perform(get("/api/m03/design/tasks"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    @DisplayName("测试健康检查API")
    public void testHealthCheck() throws Exception {
        mockMvc.perform(get("/api/m03/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }
}
