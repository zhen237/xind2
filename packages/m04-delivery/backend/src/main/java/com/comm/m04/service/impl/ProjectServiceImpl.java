package com.comm.m04.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.comm.m04.entity.Project;
import com.comm.m04.mapper.ProjectMapper;
import com.comm.m04.service.ProjectService;
import org.springframework.stereotype.Service;

@Service
public class ProjectServiceImpl extends ServiceImpl<ProjectMapper, Project> implements ProjectService {
    @Override
    public IPage<Project> list(Page<Project> page, String projectName, String regionCode) {
        LambdaQueryWrapper<Project> wrapper = new LambdaQueryWrapper<>();
        if (projectName != null && !projectName.isEmpty()) {
            wrapper.like(Project::getProjectName, projectName);
        }
        if (regionCode != null && !regionCode.isEmpty()) {
            wrapper.eq(Project::getRegionCode, regionCode);
        }
        wrapper.orderByDesc(Project::getCreateTime);
        return page(page, wrapper);
    }

    @Override
    public Project getById(Long id) {
        return baseMapper.selectById(id);
    }

    @Override
    public boolean save(Project project) {
        return baseMapper.insert(project) > 0;
    }

    @Override
    public boolean update(Project project) {
        return baseMapper.updateById(project) > 0;
    }

    @Override
    public boolean deleteById(Long id) {
        return baseMapper.deleteById(id) > 0;
    }
}