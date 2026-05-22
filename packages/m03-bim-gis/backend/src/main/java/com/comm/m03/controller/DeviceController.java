package com.comm.m03.controller;

import com.comm.m03.entity.Device;
import com.comm.m03.service.DeviceService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/m03/device")
public class DeviceController {
    
    @Autowired
    private DeviceService deviceService;
    
    @GetMapping
    public ResponseEntity<List<Device>> getAllDevices() {
        return ResponseEntity.ok(deviceService.list());
    }
    
    @GetMapping("/{id}")
    public ResponseEntity<Device> getDeviceById(@PathVariable Long id) {
        Device device = deviceService.getById(id);
        if (device == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(device);
    }
    
    @GetMapping("/project/{projectId}")
    public ResponseEntity<List<Device>> getDevicesByProjectId(@PathVariable Long projectId) {
        return ResponseEntity.ok(deviceService.findByProjectId(projectId));
    }
    
    @GetMapping("/station/{stationCode}")
    public ResponseEntity<List<Device>> getDevicesByStationCode(@PathVariable String stationCode) {
        return ResponseEntity.ok(deviceService.findByStationCode(stationCode));
    }
    
    @GetMapping("/type/{deviceType}")
    public ResponseEntity<List<Device>> getDevicesByType(@PathVariable String deviceType) {
        return ResponseEntity.ok(deviceService.findByDeviceType(deviceType));
    }
    
    @PostMapping
    public ResponseEntity<Device> createDevice(@RequestBody Device device) {
        deviceService.save(device);
        return ResponseEntity.ok(device);
    }
    
    @PutMapping("/{id}")
    public ResponseEntity<Void> updateDevice(@PathVariable Long id, @RequestBody Device device) {
        deviceService.updateById(device);
        return ResponseEntity.ok().build();
    }
    
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteDevice(@PathVariable Long id) {
        deviceService.removeById(id);
        return ResponseEntity.noContent().build();
    }
}