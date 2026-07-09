package com.comm.m03.controller;

import com.comm.common.Result;
import com.comm.m03.entity.Model;
import com.comm.m03.service.ModelService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/m03/model")
public class ModelController {

    @Autowired
    private ModelService modelService;

    @GetMapping
    @Cacheable(value = "models", key = "'list'")
    public Result<List<Model>> list() {
        return Result.success(modelService.list());
    }

    @GetMapping("/{id}")
    @Cacheable(value = "models", key = "#id")
    public Result<Model> getById(@PathVariable Long id) {
        Model model = modelService.getById(id);
        if (model == null) {
            return Result.notFound("模型不存在");
        }
        return Result.success(model);
    }

    @GetMapping("/type/{modelType}")
    @Cacheable(value = "models", key = "'type:' + #modelType")
    public Result<List<Model>> getByType(@PathVariable String modelType) {
        return Result.success(modelService.findByModelType(modelType));
    }

    @PostMapping
    @CacheEvict(value = "models", allEntries = true)
    public Result<Model> create(@RequestBody Model model) {
        modelService.save(model);
        return Result.success(model);
    }

    @PutMapping("/{id}")
    @CacheEvict(value = "models", allEntries = true)
    public Result<Boolean> update(@PathVariable Long id, @RequestBody Model model) {
        model.setId(id);
        modelService.updateById(model);
        return Result.success(true);
    }

    @DeleteMapping("/{id}")
    @CacheEvict(value = "models", allEntries = true)
    public Result<Boolean> delete(@PathVariable Long id) {
        modelService.removeById(id);
        return Result.success(true);
    }
}
