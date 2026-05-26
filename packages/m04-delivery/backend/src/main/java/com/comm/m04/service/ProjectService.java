package com.comm.m04.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.comm.m04.entity.Project;

public interface ProjectService {
    IPage<Project> list(Page<Project> page, String projectName, String regionCode);
    Project getById(Long id);
    boolean save(Project project);
    boolean update(Project project);
    boolean deleteById(Long id);
}