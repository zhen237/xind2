package com.comm.m05.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.comm.m05.entity.Alert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface AlertMapper extends BaseMapper<Alert> {
    @Select("SELECT * FROM m05_alert WHERE device_id = #{deviceId} ORDER BY create_time DESC")
    List<Alert> findByDeviceId(Long deviceId);

    @Select("SELECT * FROM m05_alert WHERE status = #{status} ORDER BY create_time DESC")
    List<Alert> findByStatus(Integer status);

    @Select("SELECT * FROM m05_alert WHERE level = #{level} ORDER BY create_time DESC")
    List<Alert> findByLevel(Integer level);

    @Select("SELECT * FROM m05_alert ORDER BY create_time DESC LIMIT #{limit}")
    List<Alert> findRecent(int limit);

    @Select("SELECT COUNT(*) FROM m05_alert WHERE status = 0")
    long countUnprocessed();

    @Select("SELECT COUNT(*) FROM m05_alert WHERE level = #{level} AND status = 0")
    long countUnprocessedByLevel(Integer level);
}
