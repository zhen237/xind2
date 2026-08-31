package com.comm.m02.dto.response;

import com.comm.m02.entity.FusionTask;
import lombok.Data;

@Data
public class FusionResultResponse {
    private Long taskId;
    private String taskName;
    private String status;
    private String statusText;
    private Integer featureCount;
    private String resultFilePath;
    private String errorMessage;
    private String createTime;
    private String completionTime;

    public static FusionResultResponse fromEntity(FusionTask entity) {
        FusionResultResponse response = new FusionResultResponse();
        response.setTaskId(entity.getId());
        response.setTaskName(entity.getTaskName());
        int status = entity.getStatus() != null ? entity.getStatus() : 0;
        response.setStatus(status == 1 ? "PROCESSING" :
                          status == 2 ? "COMPLETED" :
                          status == 3 ? "FAILED" : "PENDING");
        response.setStatusText(status == 1 ? "融合中" :
                               status == 2 ? "已完成" :
                               status == 3 ? "失败" : "待处理");
        response.setFeatureCount(entity.getFeatureCount());
        response.setResultFilePath(entity.getResultFilePath());
        response.setErrorMessage(entity.getErrorMessage());
        response.setCreateTime(entity.getCreateTime() != null ? entity.getCreateTime().toString() : null);
        response.setCompletionTime(entity.getUpdateTime() != null ? entity.getUpdateTime().toString() : null);
        return response;
    }
}
