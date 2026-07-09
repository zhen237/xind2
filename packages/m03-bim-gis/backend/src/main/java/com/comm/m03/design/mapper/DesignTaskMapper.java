package com.comm.m03.design.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.comm.m03.design.entity.DesignTask;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface DesignTaskMapper extends BaseMapper<DesignTask> {

    @Select("SELECT * FROM m03_design_task WHERE status = #{status} ORDER BY created_at DESC")
    List<DesignTask> selectByStatus(String status);
}