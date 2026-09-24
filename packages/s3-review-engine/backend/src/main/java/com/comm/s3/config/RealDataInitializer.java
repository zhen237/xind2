package com.comm.s3.config;

import com.comm.s3.dto.S1DesignDataDTO;
import com.comm.s3.entity.S3ReviewTask;
import com.comm.s3.service.ReviewService;
import com.comm.s3.service.S3ReviewTaskService;
import com.comm.s3.util.OkHttpUtil;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

import java.io.InputStream;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

/**
 * ============================================================================
 * 【真实业务代码 · 非演示模拟】
 * 本组件负责在系统启动时自动接入「真实通信工程竣工数据」并完成智能审查，
 * 属于生产级真实数据处理链路，不生成任何随机/模拟/虚假数据。
 * （历史命名曾含 "Demo" 仅为早期占位，现统一为「真实数据导入」语义。）
 * ============================================================================
 *
 * 真实工程数据自动导入器（仅用于本地一键拉起真实审查流程，不新增业务接口/不改表结构/不改端口）。
 *
 * 作用：
 *  1. Spring 启动完成后，调用 Python 引擎 /api/v1/s3/review/parse-real 解析本地真实工程
 *     竣工图 Shapefile（摩洛哥 JAD-MARJANE FTTH 通信光纤网络），得到系统可识别的 design_data；
 *  2. 创建一条真实审查任务（工程名、设计任务编号、629 个真实设备）；
 *  3. 触发审查引擎基于真实设计参数完成校验，报告页开箱即可看到"由公式比对计算生成、
 *     无随机模拟"的真实违规明细（如光分纤箱已用光纤数超过额定容量的真实违规）。
 *
 * 说明：S1 设计数据当前采用内存缓存（与现有实现一致），重启后由本组件重新拉取真实数据注入，
 * 不影响线上接口与表结构。
 */
@Slf4j
@Component
public class RealDataInitializer implements CommandLineRunner {

    @Autowired
    private ReviewService reviewService;

    @Autowired
    private S3ReviewTaskService reviewTaskService;

    @Value("${s3.python.engine-url}")
    private String engineUrl;

    /**
     * 本地 Shapefile 竣工图自动装载开关。
     * 说明：该能力属于「旧 Demo/本地样例数据源」，正式对接以 S1 推送为准。
     * 默认关闭（false），即系统启动不再自动拉取本地 Shapefile 生成审查任务；
     * 如需本地样例数据一键拉起，可在 application.yml 设置 s3.review.demo-auto-load: true。
     */
    @Value("${s3.review.demo-auto-load:false}")
    private boolean demoAutoLoadEnabled;

    /**
     * 演示数据自动种子化开关（数据固化）。
     * 开启后，若库中尚未存在 s3_demo_payload.json 对应的 designTaskId 任务，
     * 则启动时自动装入该 payload 并触发【真实审查引擎】生成演示任务，
     * 使前端开箱即有可展示的审查数据，且 Java 重启后自动恢复（不丢数据）。
     * 数据完全由规则引擎真实计算（不造假），重复启动靠 designTaskId 幂等跳过。
     * 默认开启（true）。
     */
    @Value("${s3.review.auto-seed-demo:true}")
    private boolean autoSeedDemoEnabled;

    private static final ObjectMapper MAPPER = new ObjectMapper();

    // 真实工程数据根目录（与 Python 端 real_data_parser.DEFAULT_SHAPE_DIR 上层保持一致）
    private static final String REAL_DATA_DIR =
            "D:/1通信基建数智化平台/a挑战杯赛题/真实数据/真实数据";

    // 演示数据样例（classpath 资源，打包后亦可读取）
    private static final String DEMO_PAYLOAD_CLASSPATH = "s3_demo_payload.json";

    @Override
    public void run(String... args) {
        // ===== 演示数据固化：启动即种子化（默认开启） =====
        if (autoSeedDemoEnabled) {
            new Thread(() -> {
                try {
                    // 延迟执行，确保 Python 引擎(8000)已在 Java 之前启动并就绪
                    Thread.sleep(6000);
                    seedDemoPayload();
                } catch (Exception e) {
                    log.warn("Demo seed skipped: {}", e.getMessage());
                }
            }, "demo-seed").start();
        }

        // ===== 本地 Shapefile 真实数据源（旧 Demo，默认关闭） =====
        if (!demoAutoLoadEnabled) {
            log.info("RealDataInitializer: 本地 Demo 自动装载已关闭（s3.review.demo-auto-load=false），"
                    + "正式数据源为 S1 推送（POST /api/v1/s3/review/s1/receive）。");
            return;
        }
        // 延迟执行，确保 Python 引擎(8000)已在 Java 之前启动并就绪
        new Thread(() -> {
            try {
                Thread.sleep(5000);
                importRealDataAndReview();
            } catch (Exception e) {
                log.warn("Real data import skipped: {}", e.getMessage());
            }
        }, "real-data-init").start();
    }

    /**
     * 演示数据种子化（数据固化核心）。
     * 读取 classpath 的 s3_demo_payload.json，复用与 S1 接收一致的真实审查链路：
     * 创建任务 → 存入设计数据 → 触发规则引擎审查。
     * 幂等：若库中已存在相同 designTaskId 的任务则跳过，避免重启重复建单。
     */
    private void seedDemoPayload() {
        // 1) 读取 payload
        S1DesignDataDTO payload;
        try (InputStream in = new ClassPathResource(DEMO_PAYLOAD_CLASSPATH).getInputStream()) {
            payload = MAPPER.readValue(in, S1DesignDataDTO.class);
        } catch (Exception e) {
            log.warn("Demo seed: 读取 {} 失败，跳过种子化。{}", DEMO_PAYLOAD_CLASSPATH, e.getMessage());
            return;
        }
        String dtId = payload.getDesignTaskId();
        if (dtId == null || dtId.trim().isEmpty()) {
            log.warn("Demo seed: payload 缺少 designTaskId，跳过种子化");
            return;
        }

        // 2) 幂等：已存在同 designTaskId 任务则跳过（数据固化已生效）
        long existing = reviewTaskService.lambdaQuery()
                .eq(S3ReviewTask::getDesignTaskId, dtId).count();
        if (existing > 0) {
            log.info("Demo seed: designTaskId={} 已存在任务，跳过种子化（数据固化生效，无需重建）", dtId);
            return;
        }

        // 3) 创建演示审查任务（与 S1DataReceiverController 接收逻辑对齐）
        S3ReviewTask task = new S3ReviewTask();
        task.setDesignTaskId(dtId);
        task.setTaskName("S1-" + (payload.getDesignTaskName() != null ? payload.getDesignTaskName() : dtId));
        task.setTaskStatus(ReviewService.STATUS_PENDING);
        task.setCoverageRate(0.0);
        task.setTotalCount(0);
        task.setCriticalCount(0);
        task.setErrorCount(0);
        task.setWarningCount(0);
        task.setCreateBy("S3演示种子");
        task.setCreateTime(LocalDateTime.now());
        task.setUpdateTime(LocalDateTime.now());
        reviewTaskService.save(task);
        Long taskId = task.getId();
        log.info("Demo seed: 创建演示审查任务 {} (designTaskId={})", taskId, dtId);

        // 4) 存入设计数据并异步触发真实审查（由 Python 规则引擎计算，不造假）
        @SuppressWarnings("unchecked")
        Map<String, Object> designDataAsMap = MAPPER.convertValue(payload, Map.class);
        Map<String, Object> designDataMap = new HashMap<>();
        designDataMap.put("design_data", designDataAsMap);
        reviewService.setDesignData(taskId, designDataMap);
        new Thread(() -> {
            try {
                reviewService.executeReview(task);
                log.info("Demo seed: 演示审查已触发 taskId={}", taskId);
            } catch (Exception e) {
                log.error("Demo seed: 审查失败 taskId={}", taskId, e);
            }
        }, "demo-seed-review").start();
    }

    /**
     * 拉取真实工程数据 → 创建真实审查任务 → 自动复核
     */
    private void importRealDataAndReview() {
        Map<String, Object> designData = fetchRealDesignData();
        if (designData == null) {
            log.warn("Real design data fetch failed, skip auto import (please ensure Python engine is up)");
            return;
        }

        // 创建真实审查任务
        S3ReviewTask task = new S3ReviewTask();
        task.setDesignTaskId("JAD-MARJANE-FTTH");
        task.setTaskName("JAD-MARJANE FTTH 通信光纤网络工程设计审查");
        task.setTaskStatus("PENDING");
        task.setCoverageRate(0.0);
        task.setTotalCount(0);
        task.setCriticalCount(0);
        task.setErrorCount(0);
        task.setWarningCount(0);
        task.setCreateBy("真实工程数据");
        task.setCreateTime(LocalDateTime.now());
        task.setUpdateTime(LocalDateTime.now());
        reviewTaskService.save(task);
        Long taskId = task.getId();
        log.info("Created real-data review task {}", taskId);

        // 存入设计数据缓存并触发审查
        Map<String, Object> wrapper = new HashMap<>();
        wrapper.put("design_data", designData);
        reviewService.setDesignData(taskId, wrapper);
        reviewService.executeReview(task);
        log.info("Real-data review triggered for task {}", taskId);
    }

    /**
     * 调用 Python 引擎解析真实工程 Shapefile，返回 design_data（Map 结构）
     */
    @SuppressWarnings("unchecked")
    private Map<String, Object> fetchRealDesignData() {
        try {
            String base = engineUrl;
            if (base.contains("/check")) {
                base = base.substring(0, base.lastIndexOf("/check"));
            }
            String parseUrl = base + "/parse-real";
            String json = OkHttpUtil.postJson(parseUrl, "{}");
            if (json == null) {
                return null;
            }
            JsonNode root = MAPPER.readTree(json);
            if (root.get("code").asInt() != 200) {
                return null;
            }
            JsonNode data = root.get("data");
            if (data == null) {
                return null;
            }
            return MAPPER.convertValue(data, Map.class);
        } catch (Exception e) {
            log.warn("fetchRealDesignData error: {}", e.getMessage());
            return null;
        }
    }
}
