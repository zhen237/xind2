package com.comm.m03.design;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import static org.junit.jupiter.api.Assertions.*;

/**
 * 创建类接口幂等测试：证明"重复提交同一幂等键 -> 不翻倍"。
 * 需在已应用 V5 迁移(含 idempotency_key 列与唯一索引)的测试库上运行。
 * 数据源与限流通过 @TestPropertySource 内联提供，避免依赖 application.yml 解析。
 * 设计接口由 DesignApiKeyInterceptor 校验 X-API-Key，测试中统一带上以通过鉴权。
 */
@SpringBootTest
@AutoConfigureMockMvc
@TestPropertySource(properties = {
        "spring.datasource.url=jdbc:mysql://localhost:3306/comm_platform?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true",
        "spring.datasource.username=root",
        "spring.datasource.password=Admin@123",
        "spring.datasource.driver-class-name=com.mysql.cj.jdbc.Driver",
        "spring.flyway.enabled=false",
        "jwt.secret=test-secret-for-unit-tests-only-change-me",
        "jwt.expiration=604800000",
        "m03.api-key=test-api-key-for-unit-tests",
        "spring.cache.type=none",
        "security.permit-paths[0]=/api/m03/design/**",
        "rate-limit.enabled=false"
})
public class CreateIdempotencyTest {

    @Autowired
    private MockMvc mockMvc;

    private static final ObjectMapper OM = new ObjectMapper();
    private static final String API_KEY = "test-api-key-for-unit-tests";

    private String parseDataText(MvcResult result) throws Exception {
        String json = result.getResponse().getContentAsString();
        return OM.readTree(json).get("data").asText();
    }

    private int parseSchemeId(MvcResult result) throws Exception {
        String json = result.getResponse().getContentAsString();
        return OM.readTree(json).get("data").get("schemeId").asInt();
    }

    @Test
    @DisplayName("相同 idempotencyKey 重复创建任务 -> 返回同一任务ID，不产生重复任务")
    public void testCreateTaskIdempotency() throws Exception {
        String key = "idem-task-" + java.util.UUID.randomUUID();
        String body = "{\"taskName\":\"幂等测试任务\",\"projectId\":90911,\"paramsJson\":\"{}\",\"idempotencyKey\":\"" + key + "\"}";

        MvcResult r1 = mockMvc.perform(post("/api/m03/design/tasks")
                        .header("X-API-Key", API_KEY)
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andReturn();
        String id1 = parseDataText(r1);

        MvcResult r2 = mockMvc.perform(post("/api/m03/design/tasks")
                        .header("X-API-Key", API_KEY)
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andReturn();
        String id2 = parseDataText(r2);

        assertEquals(id1, id2, "相同幂等键应返回同一任务ID（不翻倍）");
    }

    @Test
    @DisplayName("相同 idempotencyKey 重复创建模板 -> 返回同一模板ID，不产生重复模板")
    public void testCreateTemplateIdempotency() throws Exception {
        String key = "idem-tpl-" + java.util.UUID.randomUUID();
        String body = "{\"name\":\"幂等测试模板\",\"category\":\"test\",\"devicesJson\":\"{}\",\"idempotencyKey\":\"" + key + "\"}";

        MvcResult r1 = mockMvc.perform(post("/api/m03/design/templates")
                        .header("X-API-Key", API_KEY)
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andReturn();
        String id1 = parseDataText(r1);

        MvcResult r2 = mockMvc.perform(post("/api/m03/design/templates")
                        .header("X-API-Key", API_KEY)
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andReturn();
        String id2 = parseDataText(r2);

        assertEquals(id1, id2, "相同幂等键应返回同一模板ID（不翻倍）");
    }

    @Test
    @DisplayName("相同 idempotencyKey 重复提交站点 -> 站点不翻倍")
    public void testUploadSiteIdempotency() throws Exception {
        // 先建一个空方案（0 站点）
        String schemeKey = "idem-scheme-" + java.util.UUID.randomUUID();
        String schemeBody = "{\"projectId\":90912,\"schemeName\":\"站点幂等测试\",\"totalSites\":0,\"idempotencyKey\":\"" + schemeKey + "\"}";
        MvcResult sr = mockMvc.perform(post("/api/m03/design/upload")
                        .header("X-API-Key", API_KEY)
                        .contentType(MediaType.APPLICATION_JSON).content(schemeBody))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andReturn();
        int schemeId = parseSchemeId(sr);

        // 两次提交同一站点（同幂等键）
        String siteKey = "idem-site-" + java.util.UUID.randomUUID();
        String siteBody = "{\"siteId\":\"IDEM-S1\",\"siteName\":\"A\",\"idempotencyKey\":\"" + siteKey + "\"}";
        mockMvc.perform(post("/api/m03/design/" + schemeId + "/sites")
                        .header("X-API-Key", API_KEY)
                        .contentType(MediaType.APPLICATION_JSON).content(siteBody))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));
        mockMvc.perform(post("/api/m03/design/" + schemeId + "/sites")
                        .header("X-API-Key", API_KEY)
                        .contentType(MediaType.APPLICATION_JSON).content(siteBody))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));

        // 站点不应翻倍：拉回应只有 1 个
        mockMvc.perform(get("/api/m03/design/" + schemeId + "/sites")
                        .header("X-API-Key", API_KEY))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.length()").value(1));
    }
}
