package com.comm.m03.controller;

import com.comm.common.Result;
import com.comm.m03.entity.Region;
import com.comm.m03.service.RegionService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/m03/region")
public class RegionController {

    @Autowired
    private RegionService regionService;

    @GetMapping
    public Result<List<Region>> list() {
        return Result.success(regionService.list());
    }

    @GetMapping("/{id}")
    public Result<Region> getById(@PathVariable Long id) {
        Region region = regionService.getById(id);
        if (region == null) {
            return Result.notFound("区域不存在");
        }
        return Result.success(region);
    }

    @GetMapping("/parent/{parentCode}")
    public Result<List<Region>> getByParent(@PathVariable String parentCode) {
        return Result.success(regionService.findByParentCode(parentCode));
    }

    @PostMapping
    public Result<Region> create(@RequestBody Region region) {
        regionService.save(region);
        return Result.success(region);
    }

    @PutMapping("/{id}")
    public Result<Boolean> update(@PathVariable Long id, @RequestBody Region region) {
        regionService.updateById(region);
        return Result.success(true);
    }

    @DeleteMapping("/{id}")
    public Result<Boolean> delete(@PathVariable Long id) {
        regionService.removeById(id);
        return Result.success(true);
    }
}
