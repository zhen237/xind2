package com.comm.m02.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.comm.m02.entity.CoordinateSystem;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface CoordinateSystemMapper extends BaseMapper<CoordinateSystem> {

    @Select("SELECT * FROM m02_coordinate_system WHERE epsg_code = #{epsgCode}")
    CoordinateSystem findByEpsgCode(@Param("epsgCode") String epsgCode);

    @Select("SELECT * FROM m02_coordinate_system WHERE is_preset = 1 ORDER BY epsg_code")
    List<CoordinateSystem> findAllPreset();

    @Select("SELECT * FROM m02_coordinate_system WHERE type = #{type} ORDER BY epsg_code")
    List<CoordinateSystem> findByType(@Param("type") String type);
}
