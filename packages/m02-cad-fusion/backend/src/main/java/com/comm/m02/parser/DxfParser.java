package com.comm.m02.parser;

import com.comm.m02.common.BusinessException;
import com.comm.m02.utils.FileUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.io.*;
import java.math.BigDecimal;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Component
public class DxfParser {

    private static final Logger log = LoggerFactory.getLogger(DxfParser.class);

    private static final Set<String> SUPPORTED_ENTITY_TYPES = Set.of(
            "LINE", "LWPOLYLINE", "POLYLINE", "CIRCLE", "ARC",
            "TEXT", "MTEXT", "POINT", "BLOCK", "INSERT", "CIRCLE"
    );

    private static final Map<Integer, String> CODE_MEANINGS = new HashMap<>();
    static {
        CODE_MEANINGS.put(0, "entity_type");
        CODE_MEANINGS.put(2, "block_name");
        CODE_MEANINGS.put(8, "layer_name");
        CODE_MEANINGS.put(10, "x");
        CODE_MEANINGS.put(11, "x2");
        CODE_MEANINGS.put(12, "x3");
        CODE_MEANINGS.put(20, "y");
        CODE_MEANINGS.put(21, "y2");
        CODE_MEANINGS.put(22, "y3");
        CODE_MEANINGS.put(30, "z");
        CODE_MEANINGS.put(31, "z2");
        CODE_MEANINGS.put(32, "z3");
        CODE_MEANINGS.put(40, "radius");
        CODE_MEANINGS.put(50, "start_angle");
        CODE_MEANINGS.put(51, "end_angle");
        CODE_MEANINGS.put(100, "subclass");
    }

    public ParseResult parse(String filePath) {
        log.info("开始解析DXF文件: {}", filePath);
        ParseResult result = new ParseResult();

        try {
            String content = readDxfFile(filePath);
            List<String> lines = Arrays.asList(content.split("\\r?\\n"));
            
            int entitiesSectionStart = findSection(lines, "ENTITIES");
            if (entitiesSectionStart == -1) {
                log.warn("DXF文件中未找到ENTITIES段");
                result.setSuccess(true);
                result.setMessage("未找到实体段");
                return result;
            }

            parseEntities(lines, entitiesSectionStart, result);
            result.setSuccess(true);
            result.setMessage("解析成功");
            log.info("DXF文件解析完成，共解析 {} 个实体", result.getEntities().size());

        } catch (Exception e) {
            log.error("DXF文件解析失败", e);
            result.setSuccess(false);
            result.setMessage("解析失败: " + e.getMessage());
        }

        return result;
    }

    private String readDxfFile(String filePath) throws IOException {
        byte[] bytes = java.nio.file.Files.readAllBytes(java.nio.file.Paths.get(filePath));
        
        Charset charset = StandardCharsets.UTF_8;
        if (bytes.length > 1 && bytes[0] == (byte) 0xFF && bytes[1] == (byte) 0xFE) {
            charset = StandardCharsets.UTF_16;
        }

        return new String(bytes, charset);
    }

    private int findSection(List<String> lines, String sectionName) {
        for (int i = 0; i < lines.size(); i++) {
            String line = lines.get(i).trim();
            if (line.equals("SECTION")) {
                if (i + 1 < lines.size() && lines.get(i + 1).trim().equals(sectionName)) {
                    return i + 2;
                }
            }
        }
        return -1;
    }

    private void parseEntities(List<String> lines, int startIndex, ParseResult result) {
        List<CadEntity> currentEntity = null;
        String currentType = null;
        Map<String, String> currentAttributes = new HashMap<>();
        List<int[]> currentCodePairs = new ArrayList<>();

        for (int i = startIndex; i < lines.size(); i++) {
            String line = lines.get(i).trim();
            if (line.equals("ENDSEC") || line.equals("EOF")) {
                if (currentEntity != null && !currentEntity.isEmpty()) {
                    result.getEntities().add(buildEntity(currentType, currentAttributes));
                }
                break;
            }

            if (line.equals("SECTION")) {
                break;
            }

            String codeLine = line;
            String valueLine = i + 1 < lines.size() ? lines.get(i + 1).trim() : "";

            int code;
            try {
                code = Integer.parseInt(codeLine);
            } catch (NumberFormatException e) {
                continue;
            }

            if (code == 0) {
                if (currentEntity != null && !currentAttributes.isEmpty()) {
                    result.getEntities().add(buildEntity(currentType, currentAttributes));
                }
                currentType = valueLine;
                currentAttributes = new HashMap<>();
                i++;
                continue;
            }

            currentAttributes.put(String.valueOf(code), valueLine);
            i++;
        }

        if (currentEntity != null && !currentAttributes.isEmpty()) {
            result.getEntities().add(buildEntity(currentType, currentAttributes));
        }
    }

    private CadEntity buildEntity(String type, Map<String, String> attributes) {
        CadEntity entity = new CadEntity();
        entity.setEntityType(type);

        String layerName = attributes.get("8");
        entity.setLayerName(layerName != null ? layerName : "DEFAULT");

        String blockName = attributes.get("2");
        entity.setBlockName(blockName);

        extractGeometry(entity, type, attributes);
        extractAttributes(entity, attributes);

        return entity;
    }

    private void extractGeometry(CadEntity entity, String type, Map<String, String> attributes) {
        try {
            switch (type.toUpperCase()) {
                case "LINE":
                case "LWPOLYLINE":
                case "POLYLINE":
                    extractLineGeometry(entity, attributes);
                    break;
                case "CIRCLE":
                    extractCircleGeometry(entity, attributes);
                    break;
                case "ARC":
                    extractArcGeometry(entity, attributes);
                    break;
                case "POINT":
                    extractPointGeometry(entity, attributes);
                    break;
                case "TEXT":
                case "MTEXT":
                    extractTextGeometry(entity, attributes);
                    break;
                default:
                    extractGenericGeometry(entity, attributes);
                    break;
            }
        } catch (Exception e) {
            log.warn("提取几何信息失败: type={}, error={}", type, e.getMessage());
        }
    }

    private void extractLineGeometry(CadEntity entity, Map<String, String> attributes) {
        try {
            double x1 = parseDouble(attributes.get("10"));
            double y1 = parseDouble(attributes.get("20"));
            double z1 = parseDouble(attributes.get("30"));
            
            double x2 = parseDouble(attributes.get("11"));
            double y2 = parseDouble(attributes.get("21"));
            double z2 = parseDouble(attributes.get("31"));

            entity.addVertex(x1, y1, z1);
            entity.addVertex(x2, y2, z2);
        } catch (Exception e) {
            log.warn("解析线实体几何失败");
        }
    }

    private void extractCircleGeometry(CadEntity entity, Map<String, String> attributes) {
        try {
            double cx = parseDouble(attributes.get("10"));
            double cy = parseDouble(attributes.get("20"));
            double cz = parseDouble(attributes.get("30"));
            double r = parseDouble(attributes.get("40"));

            entity.addVertex(cx - r, cy, cz);
            entity.addVertex(cx + r, cy, cz);
            entity.addVertex(cx, cy - r, cz);
            entity.addVertex(cx, cy + r, cz);
        } catch (Exception e) {
            log.warn("解析圆实体几何失败");
        }
    }

    private void extractArcGeometry(CadEntity entity, Map<String, String> attributes) {
        try {
            double cx = parseDouble(attributes.get("10"));
            double cy = parseDouble(attributes.get("20"));
            double cz = parseDouble(attributes.get("30"));
            double r = parseDouble(attributes.get("40"));

            entity.addVertex(cx - r, cy, cz);
            entity.addVertex(cx + r, cy, cz);
        } catch (Exception e) {
            log.warn("解析弧实体几何失败");
        }
    }

    private void extractPointGeometry(CadEntity entity, Map<String, String> attributes) {
        try {
            double x = parseDouble(attributes.get("10"));
            double y = parseDouble(attributes.get("20"));
            double z = parseDouble(attributes.get("30"));

            entity.addVertex(x, y, z);
        } catch (Exception e) {
            log.warn("解析点实体几何失败");
        }
    }

    private void extractTextGeometry(CadEntity entity, Map<String, String> attributes) {
        try {
            double x = parseDouble(attributes.get("10"));
            double y = parseDouble(attributes.get("20"));
            double z = parseDouble(attributes.get("30"));

            entity.addVertex(x, y, z);
        } catch (Exception e) {
            log.warn("解析文本实体几何失败");
        }
    }

    private void extractGenericGeometry(CadEntity entity, Map<String, String> attributes) {
        try {
            double x = parseDouble(attributes.get("10"));
            double y = parseDouble(attributes.get("20"));
            double z = parseDouble(attributes.get("30"));

            if (x != 0 || y != 0) {
                entity.addVertex(x, y, z);
            }
        } catch (Exception e) {
            // ignore
        }
    }

    private void extractAttributes(CadEntity entity, Map<String, String> attributes) {
        for (Map.Entry<String, String> entry : attributes.entrySet()) {
            String key = CODE_MEANINGS.getOrDefault(Integer.parseInt(entry.getKey()), entry.getKey());
            entity.getAttributes().put(key, entry.getValue());
        }
    }

    private double parseDouble(String value) {
        if (value == null || value.isEmpty()) return 0;
        try {
            return Double.parseDouble(value);
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    @Data
    public static class ParseResult {
        private boolean success;
        private String message;
        private List<CadEntity> entities = new ArrayList<>();
        private Map<String, Integer> layerStats = new HashMap<>();
        private Map<String, Integer> typeStats = new HashMap<>();

        public void addEntity(CadEntity entity) {
            entities.add(entity);
            String layer = entity.getLayerName() != null ? entity.getLayerName() : "DEFAULT";
            layerStats.merge(layer, 1, Integer::sum);
            String type = entity.getEntityType();
            typeStats.merge(type, 1, Integer::sum);
        }
    }
}
