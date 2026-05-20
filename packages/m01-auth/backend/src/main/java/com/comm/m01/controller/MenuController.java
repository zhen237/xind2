package com.comm.m01.controller;

import com.comm.m01.entity.Menu;
import com.comm.m01.service.MenuService;
import com.comm.m01.utils.JwtUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/m01/menu")
public class MenuController {
    @Autowired
    private MenuService menuService;
    @Autowired
    private JwtUtils jwtUtils;

    @GetMapping("/user")
    public ResponseEntity<List<Menu>> getUserMenu(@RequestHeader("Authorization") String authHeader) {
        String token = authHeader.substring(7);
        Long userId = jwtUtils.getUserIdFromToken(token);
        List<Menu> menus = menuService.buildMenuTree(userId);
        return ResponseEntity.ok(menus);
    }
}
