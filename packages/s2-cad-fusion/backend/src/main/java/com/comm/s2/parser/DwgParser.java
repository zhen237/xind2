package com.comm.s2.parser;

import com.comm.s2.common.BusinessException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.io.*;
import java.nio.file.*;
import java.util.*;

@Component
public class DwgParser {

    private static final Logger log = LoggerFactory.getLogger(DwgParser.class);

    public DxfParser.ParseResult parse(String filePath) {
        log.info("开始解析DWG文件: {}", filePath);
        
        DxfParser.ParseResult result = new DxfParser.ParseResult();
        
        try {
            String dxfContent = convertDwgToDxf(filePath);
            if (dxfContent != null) {
                parseDxfContent(dxfContent, result);
                result.setSuccess(true);
                result.setMessage("DWG解析成功");
                log.info("DWG文件解析完成，共解析 {} 个实体", result.getEntities().size());
            } else {
                fallbackParse(filePath, result);
            }
        } catch (Exception e) {
            log.error("DWG文件解析失败", e);
            result.setSuccess(false);
            result.setMessage("解析失败: " + e.getMessage());
        }

        return result;
    }

    private String convertDwgToDxf(String dwgFilePath) {
        log.debug("尝试将DWG转换为DXF...");
        String outputDxfPath = dwgFilePath.replace(".dwg", ".dxf");
        
        try {
            ProcessBuilder pb = new ProcessBuilder("ODAFileConverter", 
                    dwgFilePath, outputDxfPath, "0", "DXF 2018");
            pb.redirectErrorStream(true);
            Process process = pb.start();
            int exitCode = process.waitFor();
            
            if (exitCode == 0 && new File(outputDxfPath).exists()) {
                log.info("DWG转DXF成功");
                return new String(Files.readAllBytes(Paths.get(outputDxfPath)));
            }
        } catch (Exception e) {
            log.debug("ODAFileConverter不可用: {}", e.getMessage());
        }

        try {
            ProcessBuilder pb = new ProcessBuilder("LibreCAD", 
                    "-I", dwgFilePath, "-o", outputDxfPath);
            pb.redirectErrorStream(true);
            Process process = pb.start();
            int exitCode = process.waitFor();
            
            if (exitCode == 0 && new File(outputDxfPath).exists()) {
                log.info("DWG转DXF成功(LibreCAD)");
                return new String(Files.readAllBytes(Paths.get(outputDxfPath)));
            }
        } catch (Exception e) {
            log.debug("LibreCAD不可用: {}", e.getMessage());
        }

        return null;
    }

    private void parseDxfContent(String dxfContent, DxfParser.ParseResult result) {
        try {
            Path tempFile = Files.createTempFile("cad_parse_", ".dxf");
            Files.write(tempFile, dxfContent.getBytes());
            
            DxfParser dxfParser = new DxfParser();
            DxfParser.ParseResult parseResult = dxfParser.parse(tempFile.toString());
            
            result.setEntities(parseResult.getEntities());
            result.setLayerStats(parseResult.getLayerStats());
            result.setTypeStats(parseResult.getTypeStats());
            
            Files.deleteIfExists(tempFile);
        } catch (IOException e) {
            log.error("解析DXF内容失败", e);
        }
    }

    private void fallbackParse(String filePath, DxfParser.ParseResult result) {
        log.info("使用回退方式解析DWG文件...");
        
        try {
            byte[] content = Files.readAllBytes(Paths.get(filePath));
            String textContent = new String(content, "UTF-8");
            
            List<CadEntity> entities = extractEntitiesFromText(textContent);
            result.setEntities(entities);
            result.setSuccess(true);
            result.setMessage("回退解析完成，共提取 " + entities.size() + " 个实体");
        } catch (Exception e) {
            log.warn("回退解析也失败", e);
            result.setSuccess(false);
            result.setMessage("DWG文件解析失败，请转换为DXF格式后重试");
        }
    }

    private List<CadEntity> extractEntitiesFromText(String content) {
        List<CadEntity> entities = new ArrayList<>();
        String[] lines = content.split("\\r?\\n");
        
        for (String line : lines) {
            line = line.trim();
            if (line.isEmpty()) continue;
            
            CadEntity entity = tryExtractEntity(line);
            if (entity != null) {
                entities.add(entity);
            }
        }
        
        return entities;
    }

    private CadEntity tryExtractEntity(String line) {
        try {
            if (line.contains("AcDbLine") || line.contains("LINE")) {
                CadEntity entity = new CadEntity();
                entity.setEntityType("LINE");
                entity.setLayerName("DEFAULT");
                
                String[] parts = line.split("[,\\s]+");
                if (parts.length >= 6) {
                    double x1 = Double.parseDouble(parts[1]);
                    double y1 = Double.parseDouble(parts[2]);
                    double x2 = Double.parseDouble(parts[3]);
                    double y2 = Double.parseDouble(parts[4]);
                    entity.addVertex(x1, y1, 0);
                    entity.addVertex(x2, y2, 0);
                }
                return entity;
            }
            
            if (line.contains("AcDbCircle") || line.contains("CIRCLE")) {
                CadEntity entity = new CadEntity();
                entity.setEntityType("CIRCLE");
                entity.setLayerName("DEFAULT");
                return entity;
            }
        } catch (Exception e) {
            // skip
        }
        return null;
    }
}
