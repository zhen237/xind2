package com.comm.m04.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.comm.m04.common.Result;
import com.comm.m04.entity.DeliveryPackage;
import com.comm.m04.service.DeliveryPackageService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/m04/delivery-package")
public class DeliveryPackageController {

    @Autowired
    private DeliveryPackageService deliveryPackageService;

    @GetMapping
    public Result<IPage<DeliveryPackage>> list(
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "10") Integer pageSize,
            @RequestParam(required = false) Long projectId,
            @RequestParam(required = false) Integer status) {
        IPage<DeliveryPackage> page = deliveryPackageService.list(new Page<>(pageNum, pageSize), projectId, status);
        return Result.success(page);
    }

    @GetMapping("/{id}")
    public Result<DeliveryPackage> getById(@PathVariable Long id) {
        DeliveryPackage deliveryPackage = deliveryPackageService.getById(id);
        return deliveryPackage != null ? Result.success(deliveryPackage) : Result.notFound("交付包不存在");
    }

    @PostMapping
    public Result<DeliveryPackage> create(@RequestBody DeliveryPackage deliveryPackage) {
        boolean success = deliveryPackageService.save(deliveryPackage);
        return success ? Result.success(deliveryPackage) : Result.error("创建失败");
    }

    @PutMapping("/{id}")
    public Result<DeliveryPackage> update(@PathVariable Long id, @RequestBody DeliveryPackage deliveryPackage) {
        deliveryPackage.setId(id);
        boolean success = deliveryPackageService.update(deliveryPackage);
        return success ? Result.success(deliveryPackage) : Result.error("更新失败");
    }

    @PutMapping("/{id}/status")
    public Result<Void> updateStatus(@PathVariable Long id, @RequestBody Map<String, Integer> body) {
        Integer status = body.get("status");
        boolean success = deliveryPackageService.updateStatus(id, status);
        return success ? Result.success() : Result.error("更新失败");
    }

    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        boolean success = deliveryPackageService.deleteById(id);
        return success ? Result.success() : Result.error("删除失败");
    }

    @GetMapping("/statistics")
    public Result<Map<String, Object>> statistics() {
        IPage<DeliveryPackage> page = deliveryPackageService.list(new Page<>(1, Integer.MAX_VALUE), null, null);
        List<DeliveryPackage> packages = page.getRecords();
        long total = packages.size();
        long pending = packages.stream().filter(p -> p.getStatus() == 0).count();
        long packaged = packages.stream().filter(p -> p.getStatus() == 1).count();
        long archived = packages.stream().filter(p -> p.getStatus() == 2).count();

        Map<String, Object> stats = new HashMap<>();
        stats.put("total", total);
        stats.put("pending", pending);
        stats.put("packaged", packaged);
        stats.put("archived", archived);
        return Result.success(stats);
    }
}