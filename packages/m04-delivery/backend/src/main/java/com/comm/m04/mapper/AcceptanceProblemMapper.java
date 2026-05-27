package com.comm.m04.mapper;

import com.baomidou.mybatisplus.core.conditions.Wrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.core.toolkit.Constants;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.comm.m04.entity.AcceptanceProblem;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

public interface AcceptanceProblemMapper extends com.baomidou.mybatisplus.core.mapper.BaseMapper<AcceptanceProblem> {
    
    @Select("SELECT * FROM m04_acceptance_problem ${ew.customSqlSegment}")
    IPage<AcceptanceProblem> selectPageWithCondition(Page<AcceptanceProblem> page, @Param(Constants.WRAPPER) Wrapper<AcceptanceProblem> wrapper);
}