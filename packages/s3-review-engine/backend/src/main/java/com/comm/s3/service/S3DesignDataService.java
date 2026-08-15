package com.comm.s3.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.comm.s3.entity.S3DesignData;

import java.util.Map;

/**
 * S1 图纸设计数据持久化服务（B-1 MySQL 持久层）。
 */
public interface S3DesignDataService extends IService<S3DesignData> {

    /**
     * 原始图纸数据入库（upsert）：以 designTaskId 为主键，
     * 同一份图纸重复推送时更新而非重复插入。
     *
     * @param designTaskId  S1 图纸标识（主键）
     * @param taskId        本次接收创建的审查任务 ID（审计用）
     * @param designDataWrapper 缓存 wrapper：{"design_data": {...S1DesignDataDTO...}}
     */
    void saveDesignData(String designTaskId, Long taskId, Map<String, Object> designDataWrapper);

    /**
     * 根据 designTaskId 查询原始图纸数据（恢复用）。
     */
    S3DesignData getByDesignTaskId(String designTaskId);
}
