package com.comm.m01.service.impl;

import com.comm.common.BusinessException;
import com.comm.m01.entity.User;
import com.comm.m01.mapper.UserMapper;
import com.comm.m01.service.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class UserServiceImpl implements UserService {
    @Autowired
    private UserMapper userMapper;
    @Autowired
    private BCryptPasswordEncoder passwordEncoder;

    @Override
    public User findByUsername(String username) {
        return userMapper.findByUsername(username);
    }

    @Override
    public User findById(Long id) {
        return userMapper.selectById(id);
    }

    @Override
    public List<User> findAll() {
        return userMapper.selectList(null);
    }

    @Override
    @Transactional
    public User create(User user) {
        // 检查用户名重复
        User existing = userMapper.findByUsername(user.getUsername());
        if (existing != null) {
            throw new BusinessException(400, "用户名已存在: " + user.getUsername());
        }
        user.setPassword(passwordEncoder.encode(user.getPassword()));
        try {
            userMapper.insert(user);
        } catch (DuplicateKeyException e) {
            // 并发注册竞态：两个请求同时通过上面的查重，后插入者撞用户名唯一约束。
            // 此时用户已存在，按"用户名已存在"处理，避免抛 500。
            throw new BusinessException(400, "用户名已存在: " + user.getUsername());
        }
        return user;
    }

    @Override
    @Transactional
    public User update(User user) {
        // 如果更新了密码，重新加密
        if (user.getPassword() != null && !user.getPassword().isEmpty()) {
            user.setPassword(passwordEncoder.encode(user.getPassword()));
        }
        userMapper.updateById(user);
        return user;
    }

    @Override
    @Transactional
    public void delete(Long id) {
        userMapper.deleteById(id);
    }
}
