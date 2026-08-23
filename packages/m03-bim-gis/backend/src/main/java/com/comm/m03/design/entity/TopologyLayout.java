package com.comm.m03.design.entity;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.util.List;

/**
 * Python 拓扑引擎返回的设备布局（扁平化的全量设备拓扑）
 */
@Data
public class TopologyLayout {

    @JsonProperty("task_id")
    private String taskId;

    @JsonProperty("devices")
    private List<TopologyDevicePosition> devices;
}
