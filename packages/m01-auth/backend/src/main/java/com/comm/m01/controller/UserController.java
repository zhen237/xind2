package com.comm.m01.controller;

import com.comm.common.Result;
import com.comm.m01.entity.User;
import com.comm.m01.service.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/m01/user")
public class UserController {
    @Autowired
    private UserService userService;

    @GetMapping
    public Result<List<User>> getAllUsers() {
        return Result.success(userService.findAll());
    }

    @GetMapping("/{id}")
    public Result<User> getUserById(@PathVariable Long id) {
        User user = userService.findById(id);
        if (user == null) {
            return Result.notFound("用户不存在");
        }
        return Result.success(user);
    }

    @PostMapping
    public Result<User> createUser(@RequestBody User user) {
        return Result.success("创建成功", userService.create(user));
    }

    @PutMapping("/{id}")
    public Result<User> updateUser(@PathVariable Long id, @RequestBody User user) {
        user.setId(id);
        return Result.success("更新成功", userService.update(user));
    }

    @DeleteMapping("/{id}")
    public Result<Void> deleteUser(@PathVariable Long id) {
        userService.delete(id);
        return Result.success("删除成功", null);
    }
}
