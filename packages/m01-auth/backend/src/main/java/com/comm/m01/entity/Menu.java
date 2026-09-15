package com.comm.m01.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import java.time.LocalDateTime;
import java.util.List;

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

    /**
     * 树形结构的子菜单，由 service 层组装，**不是表列**。
     * 必须标 exist=false：MyBatis-Plus 默认会把实体字段带进 SELECT 字段列表，
     * m01_menu 里没有 children 列，否则菜单查询会报
     * Unknown column 'children' in 'field list'（同 m03 task_name 那类"启动正常、
     * 一查库就 500"的坑，见 docs/数据库迁移遗留问题-修复方案.md 新发现 N3）。
     */
    @TableField(exist = false)
    private List<Menu> children;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Long getParentId() {
        return parentId;
    }

    public void setParentId(Long parentId) {
        this.parentId = parentId;
    }

    public String getMenuCode() {
        return menuCode;
    }

    public void setMenuCode(String menuCode) {
        this.menuCode = menuCode;
    }

    public String getMenuName() {
        return menuName;
    }

    public void setMenuName(String menuName) {
        this.menuName = menuName;
    }

    public Integer getMenuType() {
        return menuType;
    }

    public void setMenuType(Integer menuType) {
        this.menuType = menuType;
    }

    public String getIframeUrl() {
        return iframeUrl;
    }

    public void setIframeUrl(String iframeUrl) {
        this.iframeUrl = iframeUrl;
    }

    public String getPermissionCode() {
        return permissionCode;
    }

    public void setPermissionCode(String permissionCode) {
        this.permissionCode = permissionCode;
    }

    public Integer getSortOrder() {
        return sortOrder;
    }

    public void setSortOrder(Integer sortOrder) {
        this.sortOrder = sortOrder;
    }

    public Integer getStatus() {
        return status;
    }

    public void setStatus(Integer status) {
        this.status = status;
    }

    public LocalDateTime getCreateTime() {
        return createTime;
    }

    public void setCreateTime(LocalDateTime createTime) {
        this.createTime = createTime;
    }

    public List<Menu> getChildren() {
        return children;
    }

    public void setChildren(List<Menu> children) {
        this.children = children;
    }
}