package com.comm.m01.controller;

import com.comm.common.Result;
import com.comm.m01.entity.Menu;
import com.comm.m01.service.MenuService;
import com.comm.utils.JwtUtils;
import org.springframework.beans.factory.annotation.Autowired;
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
    public Result<List<Menu>> getUserMenu(@RequestHeader(value = "Authorization", required = false) String authHeader) {
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            return Result.unauthorized("缺少认证令牌");
        }
        String token = authHeader.substring(7);
        if (!jwtUtils.validateToken(token)) {
            return Result.unauthorized("令牌已过期或无效");
        }
        Long userId = jwtUtils.getUserIdFromToken(token);
        List<Menu> menus = menuService.buildMenuTree(userId);
        return Result.success(menus);
    }
}
