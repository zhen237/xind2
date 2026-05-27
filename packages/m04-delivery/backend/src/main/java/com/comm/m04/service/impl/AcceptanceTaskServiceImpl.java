package com.comm.m04.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.comm.m04.entity.AcceptanceTask;
import com.comm.m04.mapper.AcceptanceTaskMapper;
import com.comm.m04.service.AcceptanceTaskService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class AcceptanceTaskServiceImpl implements AcceptanceTaskService {

    @Autowired
    private AcceptanceTaskMapper acceptanceTaskMapper;

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
        return acceptanceTaskMapper.selectPage(page, wrapper);
    }

    @Override
    public AcceptanceTask getById(Long id) {
        return acceptanceTaskMapper.selectById(id);
    }

    @Override
    public boolean save(AcceptanceTask task) {
        return acceptanceTaskMapper.insert(task) > 0;
    }

    @Override
    public boolean update(AcceptanceTask task) {
        return acceptanceTaskMapper.updateById(task) > 0;
    }

    @Override
    public boolean deleteById(Long id) {
        return acceptanceTaskMapper.deleteById(id) > 0;
    }

    @Override
    public boolean updateStatus(Long id, Integer status) {
        AcceptanceTask task = new AcceptanceTask();
        task.setId(id);
        task.setStatus(status);
        return acceptanceTaskMapper.updateById(task) > 0;
    }
}