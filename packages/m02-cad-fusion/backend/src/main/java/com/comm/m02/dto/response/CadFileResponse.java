package com.comm.m02.dto.response;

import com.comm.m02.entity.CadFile;
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
        response.setFileSizeReadable(com.comm.m02.utils.FileUtils.getFileSizeReadable(entity.getFileSize()));
        response.setParseStatus(entity.getParseStatus() == 1 ? "已解析" : "待解析");
        response.setUploadTime(entity.getCreateTime() != null ? entity.getCreateTime().toString() : null);
        return response;
    }
}
