package com.comm.m05.controller;

import com.comm.m05.entity.Device;
import com.comm.m05.mapper.DeviceMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/m05/device")
public class DeviceController {
    @Autowired
    private DeviceMapper deviceMapper;

    @GetMapping
    public ResponseEntity<List<Device>> getAllDevices() {
        return ResponseEntity.ok(deviceMapper.selectList(null));
    }

    @GetMapping("/{id}")
    public ResponseEntity<Device> getDeviceById(@PathVariable Long id) {
        Device device = deviceMapper.selectById(id);
        if (device == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(device);
    }

    @GetMapping("/station/{stationCode}")
    public ResponseEntity<List<Device>> getDevicesByStation(@PathVariable String stationCode) {
        return ResponseEntity.ok(deviceMapper.findByStationCode(stationCode));
    }

    @GetMapping("/status/{status}")
    public ResponseEntity<List<Device>> getDevicesByStatus(@PathVariable Integer status) {
        return ResponseEntity.ok(deviceMapper.findByStatus(status));
    }

    @PostMapping
    public ResponseEntity<Device> createDevice(@RequestBody Device device) {
        deviceMapper.insert(device);
        return ResponseEntity.ok(device);
    }

    @PutMapping("/{id}")
    public ResponseEntity<Device> updateDevice(@PathVariable Long id, @RequestBody Device device) {
        device.setId(id);
        deviceMapper.updateById(device);
        return ResponseEntity.ok(device);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteDevice(@PathVariable Long id) {
        deviceMapper.deleteById(id);
        return ResponseEntity.noContent().build();
    }
}
