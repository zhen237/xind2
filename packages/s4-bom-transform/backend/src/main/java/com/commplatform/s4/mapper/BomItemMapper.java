package com.commplatform.s4.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.commplatform.s4.entity.BomItem;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * s4_bom_item Mapper。
 */
@Mapper
public interface BomItemMapper extends BaseMapper<BomItem> {

    List<BomItem> selectByTaskId(@Param("taskId") String taskId);

    int deleteByTaskId(@Param("taskId") String taskId);
}
