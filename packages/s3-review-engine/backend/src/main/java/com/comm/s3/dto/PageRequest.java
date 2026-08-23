package com.comm.s3.dto;

import lombok.Data;

/**
 * 分页请求DTO
 */
@Data
public class PageRequest {
    private Integer pageNum = 1;
    private Integer pageSize = 10;
    private String riskLevel; // 筛选风险等级
    private String keyword; // 关键字搜索
    private String orderBy = "createTime"; // 排序字段
    private String orderType = "desc"; // 排序方式
}
