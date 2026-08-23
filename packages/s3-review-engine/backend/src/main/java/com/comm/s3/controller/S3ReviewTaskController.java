package com.comm.s3.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.comm.s3.common.Result;
import com.comm.s3.service.PdfExportService;
import com.comm.s3.service.ReviewService;
import com.comm.s3.service.S3ReviewResultService;
import com.comm.s3.service.S3ReviewTaskService;
import jakarta.servlet.http.HttpServletRequest;
import com.comm.s3.entity.S3ReviewResult;
import com.comm.s3.entity.S3ReviewTask;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/v1/s3/review/task")
public class S3ReviewTaskController {

    @Autowired
    private S3ReviewTaskService s3ReviewTaskService;

    @Autowired
    private S3ReviewResultService s3ReviewResultService;

    @Autowired
    private ReviewService reviewService;

    @Autowired
    private PdfExportService pdfExportService;

    @GetMapping
    public Result<List<S3ReviewTask>> list(
            @RequestParam(required = false) String status,
            @RequestParam(required = false) String riskLevel) {
        try {
            LambdaQueryWrapper<S3ReviewTask> wrapper = new LambdaQueryWrapper<>();
            
            // 按状态筛选
            if (status != null && !status.isEmpty()) {
                wrapper.eq(S3ReviewTask::getTaskStatus, status);
            }
            
            // 按风险等级筛选（有任一等级违规即匹配）
            if (riskLevel != null && !riskLevel.isEmpty()) {
                if ("critical".equals(riskLevel)) {
                    wrapper.gt(S3ReviewTask::getCriticalCount, 0);
                } else if ("error".equals(riskLevel)) {
                    wrapper.gt(S3ReviewTask::getErrorCount, 0);
                } else if ("warning".equals(riskLevel)) {
                    wrapper.gt(S3ReviewTask::getWarningCount, 0);
                }
            }
            
            // 按创建时间倒序
            wrapper.orderByDesc(S3ReviewTask::getCreateTime);
            
            List<S3ReviewTask> tasks = s3ReviewTaskService.list(wrapper);
            log.info("Task list query succeeded, count: {}", tasks.size());
            return Result.success(tasks);
        } catch (Exception e) {
            log.error("Failed to query task list: {}", e.getMessage(), e);
            return Result.error(500, "查询任务列表失败: " + e.getMessage());
        }
    }

    @GetMapping("/{id}")
    public Result<Map<String, Object>> getById(@PathVariable Long id) {
        S3ReviewTask task = s3ReviewTaskService.getById(id);
        if (task == null) {
            return Result.error(404, "任务不存在");
        }
        
        Map<String, Object> result = new HashMap<>();
        result.put("task", task);
        
        // 获取任务的审查结果
        LambdaQueryWrapper<S3ReviewResult> resultWrapper = new LambdaQueryWrapper<>();
        resultWrapper.eq(S3ReviewResult::getTaskId, id);
        resultWrapper.orderByDesc(S3ReviewResult::getRiskLevel);
        List<S3ReviewResult> results = s3ReviewResultService.list(resultWrapper);
        result.put("results", results);
        
        // 统计信息
        Map<String, Object> statistics = new HashMap<>();
        statistics.put("totalRules", task.getTotalCount());
        statistics.put("totalViolations", task.getCriticalCount() + task.getErrorCount() + task.getWarningCount());
        statistics.put("criticalCount", task.getCriticalCount());
        statistics.put("errorCount", task.getErrorCount());
        statistics.put("warningCount", task.getWarningCount());
        statistics.put("coverageRate", task.getCoverageRate());
        result.put("statistics", statistics);
        
        return Result.success(result);
    }

    /**
     * 获取真实工程的设计元数据（只读，用于报告页展示真实工程信息）。
     * 新增端点，不改动原有业务流程、端口与表结构。
     */
    @GetMapping("/{id}/design-meta")
    public Result<Map<String, Object>> getDesignMeta(@PathVariable Long id) {
        Map<String, Object> meta = reviewService.getDesignMeta(id);
        if (meta == null) {
            return Result.success("该任务未关联真实设计数据", null);
        }
        return Result.success(meta);
    }

    @PostMapping
    public Result<S3ReviewTask> save(@RequestBody S3ReviewTask task, HttpServletRequest request) {
        // 参数校验
        if (task.getDesignTaskId() == null || task.getDesignTaskId().trim().isEmpty()) {
            return Result.error(400, "设计任务ID不能为空");
        }
        if (task.getTaskName() == null || task.getTaskName().trim().isEmpty()) {
            return Result.error(400, "任务名称不能为空");
        }

        // 记录操作人（统一认证通过后由拦截器写入 request attribute；复用既有 createBy 字段，受限于三表字段不可改约束）
        Object authUser = request.getAttribute("authUsername");
        if (authUser != null && !authUser.toString().isBlank()) {
            task.setCreateBy(authUser.toString());
        }

        // 初始化任务状态
        task.setTaskStatus("PENDING");
        task.setCoverageRate(0.0);
        task.setTotalCount(0);
        task.setCriticalCount(0);
        task.setErrorCount(0);
        task.setWarningCount(0);
        s3ReviewTaskService.save(task);
        
        // 异步执行审查（使用新线程避免阻塞）
        new Thread(() -> {
            try {
                reviewService.executeReview(task);
            } catch (Exception e) {
                // 异常已在executeReview中处理
            }
        }).start();
        
        return Result.success("任务创建成功，审查正在进行中", s3ReviewTaskService.getById(task.getId()));
    }

    @PostMapping("/{id}/recheck")
    public Result<S3ReviewTask> recheck(@PathVariable Long id) {
        S3ReviewTask task = s3ReviewTaskService.getById(id);
        if (task == null) {
            return Result.error(404, "任务不存在");
        }
        
        // 异步执行重新复核
        new Thread(() -> {
            try {
                reviewService.recheckReview(id);
            } catch (Exception e) {
                // 异常已在recheckReview中处理
            }
        }).start();
        
        return Result.success("重新复核已启动", s3ReviewTaskService.getById(id));
    }

    @GetMapping("/{id}/results")
    public Result<List<S3ReviewResult>> getTaskResults(@PathVariable Long id) {
        S3ReviewTask task = s3ReviewTaskService.getById(id);
        if (task == null) {
            return Result.error(404, "任务不存在");
        }
        
        LambdaQueryWrapper<S3ReviewResult> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(S3ReviewResult::getTaskId, id);
        wrapper.orderByDesc(S3ReviewResult::getRiskLevel);
        
        return Result.success(s3ReviewResultService.list(wrapper));
    }

    /**
     * B-3 PDF 导出：生成符合工程归档规范的审查报告 PDF 并触发浏览器下载。
     * 新增端点，不改动原有业务流程、端口与表结构。
     */
    @GetMapping("/{id}/export-pdf")
    public ResponseEntity<byte[]> exportPdf(@PathVariable Long id) {
        try {
            byte[] pdf = pdfExportService.exportTaskReport(id);
            String filename = "审查报告_" + id + ".pdf";
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_PDF);
            headers.setContentDisposition(
                    ContentDisposition.attachment().filename(filename, StandardCharsets.UTF_8).build());
            headers.setContentLength(pdf.length);
            return new ResponseEntity<>(pdf, headers, HttpStatus.OK);
        } catch (IllegalArgumentException e) {
            log.warn("PDF 导出失败(参数): {}", e.getMessage());
            return ResponseEntity.status(HttpStatus.NOT_FOUND)
                    .contentType(MediaType.TEXT_PLAIN)
                    .body(("导出失败: " + e.getMessage()).getBytes(StandardCharsets.UTF_8));
        } catch (Exception e) {
            log.error("PDF 导出失败: {}", e.getMessage(), e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .contentType(MediaType.TEXT_PLAIN)
                    .body(("导出失败: " + e.getMessage()).getBytes(StandardCharsets.UTF_8));
        }
    }

    @GetMapping("/status-options")
    public Result<List<Map<String, String>>> getStatusOptions() {
        List<Map<String, String>> options = List.of(
            Map.of("value", "PENDING", "label", "待执行"),
            Map.of("value", "PROCESSING", "label", "审查中"),
            Map.of("value", "COMPLETED", "label", "已完成"),
            Map.of("value", "FAILED", "label", "失败")
        );
        return Result.success(options);
    }

    @PutMapping
    public Result<S3ReviewTask> update(@RequestBody S3ReviewTask task) {
        if (task.getId() == null) {
            return Result.error(400, "任务ID不能为空");
        }
        
        // 不允许修改执行中的任务
        S3ReviewTask existing = s3ReviewTaskService.getById(task.getId());
        if (existing != null && "PROCESSING".equals(existing.getTaskStatus())) {
            return Result.error(400, "任务正在执行中，无法修改");
        }
        
        s3ReviewTaskService.updateById(task);
        return Result.success("任务更新成功", s3ReviewTaskService.getById(task.getId()));
    }

    @DeleteMapping("/{id}")
    public Result<String> delete(@PathVariable Long id) {
        S3ReviewTask task = s3ReviewTaskService.getById(id);
        if (task != null && "PROCESSING".equals(task.getTaskStatus())) {
            return Result.error(400, "任务正在执行中，无法删除");
        }
        
        // 删除任务及其关联的审查结果
        LambdaQueryWrapper<S3ReviewResult> resultWrapper = new LambdaQueryWrapper<>();
        resultWrapper.eq(S3ReviewResult::getTaskId, id);
        s3ReviewResultService.remove(resultWrapper);
        
        s3ReviewTaskService.removeById(id);
        return Result.success("任务删除成功");
    }
}
