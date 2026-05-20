package com.comm.m01.service.impl;

import com.comm.m01.entity.Menu;
import com.comm.m01.mapper.MenuMapper;
import com.comm.m01.service.MenuService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class MenuServiceImpl implements MenuService {
    @Autowired
    private MenuMapper menuMapper;

    @Override
    public List<Menu> getMenusByUserId(Long userId) {
        return menuMapper.findMenusByUserId(userId);
    }

    @Override
    public List<Menu> buildMenuTree(Long userId) {
        List<Menu> menus = getMenusByUserId(userId);
        Map<Long, List<Menu>> childrenMap = menus.stream()
                .filter(m -> m.getParentId() != 0)
                .collect(Collectors.groupingBy(Menu::getParentId));
        
        List<Menu> rootMenus = new ArrayList<>();
        for (Menu menu : menus) {
            if (menu.getParentId() == 0) {
                menu.setChildren(childrenMap.getOrDefault(menu.getId(), new ArrayList<>()));
                rootMenus.add(menu);
            }
        }
        rootMenus.sort((a, b) -> Integer.compare(a.getSortOrder(), b.getSortOrder()));
        return rootMenus;
    }
}
