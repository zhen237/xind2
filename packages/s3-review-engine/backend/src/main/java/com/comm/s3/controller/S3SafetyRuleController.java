package com.comm.s3.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.comm.s3.common.Result;
import com.comm.s3.entity.S3SafetyRule;
import com.comm.s3.service.S3SafetyRuleService;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.access.prepost.PreAuthorize;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.util.List;

@RestController
@RequestMapping("/api/v1/s3/review/rule")
@Validated
public class S3SafetyRuleController {

    @Autowired
    private S3SafetyRuleService s3SafetyRuleService;

    @GetMapping
    public Result<List<S3SafetyRule>> list() {
        return Result.success(s3SafetyRuleService.list());
    }

    @GetMapping("/category/{category}")
    public Result<List<S3SafetyRule>> listByCategory(@PathVariable @NotBlank(message = "分类不能为空") String category) {
        LambdaQueryWrapper<S3SafetyRule> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(S3SafetyRule::getCategory, category);
        wrapper.eq(S3SafetyRule::getStatus, 1);
        wrapper.orderByAsc(S3SafetyRule::getRuleCode);
        return Result.success(s3SafetyRuleService.list(wrapper));
    }

    @GetMapping("/{id}")
    public Result<S3SafetyRule> getById(@PathVariable @NotNull(message = "ID不能为空") Long id) {
        S3SafetyRule rule = s3SafetyRuleService.getById(id);
        if (rule == null) {
            return Result.error(404, "规则不存在");
        }
        return Result.success(rule);
    }

    @PreAuthorize("hasRole('ADMIN')")
    @PostMapping
    public Result<S3SafetyRule> save(@RequestBody @Validated S3SafetyRule rule) {
        if (rule.getRuleCode() == null || rule.getRuleCode().trim().isEmpty()) {
            return Result.error(400, "规则编号不能为空");
        }
        if (rule.getRuleName() == null || rule.getRuleName().trim().isEmpty()) {
            return Result.error(400, "规则名称不能为空");
        }
        if (rule.getCategory() == null || rule.getCategory().trim().isEmpty()) {
            return Result.error(400, "分类不能为空");
        }
        if (rule.getRiskLevel() == null || !isValidRiskLevel(rule.getRiskLevel())) {
            return Result.error(400, "风险等级必须为critical/error/warning");
        }
        
        LambdaQueryWrapper<S3SafetyRule> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(S3SafetyRule::getRuleCode, rule.getRuleCode());
        if (s3SafetyRuleService.count(wrapper) > 0) {
            return Result.error(400, "规则编号已存在");
        }
        
        rule.setStatus(rule.getStatus() == null ? 1 : rule.getStatus());
        s3SafetyRuleService.save(rule);
        return Result.success("规则创建成功", rule);
    }

    @PreAuthorize("hasRole('ADMIN')")
    @PutMapping
    public Result<S3SafetyRule> update(@RequestBody @Validated S3SafetyRule rule) {
        if (rule.getId() == null) {
            return Result.error(400, "ID不能为空");
        }
        if (rule.getRiskLevel() != null && !isValidRiskLevel(rule.getRiskLevel())) {
            return Result.error(400, "风险等级必须为critical/error/warning");
        }
        
        S3SafetyRule existingRule = s3SafetyRuleService.getById(rule.getId());
        if (existingRule == null) {
            return Result.error(404, "规则不存在");
        }
        
        s3SafetyRuleService.updateById(rule);
        return Result.success("规则更新成功", s3SafetyRuleService.getById(rule.getId()));
    }

    @PreAuthorize("hasRole('ADMIN')")
    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable @NotNull(message = "ID不能为空") Long id) {
        S3SafetyRule rule = s3SafetyRuleService.getById(id);
        if (rule == null) {
            return Result.error(404, "规则不存在");
        }
        s3SafetyRuleService.removeById(id);
        return Result.success("规则删除成功", null);
    }

    @GetMapping("/count")
    public Result<Long> count() {
        return Result.success(s3SafetyRuleService.count());
    }

    @GetMapping("/categories")
    public Result<List<String>> getCategories() {
        List<String> categories = List.of("电力", "防雷", "结构", "电磁", "通用");
        return Result.success(categories);
    }

    private boolean isValidRiskLevel(String riskLevel) {
        return "critical".equals(riskLevel) || "error".equals(riskLevel) || "warning".equals(riskLevel);
    }
}
