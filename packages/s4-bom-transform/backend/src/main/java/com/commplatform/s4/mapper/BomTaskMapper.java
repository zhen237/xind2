package com.commplatform.s4.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.commplatform.s4.entity.BomTask;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/**
 * s4_bom_task Mapper。
 */
@Mapper
public interface BomTaskMapper extends BaseMapper<BomTask> {

    IPage<BomTask> selectHistoryPage(Page<BomTask> page, @Param("projectId") String projectId);
}
