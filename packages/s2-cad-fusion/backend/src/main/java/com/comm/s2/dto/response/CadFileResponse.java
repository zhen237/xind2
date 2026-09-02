package com.comm.s2.dto.response;

import com.comm.s2.entity.CadFile;
import lombok.Data;

@Data
public class CadFileResponse {
    private Long id;
    private String fileName;
    private String originalName;
    private String fileType;
    private Long fileSize;
    private String fileSizeReadable;
    private String parseStatus;
    private Integer entityCount;
    private String uploadTime;

    public static CadFileResponse fromEntity(CadFile entity) {
        CadFileResponse response = new CadFileResponse();
        response.setId(entity.getId());
        response.setFileName(entity.getFileName());
        response.setOriginalName(entity.getOriginalName());
        response.setFileType(entity.getFileType());
        response.setFileSize(entity.getFileSize());
        response.setFileSizeReadable(com.comm.s2.utils.FileUtils.getFileSizeReadable(entity.getFileSize()));
        Integer ps = entity.getParseStatus();
        response.setParseStatus(ps != null && ps == 1 ? "已解析" : ps != null && ps == 2 ? "解析失败" : "待解析");
        response.setUploadTime(entity.getCreateTime() != null ? entity.getCreateTime().toString() : null);
        return response;
    }
}
