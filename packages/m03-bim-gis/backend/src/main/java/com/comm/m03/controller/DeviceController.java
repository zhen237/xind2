package com.comm.m03.controller;

import com.comm.common.Result;
import com.comm.m03.entity.Device;
import com.comm.m03.service.DeviceService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/m03/device")
public class DeviceController {

    @Autowired
    private DeviceService deviceService;

    @GetMapping
    public Result<List<Device>> list() {
        return Result.success(deviceService.list());
    }

    @GetMapping("/{id}")
    public Result<Device> getById(@PathVariable Long id) {
        Device device = deviceService.getById(id);
        if (device == null) {
            return Result.notFound("设备不存在");
        }
        return Result.success(device);
    }

    @GetMapping("/project/{projectId}")
    public Result<List<Device>> getByProjectId(@PathVariable Long projectId) {
        return Result.success(deviceService.findByProjectId(projectId));
    }

    @GetMapping("/station/{stationCode}")
    public Result<List<Device>> getByStationCode(@PathVariable String stationCode) {
        return Result.success(deviceService.findByStationCode(stationCode));
    }

    @GetMapping("/type/{deviceType}")
    public Result<List<Device>> getByType(@PathVariable String deviceType) {
        return Result.success(deviceService.findByDeviceType(deviceType));
    }

    @PostMapping
    public Result<Device> create(@RequestBody Device device) {
        deviceService.save(device);
        return Result.success(device);
    }

    @PutMapping("/{id}")
    public Result<Boolean> update(@PathVariable Long id, @RequestBody Device device) {
        deviceService.updateById(device);
        return Result.success(true);
    }

    @DeleteMapping("/{id}")
    public Result<Boolean> delete(@PathVariable Long id) {
        deviceService.removeById(id);
        return Result.success(true);
    }
}
