package com.comm.m03.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.comm.m03.entity.Device;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface DeviceMapper extends BaseMapper<Device> {
    
    @Select("SELECT * FROM m03_device WHERE project_id = #{projectId}")
    List<Device> findByProjectId(Long projectId);
    
    @Select("SELECT * FROM m03_device WHERE station_code = #{stationCode}")
    List<Device> findByStationCode(String stationCode);
    
    @Select("SELECT * FROM m03_device WHERE device_type = #{deviceType}")
    List<Device> findByDeviceType(String deviceType);
}