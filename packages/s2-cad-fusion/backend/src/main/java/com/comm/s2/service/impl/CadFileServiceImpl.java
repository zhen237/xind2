package com.comm.s2.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.comm.s2.common.BusinessException;
import com.comm.s2.config.FileStorageConfig;
import com.comm.s2.entity.CadFile;
import com.comm.s2.mapper.CadFileMapper;
import com.comm.s2.parser.DxfParser;
import com.comm.s2.service.CadFileService;
import com.comm.s2.utils.FileUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.time.LocalDateTime;
import java.util.List;

@Service
public class CadFileServiceImpl extends ServiceImpl<CadFileMapper, CadFile> implements CadFileService {

    private static final Logger log = LoggerFactory.getLogger(CadFileServiceImpl.class);

    @Autowired
    private FileStorageConfig fileStorageConfig;

    @Autowired
    private DxfParser dxfParser;

    @Override
    public CadFile uploadFile(MultipartFile file, Long projectId, Long userId, 
                              String sourceEpsg, String targetEpsg) {
        if (file == null || file.isEmpty()) {
            throw new BusinessException(400, "上传文件不能为空");
        }

        String originalName = file.getOriginalFilename();
        if (originalName == null || !FileUtils.isValidCadFile(originalName)) {
            throw new BusinessException(400, "只支持 DWG/DXF 格式的CAD文件");
        }

        try {
            String filePath = FileUtils.saveUploadedFile(file, fileStorageConfig.getCadDir());
            String fileType = FileUtils.getFileExtension(originalName);
            Long fileSize = file.getSize();

            CadFile cadFile = new CadFile();
            cadFile.setFileName(FileUtils.generateFileName(originalName));
            cadFile.setOriginalName(originalName);
            cadFile.setFilePath(filePath);
            cadFile.setFileType(fileType);
            cadFile.setFileSize(fileSize);
            cadFile.setProjectId(projectId);
            cadFile.setUploadedBy(userId);
            cadFile.setSourceEpsg(sourceEpsg != null ? sourceEpsg : "EPSG:4326");
            cadFile.setTargetEpsg(targetEpsg != null ? targetEpsg : "EPSG:4326");
            cadFile.setParseStatus(0);
            cadFile.setCreateTime(LocalDateTime.now());
            cadFile.setUpdateTime(LocalDateTime.now());

            this.save(cadFile);
            
            log.info("CAD文件上传成功: id={}, name={}, size={}", 
                    cadFile.getId(), originalName, FileUtils.getFileSizeReadable(fileSize));
            
            return cadFile;

        } catch (IOException e) {
            log.error("文件保存失败", e);
            throw new BusinessException(500, "文件保存失败: " + e.getMessage());
        }
    }

    @Override
    public CadFile getFileById(Long id) {
        CadFile file = this.getById(id);
        if (file == null) {
            throw new BusinessException(404, "文件不存在");
        }
        return file;
    }

    @Override
    public List<CadFile> getFilesByProjectId(Long projectId) {
        return baseMapper.findByProjectId(projectId);
    }

    @Override
    public List<CadFile> getFilesByUserId(Long userId) {
        return baseMapper.findByUserId(userId);
    }

    @Override
    public boolean deleteFile(Long id) {
        CadFile file = getFileById(id);
        
        try {
            if (file.getFilePath() != null) {
                FileUtils.deleteFile(file.getFilePath());
            }
        } catch (IOException e) {
            log.warn("删除物理文件失败: {}", file.getFilePath());
        }

        this.removeById(id);
        log.info("CAD文件删除成功: id={}", id);
        return true;
    }

    @Override
    public DxfParser.ParseResult parseFile(Long id) {
        CadFile file = getFileById(id);
        
        if (!"dxf".equalsIgnoreCase(file.getFileType())) {
            throw new BusinessException(400, "仅支持DXF文件直接解析，DWG文件需要先转换");
        }

        try {
            DxfParser.ParseResult result = dxfParser.parse(file.getFilePath());
            
            file.setParseStatus(result.isSuccess() ? 1 : 2);
            file.setParseResult(result.isSuccess() ? "解析成功，共" + result.getEntities().size() + "个实体" : result.getMessage());
            file.setUpdateTime(LocalDateTime.now());
            this.updateById(file);

            return result;

        } catch (Exception e) {
            log.error("文件解析失败", e);
            file.setParseStatus(2);
            file.setParseResult("解析失败: " + e.getMessage());
            file.setUpdateTime(LocalDateTime.now());
            this.updateById(file);
            throw new BusinessException(500, "文件解析失败: " + e.getMessage());
        }
    }
}
