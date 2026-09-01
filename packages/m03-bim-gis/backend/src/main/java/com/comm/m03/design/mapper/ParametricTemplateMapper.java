package com.comm.m03.design.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.comm.m03.design.entity.ParametricTemplate;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface ParametricTemplateMapper extends BaseMapper<ParametricTemplate> {

    /**
     * 按创建幂等键查询已存在模板（用于去重）。幂等键唯一索引，最多返回一条。
     */
    @Select("SELECT * FROM m03_parametric_template WHERE idempotency_key = #{key} LIMIT 1")
    ParametricTemplate selectByIdempotencyKey(String key);
}