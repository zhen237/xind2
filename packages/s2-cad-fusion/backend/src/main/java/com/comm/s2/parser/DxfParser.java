package com.comm.s2.parser;

import lombok.Data;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.*;

/**
 * DXF（ASCII）格式解析器。
 * <p>
 * DXF文件由若干SECTION组成，每个SECTION内是"组码-组值"成对的文本行。
 * 解析器定位ENTITIES段后按组码对逐个实体提取几何信息：
 * <ul>
 *   <li>LINE：组码10/20/30（起点）、11/21/31（终点）</li>
 *   <li>LWPOLYLINE：组码90（顶点数）、70（闭合标志），重复出现的10/20组码依次为各顶点坐标</li>
 *   <li>POLYLINE/VERTEX/SEQEND：POLYLINE头后跟若干VERTEX子实体，直到SEQEND结束</li>
 *   <li>CIRCLE：圆心10/20 + 半径40，按64段离散化为闭合圆环</li>
 *   <li>ARC：圆心 + 半径 + 起止角50/51，按弧段离散化为折线</li>
 *   <li>TEXT/MTEXT：插入点10/20 + 组码1文本内容</li>
 * </ul>
 */
@Component
public class DxfParser {

    private static final Logger log = LoggerFactory.getLogger(DxfParser.class);

    /** 圆离散化段数 */
    private static final int CIRCLE_SEGMENTS = 64;
    /** 弧离散化段数 */
    private static final int ARC_SEGMENTS = 36;

    /** 需要提取几何的实体类型 */
    private static final Set<String> GEOMETRY_ENTITY_TYPES = Set.of(
            "LINE", "LWPOLYLINE", "POLYLINE", "VERTEX", "CIRCLE", "ARC",
            "TEXT", "MTEXT", "POINT"
    );

    /** POLYLINE组码70的闭合标志位 */
    private static final int POLYLINE_CLOSED_FLAG = 1;

    public ParseResult parse(String filePath) {
        log.info("开始解析DXF文件: {}", filePath);
        ParseResult result = new ParseResult();

        try {
            String content = readDxfFile(filePath);
            List<String> lines = Arrays.asList(content.split("\\r?\\n"));

            int entitiesSectionStart = findEntitiesSection(lines);
            if (entitiesSectionStart == -1) {
                log.warn("DXF文件中未找到ENTITIES段");
                result.setSuccess(true);
                result.setMessage("未找到ENTITIES段，未解析到实体");
                return result;
            }

            parseEntities(lines, entitiesSectionStart, result);
            result.setSuccess(true);
            result.setMessage("解析成功，共解析 " + result.getEntities().size() + " 个实体");
            log.info("DXF文件解析完成，共解析 {} 个实体", result.getEntities().size());

        } catch (Exception e) {
            log.error("DXF文件解析失败", e);
            result.setSuccess(false);
            result.setMessage("解析失败: " + e.getMessage());
        }

        return result;
    }

    /**
     * 读取DXF文件内容。DXF通常为ASCII/UTF-8，少数由AutoCAD R12导出的文件为UTF-16，
     * 通过BOM简单判断字符集。
     */
    private String readDxfFile(String filePath) throws IOException {
        byte[] bytes = Files.readAllBytes(Paths.get(filePath));

        Charset charset = StandardCharsets.UTF_8;
        if (bytes.length > 1 && bytes[0] == (byte) 0xFF && bytes[1] == (byte) 0xFE) {
            charset = StandardCharsets.UTF_16LE;
        } else if (bytes.length > 1 && bytes[0] == (byte) 0xFE && bytes[1] == (byte) 0xFF) {
            charset = StandardCharsets.UTF_16BE;
        }

        return new String(bytes, charset);
    }

    /**
     * 定位ENTITIES段在行列表中的起始下标。
     * DXF段头由两组码对构成："0 SECTION" + "2 ENTITIES"，
     * 因此匹配组码2的值ENTITIES，实体内容从其后开始。
     */
    private int findEntitiesSection(List<String> lines) {
        for (int i = 0; i < lines.size() - 1; i++) {
            if ("2".equals(lines.get(i).trim())
                    && "ENTITIES".equals(lines.get(i + 1).trim())) {
                return i + 2;
            }
        }
        return -1;
    }

    /**
     * 遍历ENTITIES段内的组码对。DXF中每两行构成一组：第一行为组码（整数），
     * 第二行为组值。实体以组码0分隔。
     */
    private void parseEntities(List<String> lines, int startIndex, ParseResult result) {
        // 当前实体的有序组码对（组码, 组值），保留重复组码（如LWPOLYLINE的多个10/20）
        List<String[]> pairs = new ArrayList<>();
        String currentType = null;
        // POLYLINE状态：后续VERTEX实体的顶点累计到当前POLYLINE
        CadEntity pendingPolyline = null;

        for (int i = startIndex; i < lines.size() - 1; i += 2) {
            String codeLine = lines.get(i).trim();
            String valueLine = lines.get(i + 1).trim();

            int code;
            try {
                code = Integer.parseInt(codeLine);
            } catch (NumberFormatException e) {
                // 非组码行（如ENDSEC/EOF后的杂散内容），跳过单行重新对齐
                i -= 1;
                continue;
            }

            if (code == 0) {
                String entityType = valueLine;

                // 先提交上一个实体（VERTEX需先累计到挂起的POLYLINE上，再结束POLYLINE序列，
                // 否则最后一个VERTEX会在POLYLINE提交后丢失）
                if (currentType != null && !pairs.isEmpty()) {
                    if ("VERTEX".equals(currentType)) {
                        // VERTEX是POLYLINE的子实体，把顶点累计到挂起的POLYLINE
                        if (pendingPolyline != null) {
                            CadEntity vertex = buildEntity("VERTEX", pairs);
                            if (vertex != null) {
                                for (CadEntity.CadVertex v : vertex.getVertices()) {
                                    pendingPolyline.addVertex(v.getX().doubleValue(),
                                            v.getY().doubleValue(), v.getZ().doubleValue());
                                }
                            }
                        }
                    } else if (!"SEQEND".equals(currentType)) {
                        CadEntity entity = buildEntity(currentType, pairs);
                        if (entity != null) {
                            if ("POLYLINE".equals(currentType)) {
                                // POLYLINE本身先挂起，等待后续VERTEX
                                pendingPolyline = entity;
                            } else {
                                result.addEntity(entity);
                            }
                        }
                    }
                }

                // 新实体不是VERTEX时，结束POLYLINE的VERTEX序列
                if (pendingPolyline != null && !"VERTEX".equals(entityType)) {
                    closeRingIfNeed(pendingPolyline);
                    if (pendingPolyline.getVertices().size() >= 2) {
                        result.addEntity(pendingPolyline);
                    }
                    pendingPolyline = null;
                }

                currentType = entityType;
                pairs = new ArrayList<>();

                // ENTITIES段结束，后续BLOCKS/OBJECTS等段不再解析，避免块定义重复入库
                if ("ENDSEC".equals(entityType)) {
                    break;
                }
                continue;
            }

            if (currentType == null) {
                continue;
            }

            // 组码0以外的组码对全部记录，交给buildEntity按类型解读
            pairs.add(new String[]{String.valueOf(code), valueLine});
        }

        // 文件结束，收尾
        if (currentType != null && !pairs.isEmpty()) {
            if ("VERTEX".equals(currentType)) {
                if (pendingPolyline != null) {
                    CadEntity vertex = buildEntity("VERTEX", pairs);
                    if (vertex != null) {
                        for (CadEntity.CadVertex v : vertex.getVertices()) {
                            pendingPolyline.addVertex(v.getX().doubleValue(),
                                    v.getY().doubleValue(), v.getZ().doubleValue());
                        }
                    }
                }
            } else if (!"SEQEND".equals(currentType)) {
                CadEntity entity = buildEntity(currentType, pairs);
                if (entity != null) {
                    result.addEntity(entity);
                }
            }
        }
        if (pendingPolyline != null && pendingPolyline.getVertices().size() >= 2) {
            closeRingIfNeed(pendingPolyline);
            result.addEntity(pendingPolyline);
        }
    }

    /** 闭合多段线首尾相接，便于GIS侧生成面要素 */
    private void closeRingIfNeed(CadEntity entity) {
        if (!entity.isClosed() || entity.getVertices().size() < 3) {
            return;
        }
        CadEntity.CadVertex first = entity.getVertices().get(0);
        CadEntity.CadVertex last = entity.getVertices().get(entity.getVertices().size() - 1);
        if (first.getX().compareTo(last.getX()) != 0 || first.getY().compareTo(last.getY()) != 0) {
            entity.addVertex(first.getX().doubleValue(), first.getY().doubleValue(),
                    first.getZ().doubleValue());
        }
    }

    /** 将组码对列表转换为CadEntity */
    private CadEntity buildEntity(String type, List<String[]> pairs) {
        String upperType = type.toUpperCase(Locale.ROOT);
        if (!GEOMETRY_ENTITY_TYPES.contains(upperType)) {
            return null;
        }

        // 层名：组码8
        String layerName = firstValue(pairs, "8");

        CadEntity entity = new CadEntity();
        entity.setEntityType(upperType);
        entity.setLayerName(layerName != null ? layerName : "DEFAULT");

        switch (upperType) {
            case "LINE":
                buildLine(entity, pairs);
                break;
            case "LWPOLYLINE":
                buildLwPolyline(entity, pairs);
                break;
            case "POLYLINE":
                buildPolylineHeader(entity, pairs);
                break;
            case "VERTEX":
                buildVertex(entity, pairs);
                break;
            case "CIRCLE":
                buildCircle(entity, pairs);
                break;
            case "ARC":
                buildArc(entity, pairs);
                break;
            case "POINT":
                buildPoint(entity, pairs);
                break;
            case "TEXT":
            case "MTEXT":
                buildText(entity, pairs);
                break;
            default:
                buildGeneric(entity, pairs);
                break;
        }

        return entity;
    }

    /** LINE：起点10/20/30，终点11/21/31 */
    private void buildLine(CadEntity entity, List<String[]> pairs) {
        double x1 = doubleValue(firstValue(pairs, "10"));
        double y1 = doubleValue(firstValue(pairs, "20"));
        double z1 = doubleValue(firstValue(pairs, "30"));
        double x2 = doubleValue(firstValue(pairs, "11"));
        double y2 = doubleValue(firstValue(pairs, "21"));
        double z2 = doubleValue(firstValue(pairs, "31"));

        entity.addVertex(x1, y1, z1);
        entity.addVertex(x2, y2, z2);
    }

    /**
     * LWPOLYLINE：轻量多段线。顶点坐标由重复出现的组码10/20对组成：
     * 出现一个新的组码10表示新顶点开始，其后的20/30属于该顶点。
     * 组码70的bit0为闭合标志。
     */
    private void buildLwPolyline(CadEntity entity, List<String[]> pairs) {
        int flags = intValue(firstValue(pairs, "70"));
        entity.setClosed((flags & POLYLINE_CLOSED_FLAG) != 0);

        Double x = null;
        for (String[] pair : pairs) {
            switch (pair[0]) {
                case "10":
                    // 新的组码10：提交上一个未完结顶点，开始新顶点
                    if (x != null) {
                        entity.addVertex(x, 0, 0);
                    }
                    x = doubleValue(pair[1]);
                    break;
                case "20":
                    if (x != null) {
                        entity.addVertex(x, doubleValue(pair[1]), 0);
                        x = null;
                    }
                    break;
                default:
                    // 其他组码（42凸度、70标志等）忽略，按直角折线近似
                    break;
            }
        }
        // 兜底：只有组码10没有20的异常数据
        if (x != null) {
            entity.addVertex(x, 0, 0);
        }

        // 闭合多段线首尾相接，便于GIS侧生成面
        if (entity.isClosed() && entity.getVertices().size() >= 3) {
            CadEntity.CadVertex first = entity.getVertices().get(0);
            CadEntity.CadVertex last = entity.getVertices().get(entity.getVertices().size() - 1);
            if (first.getX().compareTo(last.getX()) != 0 || first.getY().compareTo(last.getY()) != 0) {
                entity.addVertex(first.getX().doubleValue(), first.getY().doubleValue(),
                        first.getZ().doubleValue());
            }
        }
    }

    /** POLYLINE：老式多段线，本实体仅含标志头，顶点由后续VERTEX实体提供 */
    private void buildPolylineHeader(CadEntity entity, List<String[]> pairs) {
        int flags = intValue(firstValue(pairs, "70"));
        entity.setClosed((flags & POLYLINE_CLOSED_FLAG) != 0);
    }

    /** VERTEX：POLYLINE的一个顶点 */
    private void buildVertex(CadEntity entity, List<String[]> pairs) {
        entity.addVertex(
                doubleValue(firstValue(pairs, "10")),
                doubleValue(firstValue(pairs, "20")),
                doubleValue(firstValue(pairs, "30")));
    }

    /** CIRCLE：圆心10/20 + 半径40，离散化为闭合圆环 */
    private void buildCircle(CadEntity entity, List<String[]> pairs) {
        double cx = doubleValue(firstValue(pairs, "10"));
        double cy = doubleValue(firstValue(pairs, "20"));
        double cz = doubleValue(firstValue(pairs, "30"));
        double r = doubleValue(firstValue(pairs, "40"));

        if (r <= 0) {
            log.warn("圆实体半径非法，按点处理: layer={}", entity.getLayerName());
            entity.addVertex(cx, cy, cz);
            return;
        }

        entity.setClosed(true);
        for (int i = 0; i <= CIRCLE_SEGMENTS; i++) {
            double angle = 2 * Math.PI * i / CIRCLE_SEGMENTS;
            entity.addVertex(cx + r * Math.cos(angle), cy + r * Math.sin(angle), cz);
        }
    }

    /** ARC：圆心 + 半径 + 起止角50/51（度，逆时针），离散化为折线 */
    private void buildArc(CadEntity entity, List<String[]> pairs) {
        double cx = doubleValue(firstValue(pairs, "10"));
        double cy = doubleValue(firstValue(pairs, "20"));
        double cz = doubleValue(firstValue(pairs, "30"));
        double r = doubleValue(firstValue(pairs, "40"));
        double startAngle = Math.toRadians(doubleValue(firstValue(pairs, "50")));
        double endAngle = Math.toRadians(doubleValue(firstValue(pairs, "51")));

        if (r <= 0) {
            return;
        }

        // DXF中弧始终逆时针，终止角小于起始角表示跨0度
        if (endAngle <= startAngle) {
            endAngle += 2 * Math.PI;
        }

        for (int i = 0; i <= ARC_SEGMENTS; i++) {
            double angle = startAngle + (endAngle - startAngle) * i / ARC_SEGMENTS;
            entity.addVertex(cx + r * Math.cos(angle), cy + r * Math.sin(angle), cz);
        }
    }

    /** POINT：单点10/20/30 */
    private void buildPoint(CadEntity entity, List<String[]> pairs) {
        entity.addVertex(
                doubleValue(firstValue(pairs, "10")),
                doubleValue(firstValue(pairs, "20")),
                doubleValue(firstValue(pairs, "30")));
    }

    /** TEXT/MTEXT：插入点 + 组码1文本内容（MTEXT的组码3为文本前缀块） */
    private void buildText(CadEntity entity, List<String[]> pairs) {
        entity.addVertex(
                doubleValue(firstValue(pairs, "10")),
                doubleValue(firstValue(pairs, "20")),
                doubleValue(firstValue(pairs, "30")));

        StringBuilder text = new StringBuilder();
        // MTEXT长文本会被拆分为多个组码3前缀块 + 组码1结尾块
        for (String[] pair : pairs) {
            if ("3".equals(pair[0])) {
                text.append(pair[1]);
            }
        }
        String tail = firstValue(pairs, "1");
        if (tail != null) {
            text.append(tail);
        }
        entity.setText(text.toString());
    }

    /** 其他类型：若含组码10/20则按单点提取 */
    private void buildGeneric(CadEntity entity, List<String[]> pairs) {
        String x = firstValue(pairs, "10");
        String y = firstValue(pairs, "20");
        if (x != null && y != null) {
            entity.addVertex(doubleValue(x), doubleValue(y), doubleValue(firstValue(pairs, "30")));
        }
    }

    /** 取指定组码的第一个组值 */
    private String firstValue(List<String[]> pairs, String code) {
        for (String[] pair : pairs) {
            if (pair[0].equals(code)) {
                return pair[1];
            }
        }
        return null;
    }

    private double doubleValue(String value) {
        if (value == null || value.isEmpty()) return 0;
        try {
            return Double.parseDouble(value);
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    private int intValue(String value) {
        if (value == null || value.isEmpty()) return 0;
        try {
            return (int) Double.parseDouble(value);
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

        /** 添加实体并同步更新图层/类型统计 */
        public void addEntity(CadEntity entity) {
            entities.add(entity);
            String layer = entity.getLayerName() != null ? entity.getLayerName() : "DEFAULT";
            layerStats.merge(layer, 1, Integer::sum);
            typeStats.merge(entity.getEntityType(), 1, Integer::sum);
        }
    }
}
