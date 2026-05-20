package com.comm.m05.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.comm.m05.entity.Device;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface DeviceMapper extends BaseMapper<Device> {
    @Select("SELECT * FROM m05_device WHERE station_code = #{stationCode}")
    List<Device> findByStationCode(String stationCode);

    @Select("SELECT * FROM m05_device WHERE status = #{status}")
    List<Device> findByStatus(Integer status);

    @Select("SELECT d.*, s.station_name FROM m05_device d " +
            "LEFT JOIN shared_station s ON d.station_code = s.station_code " +
            "WHERE d.id = #{id}")
    Device findByIdWithStation(Long id);
}
