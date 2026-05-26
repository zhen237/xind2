package com.comm.m04.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.comm.m04.entity.AcceptanceProblem;
import com.comm.m04.mapper.AcceptanceProblemMapper;
import com.comm.m04.service.AcceptanceProblemService;
import org.springframework.stereotype.Service;

@Service
public class AcceptanceProblemServiceImpl extends ServiceImpl<AcceptanceProblemMapper, AcceptanceProblem> implements AcceptanceProblemService {
    @Override
    public IPage<AcceptanceProblem> list(Page<AcceptanceProblem> page, Long taskId, Integer status) {
        LambdaQueryWrapper<AcceptanceProblem> wrapper = new LambdaQueryWrapper<>();
        if (taskId != null) {
            wrapper.eq(AcceptanceProblem::getTaskId, taskId);
        }
        if (status != null) {
            wrapper.eq(AcceptanceProblem::getStatus, status);
        }
        wrapper.orderByDesc(AcceptanceProblem::getCreateTime);
        return page(page, wrapper);
    }

    @Override
    public AcceptanceProblem getById(Long id) {
        return baseMapper.selectById(id);
    }

    @Override
    public boolean save(AcceptanceProblem problem) {
        return baseMapper.insert(problem) > 0;
    }

    @Override
    public boolean update(AcceptanceProblem problem) {
        return baseMapper.updateById(problem) > 0;
    }

    @Override
    public boolean deleteById(Long id) {
        return baseMapper.deleteById(id) > 0;
    }

    @Override
    public boolean updateStatus(Long id, Integer status) {
        AcceptanceProblem problem = new AcceptanceProblem();
        problem.setId(id);
        problem.setStatus(status);
        return baseMapper.updateById(problem) > 0;
    }
}