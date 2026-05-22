package com.comm.m03.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.comm.m03.entity.Device;

import java.util.List;

public interface DeviceService extends IService<Device> {
    
    List<Device> findByProjectId(Long projectId);
    
    List<Device> findByStationCode(String stationCode);
    
    List<Device> findByDeviceType(String deviceType);
}