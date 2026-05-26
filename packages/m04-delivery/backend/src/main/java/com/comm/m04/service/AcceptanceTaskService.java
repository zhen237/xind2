package com.comm.m04.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.comm.m04.entity.AcceptanceTask;

public interface AcceptanceTaskService {
    IPage<AcceptanceTask> list(Page<AcceptanceTask> page, Long projectId, Integer status);
    AcceptanceTask getById(Long id);
    boolean save(AcceptanceTask task);
    boolean update(AcceptanceTask task);
    boolean deleteById(Long id);
    boolean updateStatus(Long id, Integer status);
}