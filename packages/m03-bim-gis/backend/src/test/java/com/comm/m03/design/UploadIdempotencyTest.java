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
 * 上传可靠性集成测试：证明"重复传不翻倍"（幂等）与"计数对账"。
 * 需真实数据库（CI 环境提供），与 DesignIntegrationTest 同上下文。
 * 数据源与限流通过 @TestPropertySource 内联提供，避免依赖 application.yml
 * 在测试classpath的解析（fork后 -D 不保证传递）。
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
        "security.permit-paths[0]=/api/m03/design/**",
        "rate-limit.enabled=false"
})
public class UploadIdempotencyTest {

    @Autowired
    private MockMvc mockMvc;

    private static final ObjectMapper OM = new ObjectMapper();

    private int parseSchemeId(MvcResult result) throws Exception {
        String json = result.getResponse().getContentAsString();
        return OM.readTree(json).get("data").get("schemeId").asInt();
    }

    @Test
    @DisplayName("相同 idempotencyKey 重复上传 -> 返回同一方案ID，站点不翻倍")
    public void testUploadIdempotency() throws Exception {
        // 每次运行用唯一键，但两次上传共用同一键 -> 互相去重（保证测试可重复）
        String key = "idem-" + java.util.UUID.randomUUID();
        String body = "{"
                + "\"projectId\":90909,"
                + "\"schemeName\":\"幂等测试\","
                + "\"totalSites\":2,\"validSites\":2,\"invalidSites\":0,"
                + "\"idempotencyKey\":\"" + key + "\","
                + "\"sites\":["
                + "  {\"siteId\":\"IDEM-1\",\"siteName\":\"A\",\"longitude\":116.40,\"latitude\":39.90,\"rsrp\":-70,\"isValid\":true},"
                + "  {\"siteId\":\"IDEM-2\",\"siteName\":\"B\",\"longitude\":116.41,\"latitude\":39.91,\"rsrp\":-71,\"isValid\":true}"
                + "]}";

        MvcResult r1 = mockMvc.perform(post("/api/m03/design/upload")
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andReturn();
        int schemeId1 = parseSchemeId(r1);

        // 第二次：完全相同的幂等键
        MvcResult r2 = mockMvc.perform(post("/api/m03/design/upload")
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andReturn();
        int schemeId2 = parseSchemeId(r2);

        assertEquals(schemeId1, schemeId2, "相同幂等键应返回同一方案ID（不翻倍）");

        // 站点不应翻倍：拉回应只有 2 个
        mockMvc.perform(get("/api/m03/design/" + schemeId1 + "/sites"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.length()").value(2));
    }

    @Test
    @DisplayName("越界站点被跳过并计入 skipped，且返回明细")
    public void testRangeValidationSkipsBadSites() throws Exception {
        String key = "idem-" + java.util.UUID.randomUUID();
        String body = "{"
                + "\"projectId\":90910,"
                + "\"schemeName\":\"范围校验测试\","
                + "\"totalSites\":3,\"validSites\":2,\"invalidSites\":1,"
                + "\"idempotencyKey\":\"" + key + "\","
                + "\"sites\":["
                + "  {\"siteId\":\"RNG-1\",\"longitude\":116.40,\"latitude\":39.90,\"rsrp\":-70,\"isValid\":true},"
                + "  {\"siteId\":\"RNG-2\",\"longitude\":116.41,\"latitude\":39.91,\"rsrp\":-71,\"isValid\":true},"
                + "  {\"siteId\":\"RNG-3\",\"longitude\":999.0,\"latitude\":39.91,\"rsrp\":-71,\"isValid\":true}"
                + "]}";

        mockMvc.perform(post("/api/m03/design/upload")
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.inserted").value(2))
                .andExpect(jsonPath("$.data.skipped").value(1))
                .andExpect(jsonPath("$.data.errors.length()").value(1));
    }
}
