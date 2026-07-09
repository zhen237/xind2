package com.comm.m03.design.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.comm.m03.design.entity.GeneratedLayout;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface GeneratedLayoutMapper extends BaseMapper<GeneratedLayout> {

    @Delete("DELETE FROM m03_generated_layout WHERE task_id = #{taskId}")
    void deleteByTaskId(@Param("taskId") Long taskId);
}