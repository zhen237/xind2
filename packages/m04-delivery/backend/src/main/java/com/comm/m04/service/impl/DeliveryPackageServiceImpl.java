package com.comm.m04.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.comm.m04.entity.DeliveryPackage;
import com.comm.m04.mapper.DeliveryPackageMapper;
import com.comm.m04.service.DeliveryPackageService;
import org.springframework.stereotype.Service;

@Service
public class DeliveryPackageServiceImpl extends ServiceImpl<DeliveryPackageMapper, DeliveryPackage> implements DeliveryPackageService {
    @Override
    public IPage<DeliveryPackage> list(Page<DeliveryPackage> page, Long projectId, Integer status) {
        LambdaQueryWrapper<DeliveryPackage> wrapper = new LambdaQueryWrapper<>();
        if (projectId != null) {
            wrapper.eq(DeliveryPackage::getProjectId, projectId);
        }
        if (status != null) {
            wrapper.eq(DeliveryPackage::getStatus, status);
        }
        wrapper.orderByDesc(DeliveryPackage::getCreateTime);
        return page(page, wrapper);
    }

    @Override
    public DeliveryPackage getById(Long id) {
        return baseMapper.selectById(id);
    }

    @Override
    public boolean save(DeliveryPackage deliveryPackage) {
        return baseMapper.insert(deliveryPackage) > 0;
    }

    @Override
    public boolean update(DeliveryPackage deliveryPackage) {
        return baseMapper.updateById(deliveryPackage) > 0;
    }

    @Override
    public boolean deleteById(Long id) {
        return baseMapper.deleteById(id) > 0;
    }

    @Override
    public boolean updateStatus(Long id, Integer status) {
        DeliveryPackage deliveryPackage = new DeliveryPackage();
        deliveryPackage.setId(id);
        deliveryPackage.setStatus(status);
        return baseMapper.updateById(deliveryPackage) > 0;
    }
}