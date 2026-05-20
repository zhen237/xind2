package com.comm.m01.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.comm.m01.entity.User;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface UserMapper extends BaseMapper<User> {
    @Select("SELECT u.* FROM m01_user u WHERE u.username = #{username}")
    User findByUsername(String username);

    @Select("SELECT r.* FROM m01_role r " +
            "JOIN m01_user_role ur ON r.id = ur.role_id " +
            "WHERE ur.user_id = #{userId}")
    List<com.comm.m01.entity.Role> findRolesByUserId(Long userId);
}
