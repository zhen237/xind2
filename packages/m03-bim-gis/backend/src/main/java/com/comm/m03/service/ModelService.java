package com.comm.m03.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.comm.m03.entity.Model;

import java.util.List;

public interface ModelService extends IService<Model> {
    
    List<Model> findByModelType(String modelType);
}