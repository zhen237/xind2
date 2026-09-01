package com.comm.m02.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.comm.m02.entity.CadFile;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface CadFileMapper extends BaseMapper<CadFile> {

    @Select("SELECT * FROM m02_cad_file WHERE project_id = #{projectId} ORDER BY create_time DESC")
    List<CadFile> findByProjectId(@Param("projectId") Long projectId);

    @Select("SELECT * FROM m02_cad_file WHERE uploaded_by = #{userId} ORDER BY create_time DESC")
    List<CadFile> findByUserId(@Param("userId") Long userId);

    @Select("SELECT * FROM m02_cad_file WHERE parse_status = #{status}")
    List<CadFile> findByParseStatus(@Param("status") Integer status);
}
