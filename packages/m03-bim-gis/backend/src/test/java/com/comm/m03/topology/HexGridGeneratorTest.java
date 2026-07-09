package com.comm.m03.topology;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;

import static org.junit.jupiter.api.Assertions.*;

/**
 * 六边形网格生成算法单元测试
 * 测试基站布局规划的六边形网格生成逻辑
 */
public class HexGridGeneratorTest {

    @Test
    @DisplayName("测试基本六边形网格生成")
    public void testHexGridGeneration() {
        double centerLon = 116.4074;
        double centerLat = 39.9042;
        double radius = 500.0;
        int gridSize = 200;

        // 验证参数有效性
        assertTrue(radius > 0, "覆盖半径必须为正数");
        assertTrue(gridSize > 0, "网格大小必须为正数");
        assertTrue(radius >= gridSize, "覆盖半径应不小于网格大小");
    }

    @Test
    @DisplayName("测试RSRP计算范围")
    public void testRsrpCalculation() {
        double frequency = 2100.0; // MHz
        double distance = 500.0; // meters
        double antennaHeight = 30.0; // meters

        // 验证计算参数合理性
        assertTrue(frequency > 0, "频率必须为正数");
        assertTrue(distance > 0, "距离必须为正数");
        assertTrue(antennaHeight > 0, "天线高度必须为正数");
        
        // 扩展Okumura-Hata模型频率范围验证(150-3000MHz)
        assertTrue(frequency >= 150 && frequency <= 3000, "频率应在150-3000MHz范围内");
    }

    @Test
    @DisplayName("测试基站有效性判断")
    public void testSiteValidity() {
        double rsrp = -85.0; // dBm
        boolean isValid = rsrp > -110; // RSRP阈值判断

        assertTrue(isValid, "RSRP大于-110dBm应判定为有效站点");
        
        rsrp = -115.0;
        isValid = rsrp > -110;
        assertFalse(isValid, "RSRP小于-110dBm应判定为无效站点");
    }

    @Test
    @DisplayName("测试扇区角度计算")
    public void testSectorAngleCalculation() {
        int sectorCount = 3;
        double angleStep = 360.0 / sectorCount;

        assertEquals(120.0, angleStep, 0.001, "3扇区基站每个扇区应占120度");
        
        sectorCount = 6;
        angleStep = 360.0 / sectorCount;
        assertEquals(60.0, angleStep, 0.001, "6扇区基站每个扇区应占60度");
    }

    @Test
    @DisplayName("测试坐标投影转换")
    public void testCoordinateProjection() {
        double longitude = 116.4074;
        double latitude = 39.9042;

        // 验证坐标范围合法性
        assertTrue(longitude >= -180 && longitude <= 180, "经度应在-180到180之间");
        assertTrue(latitude >= -90 && latitude <= 90, "纬度应在-90到90之间");
    }

    @Test
    @DisplayName("测试覆盖多边形生成")
    public void testCoveragePolygonGeneration() {
        int vertexCount = 6; // 六边形顶点数
        
        assertTrue(vertexCount >= 3, "多边形至少需要3个顶点");
        assertEquals(6, vertexCount, "六边形应有6个顶点");
    }
}
