package com.comm.m05.service.impl;

import com.comm.m05.entity.Alert;
import com.comm.m05.entity.Device;
import com.comm.m05.mapper.AlertMapper;
import com.comm.m05.mapper.DeviceMapper;
import com.comm.m05.service.AlertService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class AlertServiceImpl implements AlertService {
    @Autowired
    private AlertMapper alertMapper;
    @Autowired
    private DeviceMapper deviceMapper;
    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Override
    @Transactional
    public Alert create(Alert alert) {
        alertMapper.insert(alert);
        return alert;
    }

    @Override
    @Transactional
    public Alert update(Alert alert) {
        alertMapper.updateById(alert);
        return alert;
    }

    @Override
    public Alert findById(Long id) {
        return alertMapper.selectById(id);
    }

    @Override
    public List<Alert> findByDeviceId(Long deviceId) {
        return alertMapper.findByDeviceId(deviceId);
    }

    @Override
    public List<Alert> findByStatus(Integer status) {
        return alertMapper.findByStatus(status);
    }

    @Override
    public List<Alert> findRecent(int limit) {
        return alertMapper.findRecent(limit);
    }

    @Override
    public List<Alert> findByLevel(Integer level) {
        return alertMapper.findByLevel(level);
    }

    @Override
    @Transactional
    public void confirmAlert(Long id) {
        Alert alert = alertMapper.selectById(id);
        if (alert != null) {
            alert.setStatus(1);
            alertMapper.updateById(alert);
        }
    }

    @Override
    @Transactional
    public void resolveAlert(Long id, String orderNo) {
        Alert alert = alertMapper.selectById(id);
        if (alert != null) {
            alert.setStatus(2);
            alert.setOrderNo(orderNo);
            alertMapper.updateById(alert);
        }
    }

    @Override
    public long countUnprocessed() {
        return alertMapper.countUnprocessed();
    }

    @Override
    public Map<String, Long> getAlertStatistics() {
        Map<String, Long> stats = new HashMap<>();
        stats.put("totalUnprocessed", alertMapper.countUnprocessed());
        stats.put("critical", alertMapper.countUnprocessedByLevel(1));
        stats.put("important", alertMapper.countUnprocessedByLevel(2));
        stats.put("warning", alertMapper.countUnprocessedByLevel(3));
        stats.put("info", alertMapper.countUnprocessedByLevel(4));
        return stats;
    }

    @Override
    @Transactional
    public void processMqttAlert(String deviceCode, String content, Integer level) {
        Device device = deviceMapper.selectOne(new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<Device>()
                .eq(Device::getDeviceCode, deviceCode));
        
        Alert alert = new Alert();
        if (device != null) {
            alert.setDeviceId(device.getId());
        }
        alert.setDeviceCode(deviceCode);
        alert.setAlertContent(content);
        alert.setLevel(level);
        alert.setStatus(0);
        alert.setSource("MQTT");
        alertMapper.insert(alert);
        
        if (level <= 2) {
            String orderNo = "WO" + System.currentTimeMillis();
            jdbcTemplate.update(
                "INSERT INTO m04_work_order (order_no, title, type, priority, status, device_code, create_time) " +
                "VALUES (?, ?, 'alert', ?, 0, ?, NOW())",
                orderNo, "告警工单: " + content, level, deviceCode
            );
            alert.setOrderNo(orderNo);
            alertMapper.updateById(alert);
        }
    }
}
