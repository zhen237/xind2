package com.comm.s2.controller;

import com.comm.s2.common.Result;
import com.comm.s2.dto.request.FusionRequest;
import com.comm.s2.dto.response.FusionResultResponse;
import com.comm.s2.service.CadFusionService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/s2/cad/fusion")
public class FusionController {

    @Autowired
    private CadFusionService fusionService;

    @PostMapping("/tasks")
    public Result<FusionResultResponse> createFusionTask(@RequestBody FusionRequest request) {
        FusionResultResponse response = fusionService.createFusionTask(request, null);
        return Result.success("创建成功", response);
    }

    @GetMapping("/tasks/{taskId}")
    public Result<FusionResultResponse> getFusionTask(@PathVariable Long taskId) {
        FusionResultResponse response = fusionService.getFusionTask(taskId);
        return Result.success(response);
    }

    @GetMapping("/tasks")
    public Result<List<FusionResultResponse>> getFusionTasks(
            @RequestParam(value = "projectId", required = false) Long projectId,
            @RequestParam(value = "userId", required = false) Long userId) {
        
        List<FusionResultResponse> tasks;
        if (projectId != null) {
            tasks = fusionService.getFusionTasksByProject(projectId);
        } else if (userId != null) {
            tasks = fusionService.getFusionTasksByUser(userId);
        } else {
            tasks = fusionService.list().stream()
                    .map(FusionResultResponse::fromEntity)
                    .toList();
        }
        
        return Result.success(tasks);
    }

    @PostMapping("/tasks/{taskId}/execute")
    public Result<FusionResultResponse> executeFusionTask(@PathVariable Long taskId) {
        FusionResultResponse response = fusionService.executeFusionTask(taskId);
        return Result.success("执行完成", response);
    }

    @PostMapping("/auto-fuse")
    public Result<FusionResultResponse> autoFuse(@RequestBody FusionRequest request) {
        FusionResultResponse task = fusionService.createFusionTask(request, null);
        FusionResultResponse result = fusionService.executeFusionTask(task.getTaskId());
        return Result.success("融合完成", result);
    }

    @DeleteMapping("/tasks/{taskId}")
    public Result<Void> deleteFusionTask(@PathVariable Long taskId) {
        fusionService.deleteFusionTask(taskId);
        return Result.success("删除成功", null);
    }

    @GetMapping("/tasks/{taskId}/geojson")
    public ResponseEntity<String> getFusionResultGeoJson(@PathVariable Long taskId) {
        String geoJson = fusionService.getFusionResultGeoJson(taskId);
        
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                .header(HttpHeaders.CONTENT_DISPOSITION, 
                        "attachment; filename=\"fusion_result_" + taskId + ".geojson\"")
                .body(geoJson);
    }

    @PostMapping("/tasks/{taskId}/download")
    public ResponseEntity<byte[]> downloadFusionResult(@PathVariable Long taskId) {
        String geoJson = fusionService.getFusionResultGeoJson(taskId);
        byte[] content = geoJson.getBytes();
        
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                .header(HttpHeaders.CONTENT_DISPOSITION, 
                        "attachment; filename=\"fusion_result_" + taskId + ".geojson\"")
                .body(content);
    }
}
