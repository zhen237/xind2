package com.comm.m04.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.comm.m04.entity.DeliveryPackage;

public interface DeliveryPackageService {
    IPage<DeliveryPackage> list(Page<DeliveryPackage> page, Long projectId, Integer status);
    DeliveryPackage getById(Long id);
    boolean save(DeliveryPackage deliveryPackage);
    boolean update(DeliveryPackage deliveryPackage);
    boolean deleteById(Long id);
    boolean updateStatus(Long id, Integer status);
}