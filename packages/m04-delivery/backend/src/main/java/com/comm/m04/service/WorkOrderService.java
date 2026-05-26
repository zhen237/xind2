package com.comm.m04.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.comm.m04.entity.WorkOrder;

public interface WorkOrderService {
    IPage<WorkOrder> list(Page<WorkOrder> page, String title, Integer status, String type);
    WorkOrder getById(Long id);
    boolean save(WorkOrder workOrder);
    boolean update(WorkOrder workOrder);
    boolean deleteById(Long id);
    boolean updateStatus(Long id, Integer status);
}