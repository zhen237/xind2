package com.comm.m03.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.comm.m03.entity.Device;
import com.comm.m03.mapper.DeviceMapper;
import com.comm.m03.service.DeviceService;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class DeviceServiceImpl extends ServiceImpl<DeviceMapper, Device> implements DeviceService {
    
    @Override
    public List<Device> findByProjectId(Long projectId) {
        return getBaseMapper().findByProjectId(projectId);
    }
    
    @Override
    public List<Device> findByStationCode(String stationCode) {
        return getBaseMapper().findByStationCode(stationCode);
    }
    
    @Override
    public List<Device> findByDeviceType(String deviceType) {
        return getBaseMapper().findByDeviceType(deviceType);
    }
}