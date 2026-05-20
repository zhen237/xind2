package com.comm.m01.controller;

import com.comm.m01.entity.User;
import com.comm.m01.service.UserService;
import com.comm.m01.utils.JwtUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
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
    public ResponseEntity<?> login(@RequestBody Map<String, String> request) {
        String username = request.get("username");
        String password = request.get("password");
        
        User user = userService.findByUsername(username);
        if (user == null || !passwordEncoder.matches(password, user.getPassword())) {
            return ResponseEntity.status(401).body("用户名或密码错误");
        }
        if (user.getStatus() != 1) {
            return ResponseEntity.status(401).body("用户已禁用");
        }
        
        String token = jwtUtils.generateToken(user.getId(), user.getUsername());
        Map<String, Object> response = new HashMap<>();
        response.put("token", token);
        response.put("userId", user.getId());
        response.put("username", user.getUsername());
        response.put("realName", user.getRealName());
        return ResponseEntity.ok(response);
    }

    @GetMapping("/validate")
    public ResponseEntity<?> validateToken(@RequestHeader("Authorization") String authHeader) {
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            return ResponseEntity.status(401).body("无效的Token");
        }
        String token = authHeader.substring(7);
        if (jwtUtils.validateToken(token)) {
            Long userId = jwtUtils.getUserIdFromToken(token);
            String username = jwtUtils.getUsernameFromToken(token);
            Map<String, Object> response = new HashMap<>();
            response.put("userId", userId);
            response.put("username", username);
            return ResponseEntity.ok(response);
        }
        return ResponseEntity.status(401).body("Token已过期或无效");
    }
}
