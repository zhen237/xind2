package com.comm.m04.mapper;

import com.baomidou.mybatisplus.core.conditions.Wrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.core.toolkit.Constants;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.comm.m04.entity.AcceptanceTask;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

public interface AcceptanceTaskMapper extends com.baomidou.mybatisplus.core.mapper.BaseMapper<AcceptanceTask> {
    
    @Select("SELECT * FROM m04_acceptance_task ${ew.customSqlSegment}")
    IPage<AcceptanceTask> selectPageWithCondition(Page<AcceptanceTask> page, @Param(Constants.WRAPPER) Wrapper<AcceptanceTask> wrapper);
}