package com.comm.m02.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.comm.m02.entity.GisFeature;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Delete;

import java.util.List;

@Mapper
public interface GisFeatureMapper extends BaseMapper<GisFeature> {

    @Select("SELECT * FROM m02_gis_feature WHERE fusion_task_id = #{fusionTaskId}")
    List<GisFeature> findByFusionTaskId(@Param("fusionTaskId") Long fusionTaskId);

    @Select("SELECT COUNT(*) FROM m02_gis_feature WHERE fusion_task_id = #{fusionTaskId}")
    int countByFusionTaskId(@Param("fusionTaskId") Long fusionTaskId);

    @Delete("DELETE FROM m02_gis_feature WHERE fusion_task_id = #{fusionTaskId}")
    void deleteByFusionTaskId(@Param("fusionTaskId") Long fusionTaskId);
}
