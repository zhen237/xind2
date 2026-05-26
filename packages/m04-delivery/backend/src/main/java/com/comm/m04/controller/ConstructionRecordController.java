package com.comm.m04.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.comm.m04.common.Result;
import com.comm.m04.entity.ConstructionRecord;
import com.comm.m04.service.ConstructionRecordService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/m04/construction-record")
public class ConstructionRecordController {

    @Autowired
    private ConstructionRecordService constructionRecordService;

    @GetMapping
    public Result<IPage<ConstructionRecord>> list(
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "10") Integer pageSize,
            @RequestParam(required = false) Long projectId,
            @RequestParam(required = false) String responsiblePerson) {
        IPage<ConstructionRecord> page = constructionRecordService.list(new Page<>(pageNum, pageSize), projectId, responsiblePerson);
        return Result.success(page);
    }

    @GetMapping("/{id}")
    public Result<ConstructionRecord> getById(@PathVariable Long id) {
        ConstructionRecord record = constructionRecordService.getById(id);
        return record != null ? Result.success(record) : Result.notFound("记录不存在");
    }

    @PostMapping
    public Result<ConstructionRecord> create(@RequestBody ConstructionRecord record) {
        boolean success = constructionRecordService.save(record);
        return success ? Result.success(record) : Result.error("创建失败");
    }

    @PutMapping("/{id}")
    public Result<ConstructionRecord> update(@PathVariable Long id, @RequestBody ConstructionRecord record) {
        record.setId(id);
        boolean success = constructionRecordService.update(record);
        return success ? Result.success(record) : Result.error("更新失败");
    }

    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        boolean success = constructionRecordService.deleteById(id);
        return success ? Result.success() : Result.error("删除失败");
    }
}