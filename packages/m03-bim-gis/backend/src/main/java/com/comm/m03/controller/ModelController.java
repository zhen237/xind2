package com.comm.m03.controller;

import com.comm.m03.entity.Model;
import com.comm.m03.service.ModelService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/m03/model")
public class ModelController {
    
    @Autowired
    private ModelService modelService;
    
    @GetMapping
    public ResponseEntity<List<Model>> getAllModels() {
        return ResponseEntity.ok(modelService.list());
    }
    
    @GetMapping("/{id}")
    public ResponseEntity<Model> getModelById(@PathVariable Long id) {
        Model model = modelService.getById(id);
        if (model == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(model);
    }
    
    @GetMapping("/type/{modelType}")
    public ResponseEntity<List<Model>> getModelsByType(@PathVariable String modelType) {
        return ResponseEntity.ok(modelService.findByModelType(modelType));
    }
    
    @PostMapping
    public ResponseEntity<Model> createModel(@RequestBody Model model) {
        modelService.save(model);
        return ResponseEntity.ok(model);
    }
    
    @PutMapping("/{id}")
    public ResponseEntity<Void> updateModel(@PathVariable Long id, @RequestBody Model model) {
        modelService.updateById(model);
        return ResponseEntity.ok().build();
    }
    
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteModel(@PathVariable Long id) {
        modelService.removeById(id);
        return ResponseEntity.noContent().build();
    }
}