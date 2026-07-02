package com.comm.m01.controller;

import com.comm.common.Result;
import com.comm.m01.dto.LoginRequest;
import com.comm.m01.entity.User;
import com.comm.m01.service.UserService;
import com.comm.utils.JwtUtils;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/m01/auth")
public class AuthController {
    @Autowired
    private UserService userService;
    @Autowired
    private JwtUtils jwtUtils;
    @Autowired
    private BCryptPasswordEncoder passwordEncoder;

    @PostMapping("/login")
    public Result<Map<String, Object>> login(@Valid @RequestBody LoginRequest request) {
        String username = request.getUsername();
        String password = request.getPassword();

        User user = userService.findByUsername(username);
        if (user == null || !passwordEncoder.matches(password, user.getPassword())) {
            return Result.error(401, "用户名或密码错误");
        }
        if (user.getStatus() != 1) {
            return Result.error(401, "用户已禁用");
        }

        String token = jwtUtils.generateToken(user.getId(), user.getUsername());
        Map<String, Object> data = new HashMap<>();
        data.put("token", token);
        data.put("userId", user.getId());
        data.put("username", user.getUsername());
        data.put("realName", user.getRealName());
        return Result.success("登录成功", data);
    }

    @GetMapping("/validate")
    public Result<Map<String, Object>> validateToken(@RequestHeader(value = "Authorization", required = false) String authHeader) {
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            return Result.unauthorized("缺少认证令牌");
        }
        String token = authHeader.substring(7);
        if (jwtUtils.validateToken(token)) {
            Long userId = jwtUtils.getUserIdFromToken(token);
            String username = jwtUtils.getUsernameFromToken(token);
            Map<String, Object> data = new HashMap<>();
            data.put("userId", userId);
            data.put("username", username);
            return Result.success(data);
        }
        return Result.unauthorized("令牌已过期或无效");
    }
}
