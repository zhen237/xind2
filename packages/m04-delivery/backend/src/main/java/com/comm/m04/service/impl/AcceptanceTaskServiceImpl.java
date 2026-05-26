package com.comm.m04.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.comm.m04.entity.AcceptanceTask;
import com.comm.m04.mapper.AcceptanceTaskMapper;
import com.comm.m04.service.AcceptanceTaskService;
import org.springframework.stereotype.Service;

@Service
public class AcceptanceTaskServiceImpl extends ServiceImpl<AcceptanceTaskMapper, AcceptanceTask> implements AcceptanceTaskService {
    @Override
    public IPage<AcceptanceTask> list(Page<AcceptanceTask> page, Long projectId, Integer status) {
        LambdaQueryWrapper<AcceptanceTask> wrapper = new LambdaQueryWrapper<>();
        if (projectId != null) {
            wrapper.eq(AcceptanceTask::getProjectId, projectId);
        }
        if (status != null) {
            wrapper.eq(AcceptanceTask::getStatus, status);
        }
        wrapper.orderByDesc(AcceptanceTask::getCreateTime);
        return page(page, wrapper);
    }

    @Override
    public AcceptanceTask getById(Long id) {
        return baseMapper.selectById(id);
    }

    @Override
    public boolean save(AcceptanceTask task) {
        return baseMapper.insert(task) > 0;
    }

    @Override
    public boolean update(AcceptanceTask task) {
        return baseMapper.updateById(task) > 0;
    }

    @Override
    public boolean deleteById(Long id) {
        return baseMapper.deleteById(id) > 0;
    }

    @Override
    public boolean updateStatus(Long id, Integer status) {
        AcceptanceTask task = new AcceptanceTask();
        task.setId(id);
        task.setStatus(status);
        return baseMapper.updateById(task) > 0;
    }
}