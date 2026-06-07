package com.comm.m03.design.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.comm.m03.design.entity.Site;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Delete;

import java.util.List;

/**
 * 站点Mapper
 */
@Mapper
public interface SiteMapper extends BaseMapper<Site> {

    /**
     * 根据方案ID查询站点
     * @param schemeId 方案ID
     * @return 站点列表
     */
    @Select("SELECT * FROM m03_site WHERE scheme_id = #{schemeId}")
    List<Site> selectBySchemeId(Long schemeId);

    /**
     * 根据方案ID删除站点
     * @param schemeId 方案ID
     */
    @Delete("DELETE FROM m03_site WHERE scheme_id = #{schemeId}")
    void deleteBySchemeId(Long schemeId);
}
