package com.comm.m02.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.comm.m02.common.BusinessException;
import com.comm.m02.config.FileStorageConfig;
import com.comm.m02.dto.request.FusionRequest;
import com.comm.m02.dto.response.FusionResultResponse;
import com.comm.m02.entity.CadFile;
import com.comm.m02.entity.FusionTask;
import com.comm.m02.entity.GisFeature;
import com.comm.m02.fusion.FusionEngine;
import com.comm.m02.mapper.CadFileMapper;
import com.comm.m02.mapper.FusionTaskMapper;
import com.comm.m02.mapper.GisFeatureMapper;
import com.comm.m02.service.CadFusionService;
import com.comm.m02.service.CadFileService;
import com.comm.m02.utils.FileUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class CadFusionServiceImpl extends ServiceImpl<FusionTaskMapper, FusionTask> implements CadFusionService {

    private static final Logger log = LoggerFactory.getLogger(CadFusionServiceImpl.class);

    @Autowired
    private CadFileService cadFileService;

    @Autowired
    private GisFeatureMapper gisFeatureMapper;

    @Autowired
    private FusionEngine fusionEngine;

    @Autowired
    private FileStorageConfig fileStorageConfig;

    @Override
    @Transactional
    public FusionResultResponse createFusionTask(FusionRequest request, Long userId) {
        if (request.getSourceFileId() == null) {
            throw new BusinessException(400, "请选择要融合的CAD文件");
        }

        CadFile sourceFile = cadFileService.getFileById(request.getSourceFileId());

        FusionTask task = new FusionTask();
        task.setTaskName(request.getTaskName() != null ? request.getTaskName() : "融合任务-" + System.currentTimeMillis());
        task.setProjectId(request.getProjectId());
        task.setSourceFileId(request.getSourceFileId());
        task.setSourceEpsg(request.getSourceEpsg() != null ? request.getSourceEpsg() : sourceFile.getSourceEpsg());
        task.setTargetEpsg(request.getTargetEpsg() != null ? request.getTargetEpsg() : "EPSG:4326");
        task.setTransformationType(request.getTransformationType() != null ? request.getTransformationType() : "AUTO");
        task.setStatus(0);
        task.setCreatedBy(userId);
        task.setCreateTime(LocalDateTime.now());
        task.setUpdateTime(LocalDateTime.now());

        this.save(task);

        log.info("融合任务创建成功: id={}, name={}", task.getId(), task.getTaskName());

        return FusionResultResponse.fromEntity(task);
    }

    @Override
    public FusionResultResponse getFusionTask(Long taskId) {
        FusionTask task = this.getById(taskId);
        if (task == null) {
            throw new BusinessException(404, "融合任务不存在");
        }
        return FusionResultResponse.fromEntity(task);
    }

    @Override
    public List<FusionResultResponse> getFusionTasksByProject(Long projectId) {
        List<FusionTask> tasks = baseMapper.findByProjectId(projectId);
        return tasks.stream().map(FusionResultResponse::fromEntity).toList();
    }

    @Override
    public List<FusionResultResponse> getFusionTasksByUser(Long userId) {
        List<FusionTask> tasks = baseMapper.findByUserId(userId);
        return tasks.stream().map(FusionResultResponse::fromEntity).toList();
    }

    @Override
    @Transactional
    public FusionResultResponse executeFusionTask(Long taskId) {
        FusionTask task = this.getById(taskId);
        if (task == null) {
            throw new BusinessException(404, "融合任务不存在");
        }

        task.setStatus(1);
        task.setUpdateTime(LocalDateTime.now());
        this.updateById(task);

        try {
            CadFile sourceFile = cadFileService.getFileById(task.getSourceFileId());

            FusionEngine.FusionConfig config = new FusionEngine.FusionConfig();
            config.setSourceFilePath(sourceFile.getFilePath());
            config.setFileType(sourceFile.getFileType());
            config.setSourceEpsg(task.getSourceEpsg());
            config.setTargetEpsg(task.getTargetEpsg());
            config.setTransformationType(task.getTransformationType());

            FusionEngine.FusionResult fusionResult = fusionEngine.fuse(config);

            if (fusionResult.isSuccess()) {
                saveGisFeatures(task.getId(), fusionResult.getGisFeatures());
                
                String outputPath = fileStorageConfig.getOutputDir() + "/" + task.getId() + ".geojson";
                String geoJson = fusionEngine.generateGeoJson(fusionResult);
                FileUtils.writeStringToFile(geoJson, outputPath);

                task.setStatus(2);
                task.setFeatureCount(fusionResult.getFeatureCount());
                task.setResultFilePath(outputPath);
                task.setErrorMessage(null);
            } else {
                task.setStatus(3);
                task.setErrorMessage(fusionResult.getMessage());
            }

        } catch (Exception e) {
            log.error("融合任务执行失败", e);
            task.setStatus(3);
            task.setErrorMessage("执行失败: " + e.getMessage());
        }

        task.setUpdateTime(LocalDateTime.now());
        this.updateById(task);

        log.info("融合任务执行完成: id={}, status={}", task.getId(), task.getStatus());

        return FusionResultResponse.fromEntity(task);
    }

    private void saveGisFeatures(Long fusionTaskId, List<GisFeature> features) {
        if (features == null || features.isEmpty()) {
            return;
        }

        gisFeatureMapper.deleteByFusionTaskId(fusionTaskId);
        
        for (GisFeature feature : features) {
            feature.setFusionTaskId(fusionTaskId);
            feature.setCreateTime(LocalDateTime.now());
            gisFeatureMapper.insert(feature);
        }
    }

    @Override
    @Transactional
    public boolean deleteFusionTask(Long taskId) {
        FusionTask task = this.getById(taskId);
        if (task == null) {
            throw new BusinessException(404, "融合任务不存在");
        }

        gisFeatureMapper.deleteByFusionTaskId(taskId);

        if (task.getResultFilePath() != null) {
            try {
                FileUtils.deleteFile(task.getResultFilePath());
            } catch (Exception e) {
                log.warn("删除结果文件失败: {}", task.getResultFilePath());
            }
        }

        this.removeById(taskId);
        log.info("融合任务删除成功: id={}", taskId);
        return true;
    }

    @Override
    public String getFusionResultGeoJson(Long taskId) {
        FusionTask task = this.getById(taskId);
        if (task == null) {
            throw new BusinessException(404, "融合任务不存在");
        }
        if (task.getStatus() != 2) {
            throw new BusinessException(400, "融合任务尚未完成");
        }
        if (task.getResultFilePath() == null) {
            throw new BusinessException(400, "融合结果文件不存在");
        }

        try {
            return FileUtils.readFileAsString(task.getResultFilePath());
        } catch (Exception e) {
            throw new BusinessException(500, "读取融合结果失败: " + e.getMessage());
        }
    }
}
