package com.comm.s3.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.comm.s3.entity.S3DesignData;
import com.comm.s3.mapper.S3DesignDataMapper;
import com.comm.s3.service.S3DesignDataService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

/**
 * S1 图纸设计数据持久化实现（B-1 MySQL 持久层）。
 */
@Service
public class S3DesignDataServiceImpl extends ServiceImpl<S3DesignDataMapper, S3DesignData> implements S3DesignDataService {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public void saveDesignData(String designTaskId, Long taskId, Map<String, Object> designDataWrapper) {
        if (designTaskId == null || designTaskId.trim().isEmpty() || designDataWrapper == null) {
            return;
        }
        S3DesignData entity = new S3DesignData();
        entity.setDesignTaskId(designTaskId);
        entity.setTaskId(taskId);
        entity.setCreateTime(LocalDateTime.now());

        try {
            // 完整设计数据 JSON（缓存 wrapper，保证恢复后结构与 Redis/内存态一致）
            entity.setDesignDataJson(objectMapper.writeValueAsString(designDataWrapper));
            // 工程元信息（冗余存储，便于直接查询展示）
            entity.setProjectMetaJson(objectMapper.writeValueAsString(buildProjectMeta(designDataWrapper)));
        } catch (Exception e) {
            throw new RuntimeException("序列化 S1 设计数据失败: " + e.getMessage(), e);
        }

        // upsert：同一 designTaskId 重复推送时更新而非新增
        this.saveOrUpdate(entity);
    }

    @Override
    public S3DesignData getByDesignTaskId(String designTaskId) {
        if (designTaskId == null || designTaskId.trim().isEmpty()) {
            return null;
        }
        LambdaQueryWrapper<S3DesignData> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(S3DesignData::getDesignTaskId, designTaskId);
        return this.getOne(wrapper);
    }

    /** 从缓存 wrapper 中提取工程元信息 */
    private Map<String, Object> buildProjectMeta(Map<String, Object> wrapper) {
        Map<String, Object> meta = new java.util.HashMap<>();
        Object dd = wrapper.get("design_data");
        if (!(dd instanceof Map)) {
            return meta;
        }
        @SuppressWarnings("unchecked")
        Map<String, Object> ddm = (Map<String, Object>) dd;
        meta.put("designTaskId", ddm.get("designTaskId"));
        meta.put("designTaskName", ddm.get("designTaskName"));
        meta.put("designType", ddm.get("designType"));

        Object m = ddm.get("metadata");
        if (m instanceof Map) {
            @SuppressWarnings("unchecked")
            Map<String, Object> md = (Map<String, Object>) m;
            meta.put("projectName", md.get("projectName"));
            meta.put("region", md.get("region"));
            meta.put("layerCounts", md.get("layerCounts"));
            meta.put("totalDevices", md.get("totalDevices"));
        }
        Object devs = ddm.get("devices");
        if (devs instanceof List) {
            meta.put("deviceCount", ((List<?>) devs).size());
        }
        return meta;
    }
}
