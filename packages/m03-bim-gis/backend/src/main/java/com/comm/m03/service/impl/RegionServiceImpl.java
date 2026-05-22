package com.comm.m03.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.comm.m03.entity.Region;
import com.comm.m03.mapper.RegionMapper;
import com.comm.m03.service.RegionService;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class RegionServiceImpl extends ServiceImpl<RegionMapper, Region> implements RegionService {
    
    @Override
    public List<Region> findByParentCode(String parentCode) {
        return getBaseMapper().findByParentCode(parentCode);
    }
}