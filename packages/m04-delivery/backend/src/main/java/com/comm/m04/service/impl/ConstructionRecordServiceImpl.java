package com.comm.m04.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.comm.m04.entity.ConstructionRecord;
import com.comm.m04.mapper.ConstructionRecordMapper;
import com.comm.m04.service.ConstructionRecordService;
import org.springframework.stereotype.Service;

@Service
public class ConstructionRecordServiceImpl extends ServiceImpl<ConstructionRecordMapper, ConstructionRecord> implements ConstructionRecordService {
    @Override
    public IPage<ConstructionRecord> list(Page<ConstructionRecord> page, Long projectId, String responsiblePerson) {
        LambdaQueryWrapper<ConstructionRecord> wrapper = new LambdaQueryWrapper<>();
        if (projectId != null) {
            wrapper.eq(ConstructionRecord::getProjectId, projectId);
        }
        if (responsiblePerson != null && !responsiblePerson.isEmpty()) {
            wrapper.like(ConstructionRecord::getResponsiblePerson, responsiblePerson);
        }
        wrapper.orderByDesc(ConstructionRecord::getCreateTime);
        return page(page, wrapper);
    }

    @Override
    public ConstructionRecord getById(Long id) {
        return baseMapper.selectById(id);
    }

    @Override
    public boolean save(ConstructionRecord record) {
        return baseMapper.insert(record) > 0;
    }

    @Override
    public boolean update(ConstructionRecord record) {
        return baseMapper.updateById(record) > 0;
    }

    @Override
    public boolean deleteById(Long id) {
        return baseMapper.deleteById(id) > 0;
    }
}