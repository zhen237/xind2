package com.comm.m04.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.comm.m04.common.Result;
import com.comm.m04.entity.*;
import com.comm.m04.mapper.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 视频监理五大检查项统一控制器
 */
@RestController
@RequestMapping("/api/m04/surveillance")
public class VideoSurveillanceController {

    @Autowired private CertVerificationMapper certMapper;
    @Autowired private SafetyCheckMapper safetyMapper;
    @Autowired private ConstructionRecordMapper recordMapper;
    @Autowired private BarrierCheckMapper barrierMapper;
    @Autowired private ElectricityCheckMapper electricityMapper;

    // === 人证合一 ===
    @GetMapping("/cert/project/{projectId}")
    public Result<List<CertVerification>> listCertByProject(@PathVariable Long projectId) {
        return Result.success(certMapper.selectList(
                new LambdaQueryWrapper<CertVerification>().eq(CertVerification::getProjectId, projectId)));
    }

    @PostMapping("/cert")
    public Result<CertVerification> createCert(@RequestBody CertVerification cert) {
        certMapper.insert(cert);
        return Result.success(cert);
    }

    @PutMapping("/cert/{id}/verify")
    public Result<Void> verifyCert(@PathVariable Long id, @RequestParam Integer result, @RequestParam(required = false) String comment) {
        CertVerification cert = new CertVerification();
        cert.setId(id);
        cert.setVerifyResult(result);
        cert.setVerifyComment(comment);
        certMapper.updateById(cert);
        return Result.success();
    }

    // === 个人安全防护 ===
    @GetMapping("/safety/project/{projectId}")
    public Result<List<SafetyCheck>> listSafetyByProject(@PathVariable Long projectId) {
        return Result.success(safetyMapper.selectList(
                new LambdaQueryWrapper<SafetyCheck>().eq(SafetyCheck::getProjectId, projectId)));
    }

    @PostMapping("/safety")
    public Result<SafetyCheck> createSafety(@RequestBody SafetyCheck check) {
        safetyMapper.insert(check);
        return Result.success(check);
    }

    // === 施工总体情况 ===
    @GetMapping("/record/project/{projectId}")
    public Result<List<ConstructionRecord>> listRecordByProject(@PathVariable Long projectId) {
        return Result.success(recordMapper.selectList(
                new LambdaQueryWrapper<ConstructionRecord>().eq(ConstructionRecord::getProjectId, projectId)));
    }

    @PostMapping("/record")
    public Result<ConstructionRecord> createRecord(@RequestBody ConstructionRecord record) {
        recordMapper.insert(record);
        return Result.success(record);
    }

    // === 安全围栏及警示标志 ===
    @GetMapping("/barrier/project/{projectId}")
    public Result<List<BarrierCheck>> listBarrierByProject(@PathVariable Long projectId) {
        return Result.success(barrierMapper.selectList(
                new LambdaQueryWrapper<BarrierCheck>().eq(BarrierCheck::getProjectId, projectId)));
    }

    @PostMapping("/barrier")
    public Result<BarrierCheck> createBarrier(@RequestBody BarrierCheck check) {
        barrierMapper.insert(check);
        return Result.success(check);
    }

    // === 临时用电 ===
    @GetMapping("/electricity/project/{projectId}")
    public Result<List<ElectricityCheck>> listElectricityByProject(@PathVariable Long projectId) {
        return Result.success(electricityMapper.selectList(
                new LambdaQueryWrapper<ElectricityCheck>().eq(ElectricityCheck::getProjectId, projectId)));
    }

    @PostMapping("/electricity")
    public Result<ElectricityCheck> createElectricity(@RequestBody ElectricityCheck check) {
        electricityMapper.insert(check);
        return Result.success(check);
    }
}
