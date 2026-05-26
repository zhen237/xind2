package com.comm.m04.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.comm.m04.common.Result;
import com.comm.m04.entity.WorkOrder;
import com.comm.m04.mapper.WorkOrderMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;

@RestController
@RequestMapping("/api/m04/workorder")
public class WorkOrderController {

    @Autowired
    private WorkOrderMapper workOrderMapper;

    @GetMapping
    public Result<List<WorkOrder>> list(@RequestParam(required = false) Integer status) {
        LambdaQueryWrapper<WorkOrder> qw = new LambdaQueryWrapper<>();
        if (status != null) qw.eq(WorkOrder::getStatus, status);
        qw.orderByDesc(WorkOrder::getCreateTime);
        return Result.success(workOrderMapper.selectList(qw));
    }

    @GetMapping("/{id}")
    public Result<WorkOrder> getById(@PathVariable Long id) {
        WorkOrder wo = workOrderMapper.selectById(id);
        return wo != null ? Result.success(wo) : Result.notFound("工单不存在");
    }

    @GetMapping("/statistics")
    public Result<java.util.Map<String, Object>> statistics() {
        List<WorkOrder> all = workOrderMapper.selectList(null);
        long pending = all.stream().filter(w -> w.getStatus() == 0).count();
        long processing = all.stream().filter(w -> w.getStatus() == 1).count();
        long done = all.stream().filter(w -> w.getStatus() == 2).count();

        java.util.Map<String, Object> stats = new java.util.HashMap<>();
        stats.put("pending", pending);
        stats.put("processing", processing);
        stats.put("done", done);
        return Result.success(stats);
    }

    @PostMapping
    public Result<WorkOrder> create(@RequestBody WorkOrder workOrder) {
        workOrder.setOrderNo("WO" + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss")));
        workOrderMapper.insert(workOrder);
        return Result.success(workOrder);
    }

    @PutMapping("/{id}/status")
    public Result<Void> updateStatus(@PathVariable Long id, @RequestParam Integer status) {
        WorkOrder wo = new WorkOrder();
        wo.setId(id);
        wo.setStatus(status);
        workOrderMapper.updateById(wo);
        return Result.success();
    }
}
