package com.comm.m04.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.comm.m04.entity.AcceptanceProblem;

public interface AcceptanceProblemService {
    IPage<AcceptanceProblem> list(Page<AcceptanceProblem> page, Long taskId, Integer status);
    AcceptanceProblem getById(Long id);
    boolean save(AcceptanceProblem problem);
    boolean update(AcceptanceProblem problem);
    boolean deleteById(Long id);
    boolean updateStatus(Long id, Integer status);
}