package com.comm.m01.service;

import com.comm.m01.entity.Menu;

import java.util.List;

public interface MenuService {
    List<Menu> getMenusByUserId(Long userId);
    List<Menu> buildMenuTree(Long userId);
}
