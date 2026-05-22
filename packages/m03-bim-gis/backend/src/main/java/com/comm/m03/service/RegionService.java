package com.comm.m03.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.comm.m03.entity.Region;

import java.util.List;

public interface RegionService extends IService<Region> {
    
    List<Region> findByParentCode(String parentCode);
}