package com.comm.m02.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.comm.m02.entity.FusionTask;
import com.comm.m02.dto.request.FusionRequest;
import com.comm.m02.dto.response.FusionResultResponse;

import java.util.List;

public interface CadFusionService extends IService<FusionTask> {

    FusionResultResponse createFusionTask(FusionRequest request, Long userId);

    FusionResultResponse getFusionTask(Long taskId);

    List<FusionResultResponse> getFusionTasksByProject(Long projectId);

    List<FusionResultResponse> getFusionTasksByUser(Long userId);

    FusionResultResponse executeFusionTask(Long taskId);

    boolean deleteFusionTask(Long taskId);

    String getFusionResultGeoJson(Long taskId);
}
