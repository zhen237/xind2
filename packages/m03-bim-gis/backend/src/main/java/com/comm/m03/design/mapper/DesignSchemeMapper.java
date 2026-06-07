package com.comm.m03.design.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.comm.m03.design.entity.DesignScheme;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

/**
 * 设计方案Mapper
 */
@Mapper
public interface DesignSchemeMapper extends BaseMapper<DesignScheme> {

    /**
     * 根据项目ID查询设计方案
     * @param projectId 项目ID
     * @return 设计方案
     */
    @Select("SELECT * FROM m03_design_scheme WHERE project_id = #{projectId} ORDER BY create_time DESC LIMIT 1")
    DesignScheme selectByProjectId(Long projectId);
}
