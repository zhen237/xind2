package com.comm.s3.dto;

import lombok.Data;
import java.util.List;

/**
 * 分页响应DTO
 */
@Data
public class PageResponse<T> {
    private Long total;
    private Integer pageNum;
    private Integer pageSize;
    private Integer totalPages;
    private List<T> list;

    public PageResponse(long total, int pageNum, int pageSize, List<T> list) {
        this.total = total;
        this.pageNum = pageNum;
        this.pageSize = pageSize;
        this.totalPages = (int) Math.ceil((double) total / pageSize);
        this.list = list;
    }
}
