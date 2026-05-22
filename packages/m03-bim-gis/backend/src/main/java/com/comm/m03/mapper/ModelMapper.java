package com.comm.m03.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.comm.m03.entity.Model;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface ModelMapper extends BaseMapper<Model> {
    
    @Select("SELECT * FROM m03_model WHERE model_type = #{modelType}")
    List<Model> findByModelType(String modelType);
}