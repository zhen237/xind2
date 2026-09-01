package com.comm.m02.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.comm.m02.entity.FusionTask;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface FusionTaskMapper extends BaseMapper<FusionTask> {

    @Select("SELECT * FROM m02_fusion_task WHERE project_id = #{projectId} ORDER BY create_time DESC")
    List<FusionTask> findByProjectId(@Param("projectId") Long projectId);

    @Select("SELECT * FROM m02_fusion_task WHERE created_by = #{userId} ORDER BY create_time DESC")
    List<FusionTask> findByUserId(@Param("userId") Long userId);

    @Select("SELECT * FROM m02_fusion_task WHERE status = #{status}")
    List<FusionTask> findByStatus(@Param("status") Integer status);
}
