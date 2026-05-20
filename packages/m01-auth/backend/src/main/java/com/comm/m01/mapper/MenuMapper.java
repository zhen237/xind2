package com.comm.m01.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.comm.m01.entity.Menu;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface MenuMapper extends BaseMapper<Menu> {
    @Select("SELECT m.* FROM m01_menu m " +
            "JOIN m01_role_menu rm ON m.id = rm.menu_id " +
            "JOIN m01_user_role ur ON rm.role_id = ur.role_id " +
            "WHERE ur.user_id = #{userId} AND m.status = 1 " +
            "ORDER BY m.sort_order")
    List<Menu> findMenusByUserId(Long userId);

    @Select("SELECT * FROM m01_menu WHERE parent_id = 0 AND status = 1 ORDER BY sort_order")
    List<Menu> findTopLevelMenus();

    @Select("SELECT * FROM m01_menu WHERE parent_id = #{parentId} AND status = 1 ORDER BY sort_order")
    List<Menu> findChildrenByParentId(Long parentId);
}
