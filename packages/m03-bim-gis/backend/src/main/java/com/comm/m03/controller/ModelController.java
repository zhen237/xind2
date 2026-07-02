package com.comm.m03.controller;

import com.comm.common.Result;
import com.comm.m03.entity.Model;
import com.comm.m03.service.ModelService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/m03/model")
public class ModelController {

    @Autowired
    private ModelService modelService;

    @GetMapping
    public Result<List<Model>> list() {
        return Result.success(modelService.list());
    }

    @GetMapping("/{id}")
    public Result<Model> getById(@PathVariable Long id) {
        Model model = modelService.getById(id);
        if (model == null) {
            return Result.notFound("模型不存在");
        }
        return Result.success(model);
    }

    @GetMapping("/type/{modelType}")
    public Result<List<Model>> getByType(@PathVariable String modelType) {
        return Result.success(modelService.findByModelType(modelType));
    }

    @PostMapping
    public Result<Model> create(@RequestBody Model model) {
        modelService.save(model);
        return Result.success(model);
    }

    @PutMapping("/{id}")
    public Result<Boolean> update(@PathVariable Long id, @RequestBody Model model) {
        modelService.updateById(model);
        return Result.success(true);
    }

    @DeleteMapping("/{id}")
    public Result<Boolean> delete(@PathVariable Long id) {
        modelService.removeById(id);
        return Result.success(true);
    }
}
