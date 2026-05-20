package com.comm.m01.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

@Data
@TableName("m01_menu")
public class Menu {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long parentId;
    private String menuCode;
    private String menuName;
    private Integer menuType;
    private String iframeUrl;
    private String permissionCode;
    private Integer sortOrder;
    private Integer status;
    private LocalDateTime createTime;
    private List<Menu> children;
}
