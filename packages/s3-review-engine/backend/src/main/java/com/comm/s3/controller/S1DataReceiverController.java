package com.comm.s3.controller;

import com.comm.s3.common.Result;
import com.comm.s3.dto.S1DesignDataDTO;
import com.comm.s3.dto.S1ReceiveResponse;
import com.comm.s3.entity.S3ReviewTask;
import com.comm.s3.service.ReviewService;
import com.comm.s3.service.S3ReviewTaskService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * 对接上游S1模块的数据接收接口
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/s3/review/s1")
public class S1DataReceiverController {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    @Autowired
    private S3ReviewTaskService s3ReviewTaskService;

    @Autowired
    private ReviewService reviewService;

    /**
     * 接收S1模块传来的设计数据并创建审查任务
     *
     * 接口容错与降级：
     *  - 必填字段(designTaskId/designTaskName/devices 及设备 deviceId/deviceType)缺失时，
     *    仍创建审查任务但标记为 FAILED，并在报告中写明明确错误原因，不继续执行审查；
     *  - 正常接收后异步触发 Python 规则引擎审查，链路异常由 ReviewService 统一降级为 FAILED。
     *
     * 响应格式：code / message / reviewTaskId / status（不修改原有返回字段结构）
     */
    @PostMapping("/receive")
    public ResponseEntity<S1ReceiveResponse> receiveDesignData(@RequestBody S1DesignDataDTO designData) {
        S1ReceiveResponse resp = new S1ReceiveResponse();

        // 先创建审查任务：即便后续参数校验失败，也要保留任务记录并标记为 FAILED（降级要求）
        S3ReviewTask task = new S3ReviewTask();
        String dtId = (designData.getDesignTaskId() != null && !designData.getDesignTaskId().trim().isEmpty())
                ? designData.getDesignTaskId() : "UNKNOWN";
        String dtName = (designData.getDesignTaskName() != null && !designData.getDesignTaskName().trim().isEmpty())
                ? designData.getDesignTaskName() : "S1-数据校验失败";
        task.setDesignTaskId(dtId);

        // 同一份图纸（designTaskId）重复推送：命中缓存则复用设计数据，跳过重复参数解析（B-1 需求）
        boolean cacheHit = dtId != null && !dtId.isEmpty() && !"UNKNOWN".equals(dtId)
                && reviewService.isDesignCached(dtId);
        task.setTaskName("S1-" + dtName);
        task.setTaskStatus(ReviewService.STATUS_PENDING);
        task.setCoverageRate(0.0);
        task.setTotalCount(0);
        task.setCriticalCount(0);
        task.setErrorCount(0);
        task.setWarningCount(0);
        task.setCreateBy("S1模块");
        task.setCreateTime(LocalDateTime.now());
        task.setUpdateTime(LocalDateTime.now());

        s3ReviewTaskService.save(task);
        Long taskId = task.getId();
        log.info("Created review task {} from S1 data, designTaskId: {}", taskId, dtId);

        // ===== 参数合法性校验（关键字段缺失 → 任务 FAILED + 明确原因，不继续审查） =====
        if (designData.getDesignTaskId() == null || designData.getDesignTaskId().trim().isEmpty()) {
            return fail(resp, taskId, "设计任务ID(designTaskId)不能为空");
        }
        if (designData.getDesignTaskName() == null || designData.getDesignTaskName().trim().isEmpty()) {
            return fail(resp, taskId, "设计任务名称(designTaskName)不能为空");
        }
        if (designData.getDevices() == null || designData.getDevices().isEmpty()) {
            return fail(resp, taskId, "设备列表(devices)不能为空，S1 未推送任何图纸业务数据");
        }
        for (S1DesignDataDTO.DeviceParam device : designData.getDevices()) {
            if (device.getDeviceId() == null || device.getDeviceId().trim().isEmpty()
                    || device.getDeviceType() == null || device.getDeviceType().trim().isEmpty()) {
                return fail(resp, taskId, "设备存在 deviceId 或 deviceType 为空，无法定位审查对象");
            }
        }

        // ===== 校验通过：存入设计数据并异步触发审查 =====
        // 同一份图纸（designTaskId）重复推送时命中缓存，直接复用设计数据，跳过 MAPPER.convertValue 重复参数解析（B-1 需求性能优化）。
        // 注意：design_data 必须存为 Map 结构，与 Python 引擎入参 / 覆盖率计算 / designMeta 预期一致。
        Map<String, Object> reused = cacheHit ? reviewService.getCachedDesign(dtId) : null;
        Map<String, Object> designDataMap;
        if (reused != null && reused.containsKey("design_data")) {
            designDataMap = reused;
            log.info("Task {} 命中缓存，复用 designTaskId={} 的设计数据，跳过重复参数解析", taskId, dtId);
        } else {
            cacheHit = false;
            @SuppressWarnings("unchecked")
            Map<String, Object> designDataAsMap = MAPPER.convertValue(designData, Map.class);
            designDataMap = new HashMap<>();
            designDataMap.put("design_data", designDataAsMap);
        }
        reviewService.setDesignData(taskId, designDataMap);

        new Thread(() -> {
            try {
                reviewService.executeReview(task);
            } catch (Exception e) {
                log.error("S1 review task failed, taskId: {}", taskId, e);
            }
        }).start();

        resp.setCode(200);
        resp.setMessage(cacheHit ? "命中缓存，复用设计数据并重新审查" : "S1设计数据接收成功，审查已启动");
        resp.setReviewTaskId(taskId);
        resp.setStatus(task.getTaskStatus());
        return ResponseEntity.ok(resp);
    }

    /**
     * 校验失败的统一处理：将已创建的任务标记为 FAILED，写入对接异常原因，返回明确错误信息。
     */
    private ResponseEntity<S1ReceiveResponse> fail(S1ReceiveResponse resp, Long taskId, String reason) {
        resp.setCode(400);
        resp.setMessage(reason);
        resp.setStatus(ReviewService.STATUS_FAILED);
        resp.setReviewTaskId(taskId);
        if (taskId != null) {
            reviewService.recordIntegrationFailure(taskId, "S1数据校验失败: " + reason);
        }
        log.warn("S1 receive rejected, taskId {}: {}", taskId, reason);
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(resp);
    }

    /**
     * 接收S1模块传来的设备参数数据（用于覆盖率计算）
     */
    @PostMapping("/devices")
    public Result<Map<String, Object>> receiveDeviceData(
            @RequestBody S1DesignDataDTO designData) {
        log.info("Received S1 device data, designType: {}, deviceCount: {}", 
                designData.getDesignType(), 
                designData.getDevices() != null ? designData.getDevices().size() : 0);

        Map<String, Object> result = new HashMap<>();
        int deviceCount = designData.getDevices() != null ? designData.getDevices().size() : 0;

        // 统计各类型设备数量
        Map<String, Integer> typeCount = new HashMap<>();
        if (designData.getDevices() != null) {
            for (S1DesignDataDTO.DeviceParam device : designData.getDevices()) {
                String type = device.getDeviceType() != null ? device.getDeviceType() : "unknown";
                typeCount.merge(type, 1, Integer::sum);
            }
        }

        result.put("totalDevices", deviceCount);
        result.put("deviceTypeDistribution", typeCount);
        result.put("hasBuriedDepthData", designData.getDevices() != null && 
                designData.getDevices().stream().anyMatch(d -> d.getBurialDepth() != null));
        result.put("hasGroundingData", designData.getDevices() != null && 
                designData.getDevices().stream().anyMatch(d -> d.getGroundingResistance() != null));
        result.put("receivedAt", LocalDateTime.now().toString());

        return Result.success(result);
    }

    /**
     * 获取设备参数模板
     */
    @GetMapping("/template")
    public Result<Map<String, Object>> getDeviceTemplate() {
        Map<String, Object> template = new HashMap<>();
        template.put("description", "S1模块设备参数模板");
        
        Map<String, Object> deviceTemplate = new HashMap<>();
        deviceTemplate.put("deviceId", "设备ID");
        deviceTemplate.put("deviceName", "设备名称");
        deviceTemplate.put("deviceType", "设备类型(cable/pipe/tower/transformer/box 等)");
        deviceTemplate.put("material", "材质");
        deviceTemplate.put("burialDepth", "埋深(米)");
        deviceTemplate.put("groundingResistance", "接地电阻(欧姆)");
        deviceTemplate.put("cableLength", "电缆长度(米)");
        deviceTemplate.put("cableDiameter", "电缆直径(毫米)");
        deviceTemplate.put("bendingRadius", "弯曲半径(毫米)");
        deviceTemplate.put("crossSection", "导体截面积(mm²)，供载流量校验");
        deviceTemplate.put("actualCurrent", "工作电流(A)，供载流量校验");
        deviceTemplate.put("capacity", "额定容量(芯/端口)，供光缆容量校验");
        deviceTemplate.put("fibreUsed", "已用光纤数(芯/端口)，供光缆容量校验");
        deviceTemplate.put("coordinates", "坐标[经度,纬度,高度]");
        deviceTemplate.put("params", "其他参数(Map)");

        template.put("deviceFields", deviceTemplate);
        
        // 示例数据
        Map<String, Object> example = new HashMap<>();
        example.put("designTaskId", "DT2024001");
        example.put("designTaskName", "110kV输电线路设计");
        example.put("designType", "cable");
        
        Map<String, Object> device = new HashMap<>();
        device.put("deviceId", "DEV001");
        device.put("deviceName", "电缆段1");
        device.put("deviceType", "cable");
        device.put("material", "铜");
        device.put("burialDepth", 0.8);
        device.put("groundingResistance", 3.5);
        device.put("cableLength", 500);
        device.put("cableDiameter", 30);
        device.put("bendingRadius", 450);
        device.put("crossSection", 240.0);
        device.put("actualCurrent", 320.0);
        device.put("capacity", 48);
        device.put("fibreUsed", 0);
        device.put("coordinates", "[114.05,30.60,0]");
        Map<String, Object> params = new HashMap<>();
        params.put("voltage", "110kV");
        device.put("params", params);
        
        example.put("devices", new Object[]{device});
        template.put("example", example);

        return Result.success(template);
    }
}
