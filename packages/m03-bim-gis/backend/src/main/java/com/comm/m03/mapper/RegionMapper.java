package com.comm.m03.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.comm.m03.entity.Region;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface RegionMapper extends BaseMapper<Region> {
    
    @Select("SELECT * FROM m03_region WHERE parent_code = #{parentCode}")
    List<Region> findByParentCode(String parentCode);
}