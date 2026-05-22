package com.comm.m03.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.comm.m03.entity.Model;
import com.comm.m03.mapper.ModelMapper;
import com.comm.m03.service.ModelService;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class ModelServiceImpl extends ServiceImpl<ModelMapper, Model> implements ModelService {
    
    @Override
    public List<Model> findByModelType(String modelType) {
        return getBaseMapper().findByModelType(modelType);
    }
}