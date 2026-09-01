package com.comm.m03.design.service;

import com.comm.m03.design.entity.GenerateRequest;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * RSRP / 路径损耗传播模型的纯单元测试（无需 Spring 容器、无需数据库）。
 *
 * 三道防线：
 *  ① Oracle（权威基准）：与 Okumura-Hata 文献经典值对齐，证明公式实现正确；
 *  ② 不变式（Invariant）：RSRP 随距离/频率/塔高单调，假实现过不了；
 *  ③ 交叉验证：computePathLossDb 与 Python 拓扑引擎 calculate_okumura_hata_path_loss
 *     共享同一基准（f=900MHz, hb=30m, hm=1.5m, d=1km, 城区 → 126.4 dB），
 *     两种独立语言实现都通过该基准，互相审计。
 */
public class PropagationModelTest {

    // 权威基准：Okumura-Hata 文献经典值
    // f=900MHz, hb=30m, hm=1.5m, d=1km, 城区环境 → 路径损耗 ≈ 126.4 dB
    private static final double ORACLE_900_1KM_URBAN = 126.4;

    @Test
    @DisplayName("① Oracle：900MHz/30m/1km/城区 路径损耗 ≈ 126.4dB")
    public void testPathLossOracle() {
        double L = DesignService.computePathLossDb(900.0, 1.0, 30.0, 1.5, "urban");
        assertEquals(ORACLE_900_1KM_URBAN, L, 0.5,
                "应与 Okumura-Hata 文献基准一致（±0.5dB）");
    }

    @Test
    @DisplayName("② Invariant：路径损耗随距离单调递增")
    public void testPathLossMonotonicInDistance() {
        double near = DesignService.computePathLossDb(1800, 0.5, 30, 1.5, "urban");
        double far = DesignService.computePathLossDb(1800, 2.0, 30, 1.5, "urban");
        assertTrue(far > near, "距离越远路径损耗应越大");
    }

    @Test
    @DisplayName("② Invariant：路径损耗随频率单调递增（>200MHz 频段内）")
    public void testPathLossMonotonicInFrequency() {
        double low = DesignService.computePathLossDb(1800, 0.5, 30, 1.5, "urban");
        double high = DesignService.computePathLossDb(2600, 0.5, 30, 1.5, "urban");
        assertTrue(high > low, "频率越高路径损耗应越大");
    }

    @Test
    @DisplayName("② Invariant：环境修正顺序 城区>郊区>农村 路径损耗")
    public void testScenarioOrdering() {
        double urban = DesignService.computePathLossDb(1800, 0.5, 30, 1.5, "urban");
        double suburban = DesignService.computePathLossDb(1800, 0.5, 30, 1.5, "suburban");
        double rural = DesignService.computePathLossDb(1800, 0.5, 30, 1.5, "rural");
        assertTrue(urban > suburban, "城区损耗应大于郊区");
        assertTrue(suburban > rural, "郊区损耗应大于农村");
    }

    @Test
    @DisplayName("① Oracle：1800MHz/30m/城区/0.5km 的 RSRP ≈ -80.7dBm（= -路径损耗 + 43）")
    public void testRsrpOracle() {
        GenerateRequest req = new GenerateRequest();
        req.setFrequencyBand("fdd-lte-1800");
        req.setScenario("urban");
        req.setTowerHeight(BigDecimal.valueOf(30));

        BigDecimal rsrp = new DesignService().calculateRsrp(req, BigDecimal.valueOf(30));
        // 路径损耗 ≈ 123.7 → RSRP = -123.7 + 43 = -80.7
        assertEquals(-80.7, rsrp.doubleValue(), 0.1, "RSRP 应等于 -路径损耗 + 43");
    }

    @Test
    @DisplayName("② Invariant：RSRP 随塔高单调递增（塔越高损耗越低，RSRP 越大）")
    public void testRsrpMonotonicInTowerHeight() {
        GenerateRequest low = new GenerateRequest();
        low.setFrequencyBand("fdd-lte-1800");
        low.setScenario("urban");
        low.setTowerHeight(BigDecimal.valueOf(20));

        GenerateRequest high = new GenerateRequest();
        high.setFrequencyBand("fdd-lte-1800");
        high.setScenario("urban");
        high.setTowerHeight(BigDecimal.valueOf(40));

        double rLow = new DesignService().calculateRsrp(low, BigDecimal.valueOf(20)).doubleValue();
        double rHigh = new DesignService().calculateRsrp(high, BigDecimal.valueOf(40)).doubleValue();
        assertTrue(rHigh > rLow, "塔越高 RSRP 应越大");
    }
}
