package com.comm.m05.service;

import com.comm.m05.entity.Alert;

import java.util.List;
import java.util.Map;

public interface AlertService {
    Alert create(Alert alert);
    Alert update(Alert alert);
    Alert findById(Long id);
    List<Alert> findByDeviceId(Long deviceId);
    List<Alert> findByStatus(Integer status);
    List<Alert> findRecent(int limit);
    List<Alert> findByLevel(Integer level);
    void confirmAlert(Long id);
    void resolveAlert(Long id, String orderNo);
    long countUnprocessed();
    Map<String, Long> getAlertStatistics();
    void processMqttAlert(String deviceCode, String content, Integer level);
}
