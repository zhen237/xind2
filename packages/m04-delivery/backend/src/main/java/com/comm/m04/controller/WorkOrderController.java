package com.comm.m04.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.comm.m04.common.Result;
import com.comm.m04.entity.WorkOrder;
import com.comm.m04.service.WorkOrderService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/m04/work-order")
public class WorkOrderController {

    @Autowired
    private WorkOrderService workOrderService;

    @GetMapping
    public Result<IPage<WorkOrder>> list(
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "10") Integer pageSize,
            @RequestParam(required = false) String title,
            @RequestParam(required = false) Integer status,
            @RequestParam(required = false) String type) {
        IPage<WorkOrder> page = workOrderService.list(new Page<>(pageNum, pageSize), title, status, type);
        return Result.success(page);
    }

    @GetMapping("/{id}")
    public Result<WorkOrder> getById(@PathVariable Long id) {
        WorkOrder order = workOrderService.getById(id);
        return order != null ? Result.success(order) : Result.notFound("工单不存在");
    }

    @GetMapping("/statistics")
    public Result<Map<String, Object>> statistics() {
        IPage<WorkOrder> page = workOrderService.list(new Page<>(1, Integer.MAX_VALUE), null, null, null);
        List<WorkOrder> all = page.getRecords();
        long total = all.size();
        long pending = all.stream().filter(o -> o.getStatus() == 0).count();
        long processing = all.stream().filter(o -> o.getStatus() == 1).count();
        long completed = all.stream().filter(o -> o.getStatus() == 2).count();
        long closed = all.stream().filter(o -> o.getStatus() == 3).count();

        Map<String, Object> stats = new HashMap<>();
        stats.put("total", total);
        stats.put("pending", pending);
        stats.put("processing", processing);
        stats.put("completed", completed);
        stats.put("closed", closed);
        return Result.success(stats);
    }

    @PostMapping
    public Result<WorkOrder> create(@RequestBody WorkOrder workOrder) {
        boolean success = workOrderService.save(workOrder);
        return success ? Result.success(workOrder) : Result.error("创建失败");
    }

    @PutMapping("/{id}")
    public Result<WorkOrder> update(@PathVariable Long id, @RequestBody WorkOrder workOrder) {
        workOrder.setId(id);
        boolean success = workOrderService.update(workOrder);
        return success ? Result.success(workOrder) : Result.error("更新失败");
    }

    @PutMapping("/{id}/status")
    public Result<Void> updateStatus(@PathVariable Long id, @RequestBody Map<String, Integer> body) {
        Integer status = body.get("status");
        boolean success = workOrderService.updateStatus(id, status);
        return success ? Result.success() : Result.error("更新失败");
    }

    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        boolean success = workOrderService.deleteById(id);
        return success ? Result.success() : Result.error("删除失败");
    }
}