package com.comm.s2.controller;

import com.comm.s2.common.Result;
import com.comm.s2.dto.response.CadFileResponse;
import com.comm.s2.entity.CadFile;
import com.comm.s2.parser.DxfParser;
import com.comm.s2.service.CadFileService;
import com.comm.s2.utils.FileUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.math.BigDecimal;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/s2/cad/cad-files")
public class CadFileController {

    @Autowired
    private CadFileService cadFileService;

    @PostMapping("/upload")
    public Result<CadFileResponse> uploadFile(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "projectId", required = false) Long projectId,
            @RequestParam(value = "userId", required = false) Long userId,
            @RequestParam(value = "sourceEpsg", required = false) String sourceEpsg,
            @RequestParam(value = "targetEpsg", required = false) String targetEpsg) {
        
        CadFile cadFile = cadFileService.uploadFile(file, projectId, userId, sourceEpsg, targetEpsg);
        return Result.success("上传成功", CadFileResponse.fromEntity(cadFile));
    }

    @GetMapping("/{id}")
    public Result<CadFileResponse> getFile(@PathVariable Long id) {
        CadFile file = cadFileService.getFileById(id);
        return Result.success(CadFileResponse.fromEntity(file));
    }

    @GetMapping
    public Result<List<CadFileResponse>> getFiles(
            @RequestParam(value = "projectId", required = false) Long projectId,
            @RequestParam(value = "userId", required = false) Long userId) {
        
        List<CadFile> files;
        if (projectId != null) {
            files = cadFileService.getFilesByProjectId(projectId);
        } else if (userId != null) {
            files = cadFileService.getFilesByUserId(userId);
        } else {
            files = cadFileService.list();
        }
        
        List<CadFileResponse> responses = files.stream()
                .map(CadFileResponse::fromEntity)
                .collect(Collectors.toList());
        return Result.success(responses);
    }

    @DeleteMapping("/{id}")
    public Result<Void> deleteFile(@PathVariable Long id) {
        cadFileService.deleteFile(id);
        return Result.success("删除成功", null);
    }

    @PostMapping("/{id}/parse")
    public Result<Map<String, Object>> parseFile(@PathVariable Long id) {
        DxfParser.ParseResult result = cadFileService.parseFile(id);
        
        Map<String, Object> response = new HashMap<>();
        response.put("success", result.isSuccess());
        response.put("message", result.getMessage());
        response.put("entityCount", result.getEntities().size());
        response.put("layerStats", result.getLayerStats());
        response.put("typeStats", result.getTypeStats());
        
        return Result.success("解析完成", response);
    }

    @GetMapping("/{id}/content")
    public ResponseEntity<byte[]> getFileContent(@PathVariable Long id) throws IOException {
        CadFile file = cadFileService.getFileById(id);
        byte[] content = FileUtils.readFileAsBytes(file.getFilePath());
        
        String contentType = getContentType(file.getFileType());
        
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_TYPE, contentType)
                .header(HttpHeaders.CONTENT_DISPOSITION, 
                        "attachment; filename=\"" + file.getOriginalName() + "\"")
                .body(content);
    }

    private String getContentType(String fileType) {
        if (fileType == null) return MediaType.APPLICATION_OCTET_STREAM_VALUE;
        
        switch (fileType.toLowerCase()) {
            case "dxf":
                return "application/dxf";
            case "dwg":
                return "application/dwg";
            default:
                return MediaType.APPLICATION_OCTET_STREAM_VALUE;
        }
    }
}
