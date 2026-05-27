package com.comm.m04.controller;

import com.comm.m04.common.Result;
import com.comm.m04.entity.Project;
import com.comm.m04.entity.WorkOrder;
import com.comm.m04.mapper.ProjectMapper;
import com.comm.m04.mapper.WorkOrderMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.HashMap;
import java.util.Map;

/**
 * 临时初始化控制器 - 用于快速插入测试数据
 * 访问 http://localhost:8084/api/m04/init-demo-data
 */
@RestController
@RequestMapping("/api/m04")
public class InitController {

    @Autowired
    private ProjectMapper projectMapper;

    @Autowired
    private WorkOrderMapper workOrderMapper;

    /**
     * 初始化测试数据
     * 访问地址：http://localhost:8084/api/m04/init-demo-data
     */
    @GetMapping("/init-demo-data")
    public Result<Map<String, Object>> initDemoData() {
        Map<String, Object> result = new HashMap<>();
        try {
            int projectCount = 0;
            int workOrderCount = 0;
            
            // 创建示例项目 - 如果已存在则跳过
            if (projectMapper.selectByMap(Map.of("project_code", "PRJ-2026-001")).isEmpty()) {
                Project p1 = new Project();
                p1.setProjectName("广州天河5G基站建设项目");
                p1.setProjectCode("PRJ-2026-001");
                p1.setRegionCode("CN_GZ");
                p1.setCurrentPhase("CONSTRUCTION");
                p1.setPhaseProgress(new BigDecimal("65.00"));
                p1.setTotalProgress(new BigDecimal("45.00"));
                p1.setStartDate(LocalDate.of(2026, 3, 1));
                p1.setPlannedEndDate(LocalDate.of(2026, 8, 30));
                p1.setConstructionUnit("中通建工有限公司");
                p1.setDesignUnit("华信设计院");
                p1.setSupervisionUnit("公诚监理");
                p1.setOwnerUnit("广东移动");
                p1.setStatus(1);
                projectMapper.insert(p1);
                projectCount++;
            }

            if (projectMapper.selectByMap(Map.of("project_code", "PRJ-2026-002")).isEmpty()) {
                Project p2 = new Project();
                p2.setProjectName("深圳南山机房改造工程");
                p2.setProjectCode("PRJ-2026-002");
                p2.setRegionCode("CN_SZ");
                p2.setCurrentPhase("DESIGN");
                p2.setPhaseProgress(new BigDecimal("90.00"));
                p2.setTotalProgress(new BigDecimal("25.00"));
                p2.setStartDate(LocalDate.of(2026, 4, 15));
                p2.setPlannedEndDate(LocalDate.of(2026, 10, 15));
                p2.setConstructionUnit("深圳电信工程");
                p2.setDesignUnit("南方设计院");
                p2.setSupervisionUnit("深圳监理");
                p2.setOwnerUnit("深圳电信");
                p2.setStatus(1);
                projectMapper.insert(p2);
                projectCount++;
            }

            if (projectMapper.selectByMap(Map.of("project_code", "PRJ-2026-003")).isEmpty()) {
                Project p3 = new Project();
                p3.setProjectName("北京朝阳管线敷设项目");
                p3.setProjectCode("PRJ-2026-003");
                p3.setRegionCode("CN_BJ");
                p3.setCurrentPhase("ACCEPTANCE");
                p3.setPhaseProgress(new BigDecimal("95.00"));
                p3.setTotalProgress(new BigDecimal("85.00"));
                p3.setStartDate(LocalDate.of(2026, 2, 10));
                p3.setPlannedEndDate(LocalDate.of(2026, 6, 30));
                p3.setConstructionUnit("北京工程局");
                p3.setDesignUnit("北京设计院");
                p3.setSupervisionUnit("北京监理");
                p3.setOwnerUnit("北京移动");
                p3.setStatus(1);
                projectMapper.insert(p3);
                projectCount++;
            }

            // 创建示例工单 - 如果已存在则跳过
            if (workOrderMapper.selectByMap(Map.of("order_no", "WO20260520001")).isEmpty()) {
                WorkOrder w1 = new WorkOrder();
                w1.setOrderNo("WO20260520001");
                w1.setTitle("基站高温告警处理");
                w1.setType("ALERT");
                w1.setPriority(1);
                w1.setStatus(1);
                w1.setStationCode("ST001");
                w1.setDeviceCode("BTS-1024");
                w1.setDescription("机柜温度超过阈值，需现场检查空调运行状态");
                workOrderMapper.insert(w1);
                workOrderCount++;
            }

            if (workOrderMapper.selectByMap(Map.of("order_no", "WO20260521002")).isEmpty()) {
                WorkOrder w2 = new WorkOrder();
                w2.setOrderNo("WO20260521002");
                w2.setTitle("RRU驻波比异常排查");
                w2.setType("ALERT");
                w2.setPriority(2);
                w2.setStatus(0);
                w2.setStationCode("ST002");
                w2.setDeviceCode("BTS-2049");
                w2.setDescription("驻波比超过1.5，需检查天线馈线连接");
                workOrderMapper.insert(w2);
                workOrderCount++;
            }

            if (workOrderMapper.selectByMap(Map.of("order_no", "WO20260522003")).isEmpty()) {
                WorkOrder w3 = new WorkOrder();
                w3.setOrderNo("WO20260522003");
                w3.setTitle("季度安全巡检");
                w3.setType("INSPECTION");
                w3.setPriority(3);
                w3.setStatus(0);
                w3.setStationCode("ST003");
                w3.setDescription("2026年Q2安全巡检，重点检查防雷接地和临时用电");
                workOrderMapper.insert(w3);
                workOrderCount++;
            }

            result.put("success", true);
            result.put("message", "测试数据初始化成功！");
            result.put("projects", 3);
            result.put("workOrders", 3);
            result.put("tip", "请刷新前端页面查看数据！");
            
            return Result.success(result);
        } catch (Exception e) {
            e.printStackTrace();
            result.put("success", false);
            result.put("message", "初始化失败：" + e.getMessage());
            return Result.error("初始化失败：" + e.getMessage());
        }
    }
}
