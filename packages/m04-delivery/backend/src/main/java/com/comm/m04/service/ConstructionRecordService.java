package com.comm.m04.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.comm.m04.entity.ConstructionRecord;

public interface ConstructionRecordService {
    IPage<ConstructionRecord> list(Page<ConstructionRecord> page, Long projectId, String responsiblePerson);
    ConstructionRecord getById(Long id);
    boolean save(ConstructionRecord record);
    boolean update(ConstructionRecord record);
    boolean deleteById(Long id);
}