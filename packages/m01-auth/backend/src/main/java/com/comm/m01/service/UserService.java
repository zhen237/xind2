package com.comm.m01.service;

import com.comm.m01.entity.User;
import java.util.List;

public interface UserService {
    User findByUsername(String username);
    User findById(Long id);
    List<User> findAll();
    User create(User user);
    User update(User user);
    void delete(Long id);
}
