package com.comm.s2.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.comm.s2.entity.CadFile;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

public interface CadFileService extends IService<CadFile> {

    CadFile uploadFile(MultipartFile file, Long projectId, Long userId, String sourceEpsg, String targetEpsg);

    CadFile getFileById(Long id);

    List<CadFile> getFilesByProjectId(Long projectId);

    List<CadFile> getFilesByUserId(Long userId);

    boolean deleteFile(Long id);

    com.comm.s2.parser.DxfParser.ParseResult parseFile(Long id);
}
