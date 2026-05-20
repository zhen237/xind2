package com.comm.m05.config;

import com.comm.m05.service.AlertService;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.eclipse.paho.client.mqttv3.*;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import jakarta.annotation.PostConstruct;

@Component
public class MqttSubscriber {
    private static final Logger logger = LoggerFactory.getLogger(MqttSubscriber.class);
    
    @Value("${mqtt.broker}")
    private String broker;
    @Value("${mqtt.username}")
    private String username;
    @Value("${mqtt.password}")
    private String password;
    
    private MqttClient client;
    private final AlertService alertService;
    private final ObjectMapper objectMapper;

    public MqttSubscriber(AlertService alertService, ObjectMapper objectMapper) {
        this.alertService = alertService;
        this.objectMapper = objectMapper;
    }

    @PostConstruct
    public void init() {
        try {
            String clientId = "m05-backend-" + System.currentTimeMillis();
            MqttConnectOptions options = new MqttConnectOptions();
            options.setUserName(username);
            options.setPassword(password.toCharArray());
            options.setAutomaticReconnect(true);
            options.setCleanSession(true);
            
            client = new MqttClient(broker, clientId, new MemoryPersistence());
            client.connect(options);
            
            client.subscribe("/device/+/alert", (topic, message) -> {
                try {
                    String payload = new String(message.getPayload());
                    JsonNode node = objectMapper.readTree(payload);
                    String deviceCode = node.get("deviceCode").asText();
                    String content = node.get("content").asText();
                    int level = node.get("level").asInt();
                    
                    logger.info("Received MQTT alert: device={}, level={}, content={}", deviceCode, level, content);
                    alertService.processMqttAlert(deviceCode, content, level);
                } catch (Exception e) {
                    logger.error("Failed to process MQTT message", e);
                }
            });
            
            logger.info("MQTT subscriber connected to {}", broker);
        } catch (MqttException e) {
            logger.error("Failed to connect to MQTT broker", e);
        }
    }
}
