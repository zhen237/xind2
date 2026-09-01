package com.comm.s3.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.comm.s3.common.Result;
import com.comm.s3.dto.PageResponse;
import com.comm.s3.entity.S3ReviewResult;
import com.comm.s3.service.S3ReviewResultService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 违规结果分页查询控制器
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/s3/review/result")
public class S3ReviewResultController {

    @Autowired
    private S3ReviewResultService s3ReviewResultService;

    /**
     * 分页查询违规结果（支持按任务ID、风险等级筛选）
     */
    @GetMapping("/page")
    public Result<PageResponse<S3ReviewResult>> pageQuery(
            @RequestParam(required = false) Long taskId,
            @RequestParam(required = false) String riskLevel,
            @RequestParam(required = false) String keyword,
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "10") Integer pageSize,
            @RequestParam(defaultValue = "createTime") String orderBy,
            @RequestParam(defaultValue = "desc") String orderType) {

        log.info("Page query: taskId={}, riskLevel={}, keyword={}, page={}/{}",
                taskId, riskLevel, keyword, pageNum, pageSize);

        LambdaQueryWrapper<S3ReviewResult> wrapper = new LambdaQueryWrapper<>();

        // 按任务ID筛选
        if (taskId != null) {
            wrapper.eq(S3ReviewResult::getTaskId, taskId);
        }

        // 按风险等级筛选
        if (riskLevel != null && !riskLevel.isEmpty()) {
            wrapper.eq(S3ReviewResult::getRiskLevel, riskLevel);
        }

        // 关键字搜索（规则编号或规则名称）
        if (keyword != null && !keyword.isEmpty()) {
            wrapper.and(w -> w
                .like(S3ReviewResult::getRuleCode, keyword)
                .or()
                .like(S3ReviewResult::getRuleName, keyword)
            );
        }

        // 排序
        if ("asc".equalsIgnoreCase(orderType)) {
            wrapper.orderByAsc(S3ReviewResult::getCreateTime);
        } else {
            wrapper.orderByDesc(S3ReviewResult::getCreateTime);
        }

        // 分页查询
        Page<S3ReviewResult> page = new Page<>(pageNum, pageSize);
        Page<S3ReviewResult> result = s3ReviewResultService.page(page, wrapper);

        PageResponse<S3ReviewResult> response = new PageResponse<>(
                result.getTotal(),
                (int) result.getCurrent(),
                (int) result.getSize(),
                result.getRecords()
        );

        return Result.success(response);
    }

    /**
     * 按任务ID分页查询违规结果
     */
    @GetMapping("/task-page/{taskId}")
    public Result<PageResponse<S3ReviewResult>> pageByTaskId(
            @PathVariable Long taskId,
            @RequestParam(required = false) String riskLevel,
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "10") Integer pageSize) {

        log.info("Page by task: taskId={}, riskLevel={}, page={}/{}",
                taskId, riskLevel, pageNum, pageSize);

        LambdaQueryWrapper<S3ReviewResult> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(S3ReviewResult::getTaskId, taskId);

        // 按风险等级筛选
        if (riskLevel != null && !riskLevel.isEmpty()) {
            wrapper.eq(S3ReviewResult::getRiskLevel, riskLevel);
        }

        // 按风险等级降序排列（critical > error > warning）
        wrapper.orderByDesc(S3ReviewResult::getRiskLevel);
        wrapper.orderByDesc(S3ReviewResult::getCreateTime);

        // 分页查询
        Page<S3ReviewResult> page = new Page<>(pageNum, pageSize);
        Page<S3ReviewResult> result = s3ReviewResultService.page(page, wrapper);

        PageResponse<S3ReviewResult> response = new PageResponse<>(
                result.getTotal(),
                (int) result.getCurrent(),
                (int) result.getSize(),
                result.getRecords()
        );

        return Result.success(response);
    }

    /**
     * 获取违规统计信息
     */
    @GetMapping("/statistics")
    public Result<Map<String, Object>> getStatistics(
            @RequestParam(required = false) Long taskId) {

        LambdaQueryWrapper<S3ReviewResult> wrapper = new LambdaQueryWrapper<>();
        if (taskId != null) {
            wrapper.eq(S3ReviewResult::getTaskId, taskId);
        }

        long total = s3ReviewResultService.count(wrapper);
        
        // 按风险等级统计
        LambdaQueryWrapper<S3ReviewResult> criticalWrapper = new LambdaQueryWrapper<>();
        LambdaQueryWrapper<S3ReviewResult> errorWrapper = new LambdaQueryWrapper<>();
        LambdaQueryWrapper<S3ReviewResult> warningWrapper = new LambdaQueryWrapper<>();
        
        if (taskId != null) {
            criticalWrapper.eq(S3ReviewResult::getTaskId, taskId);
            errorWrapper.eq(S3ReviewResult::getTaskId, taskId);
            warningWrapper.eq(S3ReviewResult::getTaskId, taskId);
        }
        
        criticalWrapper.eq(S3ReviewResult::getRiskLevel, "critical");
        errorWrapper.eq(S3ReviewResult::getRiskLevel, "error");
        warningWrapper.eq(S3ReviewResult::getRiskLevel, "warning");

        // 待核查(pending)：规则应具备参数但 S1 设计数据缺失/异常，无法判定合规性，标记待人工复核
        LambdaQueryWrapper<S3ReviewResult> pendingWrapper = new LambdaQueryWrapper<>();
        if (taskId != null) {
            pendingWrapper.eq(S3ReviewResult::getTaskId, taskId);
        }
        pendingWrapper.eq(S3ReviewResult::getRiskLevel, "pending");

        Map<String, Object> stats = new HashMap<>();
        stats.put("total", total);
        stats.put("critical", s3ReviewResultService.count(criticalWrapper));
        stats.put("error", s3ReviewResultService.count(errorWrapper));
        stats.put("warning", s3ReviewResultService.count(warningWrapper));
        stats.put("pending", s3ReviewResultService.count(pendingWrapper));

        return Result.success(stats);
    }

    // 保留原有接口兼容
    @GetMapping
    public Result<List<S3ReviewResult>> list(
            @RequestParam(required = false) Long taskId,
            @RequestParam(required = false) String riskLevel) {
        
        LambdaQueryWrapper<S3ReviewResult> wrapper = new LambdaQueryWrapper<>();
        if (taskId != null) {
            wrapper.eq(S3ReviewResult::getTaskId, taskId);
        }
        if (riskLevel != null && !riskLevel.isEmpty()) {
            wrapper.eq(S3ReviewResult::getRiskLevel, riskLevel);
        }
        wrapper.orderByDesc(S3ReviewResult::getCreateTime);
        
        return Result.success(s3ReviewResultService.list(wrapper));
    }

    @GetMapping("/{id}")
    public Result<S3ReviewResult> getById(@PathVariable Long id) {
        return Result.success(s3ReviewResultService.getById(id));
    }

    @GetMapping("/task/{taskId}")
    public Result<List<S3ReviewResult>> getByTaskId(@PathVariable Long taskId) {
        LambdaQueryWrapper<S3ReviewResult> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(S3ReviewResult::getTaskId, taskId);
        wrapper.orderByDesc(S3ReviewResult::getRiskLevel);
        return Result.success(s3ReviewResultService.list(wrapper));
    }

    @PostMapping
    public Result<S3ReviewResult> save(@RequestBody S3ReviewResult result) {
        s3ReviewResultService.save(result);
        return Result.success(result);
    }

    @PutMapping
    public Result<S3ReviewResult> update(@RequestBody S3ReviewResult result) {
        s3ReviewResultService.updateById(result);
        return Result.success(result);
    }

    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        s3ReviewResultService.removeById(id);
        return Result.success();
    }
}
