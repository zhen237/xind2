package com.comm.m03.controller;

import com.comm.m03.entity.Region;
import com.comm.m03.service.RegionService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/m03/region")
public class RegionController {
    
    @Autowired
    private RegionService regionService;
    
    @GetMapping
    public ResponseEntity<List<Region>> getAllRegions() {
        return ResponseEntity.ok(regionService.list());
    }
    
    @GetMapping("/{id}")
    public ResponseEntity<Region> getRegionById(@PathVariable Long id) {
        Region region = regionService.getById(id);
        if (region == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(region);
    }
    
    @GetMapping("/parent/{parentCode}")
    public ResponseEntity<List<Region>> getRegionsByParentCode(@PathVariable String parentCode) {
        return ResponseEntity.ok(regionService.findByParentCode(parentCode));
    }
    
    @PostMapping
    public ResponseEntity<Region> createRegion(@RequestBody Region region) {
        regionService.save(region);
        return ResponseEntity.ok(region);
    }
    
    @PutMapping("/{id}")
    public ResponseEntity<Void> updateRegion(@PathVariable Long id, @RequestBody Region region) {
        regionService.updateById(region);
        return ResponseEntity.ok().build();
    }
    
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteRegion(@PathVariable Long id) {
        regionService.removeById(id);
        return ResponseEntity.noContent().build();
    }
}