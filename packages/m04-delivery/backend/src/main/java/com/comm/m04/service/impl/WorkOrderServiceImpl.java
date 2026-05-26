package com.comm.m04.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.comm.m04.entity.WorkOrder;
import com.comm.m04.mapper.WorkOrderMapper;
import com.comm.m04.service.WorkOrderService;
import org.springframework.stereotype.Service;

@Service
public class WorkOrderServiceImpl extends ServiceImpl<WorkOrderMapper, WorkOrder> implements WorkOrderService {
    @Override
    public IPage<WorkOrder> list(Page<WorkOrder> page, String title, Integer status, String type) {
        LambdaQueryWrapper<WorkOrder> wrapper = new LambdaQueryWrapper<>();
        if (title != null && !title.isEmpty()) {
            wrapper.like(WorkOrder::getTitle, title);
        }
        if (status != null) {
            wrapper.eq(WorkOrder::getStatus, status);
        }
        if (type != null && !type.isEmpty()) {
            wrapper.eq(WorkOrder::getType, type);
        }
        wrapper.orderByDesc(WorkOrder::getCreateTime);
        return page(page, wrapper);
    }

    @Override
    public WorkOrder getById(Long id) {
        return baseMapper.selectById(id);
    }

    @Override
    public boolean save(WorkOrder workOrder) {
        if (workOrder.getOrderNo() == null || workOrder.getOrderNo().isEmpty()) {
            workOrder.setOrderNo("WO" + System.currentTimeMillis());
        }
        return baseMapper.insert(workOrder) > 0;
    }

    @Override
    public boolean update(WorkOrder workOrder) {
        return baseMapper.updateById(workOrder) > 0;
    }

    @Override
    public boolean deleteById(Long id) {
        return baseMapper.deleteById(id) > 0;
    }

    @Override
    public boolean updateStatus(Long id, Integer status) {
        WorkOrder workOrder = new WorkOrder();
        workOrder.setId(id);
        workOrder.setStatus(status);
        return baseMapper.updateById(workOrder) > 0;
    }
}