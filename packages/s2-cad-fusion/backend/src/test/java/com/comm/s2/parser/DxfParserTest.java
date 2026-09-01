package com.comm.s2.parser;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * DXF解析器单元测试：覆盖LINE、LWPOLYLINE（闭合多顶点）、
 * POLYLINE/VERTEX/SEQEND、TEXT、CIRCLE等核心实体类型。
 */
class DxfParserTest {

    @TempDir
    Path tempDir;

    private DxfParser parser;

    @BeforeEach
    void setUp() {
        parser = new DxfParser();
    }

    private Path writeDxf(String entitiesBody) throws Exception {
        StringBuilder dxf = new StringBuilder();
        dxf.append("0\nSECTION\n2\nHEADER\n0\nENDSEC\n");
        dxf.append("0\nSECTION\n2\nENTITIES\n");
        dxf.append(entitiesBody);
        dxf.append("0\nENDSEC\n0\nEOF\n");
        Path file = tempDir.resolve("test.dxf");
        Files.writeString(file, dxf.toString());
        return file;
    }

    @Test
    void shouldParseLineEntity() throws Exception {
        Path file = writeDxf(
                "0\nLINE\n8\nROAD\n10\n100.0\n20\n200.0\n30\n0.0\n11\n150.0\n21\n250.0\n31\n0.0\n");

        DxfParser.ParseResult result = parser.parse(file.toString());

        assertTrue(result.isSuccess());
        assertEquals(1, result.getEntities().size());
        CadEntity entity = result.getEntities().get(0);
        assertEquals("LINE", entity.getEntityType());
        assertEquals("ROAD", entity.getLayerName());
        assertEquals(2, entity.getVertices().size());
        assertEquals(100.0, entity.getVertices().get(0).getX().doubleValue(), 1e-9);
        assertEquals(250.0, entity.getVertices().get(1).getY().doubleValue(), 1e-9);
    }

    @Test
    void shouldParseLwPolylineWithMultipleVertices() throws Exception {
        // 闭合LWPOLYLINE：3个顶点 + 闭合标志70=1
        Path file = writeDxf(
                "0\nLWPOLYLINE\n8\nBUILDING\n90\n3\n70\n1\n"
                + "10\n0.0\n20\n0.0\n"
                + "10\n10.0\n20\n0.0\n"
                + "10\n10.0\n20\n10.0\n");

        DxfParser.ParseResult result = parser.parse(file.toString());

        assertTrue(result.isSuccess());
        assertEquals(1, result.getEntities().size());
        CadEntity entity = result.getEntities().get(0);
        assertTrue(entity.isClosed());
        // 3个原始顶点 + 闭合补点 = 4
        assertEquals(4, entity.getVertices().size());
        // 闭合折线应为面
        assertEquals("POLYGON", entity.getGeometryType());
    }

    @Test
    void shouldParsePolylineWithVertexSequence() throws Exception {
        // 老式POLYLINE + 2个VERTEX + SEQEND
        Path file = writeDxf(
                "0\nPOLYLINE\n8\nPIPELINE\n70\n0\n"
                + "0\nVERTEX\n8\nPIPELINE\n10\n1.0\n20\n2.0\n30\n0.0\n"
                + "0\nVERTEX\n8\nPIPELINE\n10\n3.0\n20\n4.0\n30\n0.0\n"
                + "0\nVERTEX\n8\nPIPELINE\n10\n5.0\n20\n6.0\n30\n0.0\n"
                + "0\nSEQEND\n8\nPIPELINE\n"
                + "0\nLINE\n8\nROAD\n10\n0\n20\n0\n11\n1\n21\n1\n");

        DxfParser.ParseResult result = parser.parse(file.toString());

        assertTrue(result.isSuccess());
        // POLYLINE（含3个顶点）+ LINE，VERTEX和SEQEND不应单独成实体
        assertEquals(2, result.getEntities().size());

        CadEntity polyline = result.getEntities().stream()
                .filter(e -> "POLYLINE".equals(e.getEntityType()))
                .findFirst().orElseThrow();
        assertEquals(3, polyline.getVertices().size());
        assertEquals(5.0, polyline.getVertices().get(2).getX().doubleValue(), 1e-9);
    }

    @Test
    void shouldExtractTextContent() throws Exception {
        Path file = writeDxf(
                "0\nTEXT\n8\nANNOTATION\n1\n阀门井K-01\n10\n50.0\n20\n60.0\n30\n0.0\n");

        DxfParser.ParseResult result = parser.parse(file.toString());

        assertEquals(1, result.getEntities().size());
        CadEntity entity = result.getEntities().get(0);
        assertEquals("TEXT", entity.getEntityType());
        assertEquals("阀门井K-01", entity.getText());
    }

    @Test
    void shouldDiscretizeCircleIntoClosedRing() throws Exception {
        Path file = writeDxf(
                "0\nCIRCLE\n8\nWATER\n10\n0.0\n20\n0.0\n30\n0.0\n40\n5.0\n");

        DxfParser.ParseResult result = parser.parse(file.toString());

        assertEquals(1, result.getEntities().size());
        CadEntity circle = result.getEntities().get(0);
        assertTrue(circle.isClosed());
        // 64段 + 收尾点 = 65个顶点
        assertEquals(65, circle.getVertices().size());
        assertEquals("POLYGON", circle.getGeometryType());
    }

    @Test
    void shouldComputeLayerStatistics() throws Exception {
        Path file = writeDxf(
                "0\nLINE\n8\nROAD\n10\n0\n20\n0\n11\n1\n21\n1\n"
                + "0\nLINE\n8\nROAD\n10\n0\n20\n0\n11\n1\n21\n1\n"
                + "0\nPOINT\n8\nTREE\n10\n7\n20\n8\n30\n0\n");

        DxfParser.ParseResult result = parser.parse(file.toString());

        assertEquals(3, result.getEntities().size());
        assertEquals(2, result.getLayerStats().get("ROAD"));
        assertEquals(1, result.getLayerStats().get("TREE"));
    }

    @Test
    void shouldReturnEmptyWhenNoEntitiesSection() throws Exception {
        Path file = tempDir.resolve("empty.dxf");
        Files.writeString(file, "0\nSECTION\n2\nHEADER\n0\nENDSEC\n0\nEOF\n");

        DxfParser.ParseResult result = parser.parse(file.toString());

        assertTrue(result.isSuccess());
        assertTrue(result.getEntities().isEmpty());
    }

    @Test
    void shouldNotParseEntitiesAfterEndsec() throws Exception {
        // ENDSEC之后不应继续解析（避免BLOCKS段重复入库）
        Path file = writeDxf(
                "0\nLINE\n8\nROAD\n10\n0\n20\n0\n11\n1\n21\n1\n");

        DxfParser.ParseResult result = parser.parse(file.toString());
        assertEquals(1, result.getEntities().size());
    }
}
