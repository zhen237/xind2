package com.comm.s2.transform;

import com.comm.s2.parser.CadEntity;
import com.comm.s2.parser.CadEntityExtractor;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * CAD-GIS语义映射单元测试：几何类型映射、图层→要素分类、文本label提升。
 */
class CadToGisMapperTest {

    private CadToGisMapper mapper;
    private CadEntityExtractor extractor;

    @BeforeEach
    void setUp() {
        mapper = new CadToGisMapper();
        extractor = new CadEntityExtractor();
    }

    @Test
    void shouldMapLineToLineString() {
        CadEntity line = new CadEntity();
        line.setEntityType("LINE");
        line.setLayerName("ROAD_CENTER");
        line.addVertex(0, 0, 0);
        line.addVertex(100, 100, 0);

        CadToGisMapper.GisMappingResult result = mapper.map(extractor.extract(line));

        assertEquals("LineString", result.getTargetGeometryType());
        assertEquals("road", result.getTargetFeatureClass());
        assertEquals(2, result.getCoordinates().size());
    }

    @Test
    void shouldMapClosedPolylineToPolygon() {
        CadEntity polyline = new CadEntity();
        polyline.setEntityType("LWPOLYLINE");
        polyline.setLayerName("BUILDING_OUTLINE");
        polyline.setClosed(true);
        polyline.addVertex(0, 0, 0);
        polyline.addVertex(10, 0, 0);
        polyline.addVertex(10, 10, 0);
        polyline.addVertex(0, 10, 0);

        CadToGisMapper.GisMappingResult result = mapper.map(extractor.extract(polyline));

        assertEquals("Polygon", result.getTargetGeometryType());
        assertEquals("building", result.getTargetFeatureClass());
        assertEquals(4, result.getCoordinates().size());
    }

    @Test
    void shouldMapTextToPointWithLabel() {
        CadEntity text = new CadEntity();
        text.setEntityType("TEXT");
        text.setLayerName("ANNOTATION");
        text.setText("1号教学楼");
        text.addVertex(50, 60, 0);

        CadToGisMapper.GisMappingResult result = mapper.map(extractor.extract(text));

        assertEquals("Point", result.getTargetGeometryType());
        assertEquals(1, result.getCoordinates().size());
        // 文本内容提升为label属性
        assertEquals("1号教学楼", result.getProperties().get("label"));
    }

    @Test
    void shouldMapUnknownLayerToOther() {
        CadEntity point = new CadEntity();
        point.setEntityType("POINT");
        point.setLayerName("SOMETHING_ELSE");
        point.addVertex(1, 2, 0);

        CadToGisMapper.GisMappingResult result = mapper.map(extractor.extract(point));

        assertEquals("other", result.getTargetFeatureClass());
        assertEquals("Point", result.getTargetGeometryType());
    }

    @Test
    void shouldCarrySourceInfoInProperties() {
        CadEntity line = new CadEntity();
        line.setEntityType("LINE");
        line.setLayerName("PIPELINE");
        line.addVertex(0, 0, 0);
        line.addVertex(1, 1, 0);

        CadToGisMapper.GisMappingResult result = mapper.map(extractor.extract(line));

        assertEquals("LINE", result.getProperties().get("sourceEntityType"));
        assertEquals("PIPELINE", result.getProperties().get("sourceLayer"));
        assertNotNull(result.getProperties().get("centerX"));
        assertNotNull(result.getProperties().get("extentMaxX"));
    }

    @Test
    void shouldMapAllEntities() {
        CadEntity a = new CadEntity();
        a.setEntityType("LINE");
        a.setLayerName("ROAD");
        a.addVertex(0, 0, 0);
        a.addVertex(1, 1, 0);

        CadEntity b = new CadEntity();
        b.setEntityType("CIRCLE");
        b.setLayerName("WATER");
        b.setClosed(true);
        b.addVertex(0, 0, 0);
        b.addVertex(1, 0, 0);
        b.addVertex(1, 1, 0);
        b.addVertex(0, 1, 0);

        List<CadToGisMapper.GisMappingResult> results =
                mapper.mapAll(extractor.extractAll(List.of(a, b)));

        assertEquals(2, results.size());
        assertTrue(results.stream().anyMatch(r -> "LineString".equals(r.getTargetGeometryType())));
        assertTrue(results.stream().anyMatch(r -> "Polygon".equals(r.getTargetGeometryType())));
    }
}
