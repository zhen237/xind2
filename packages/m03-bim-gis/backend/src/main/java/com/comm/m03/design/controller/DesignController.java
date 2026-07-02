package com.comm.m03.design.controller;

import com.comm.m03.design.entity.DesignData;
import com.comm.m03.design.entity.DesignScheme;
import com.comm.m03.design.entity.Site;
import com.comm.m03.design.entity.SiteData;
import com.comm.m03.design.service.DesignService;
import com.comm.common.Result;
import com.comm.m03.rate_limit.RateLimit;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 设计数据控制器
 * 负责处理QGIS插件的设计数据上传和查询
 */
@RestController
@RequestMapping("/api/m03/design")
public class DesignController {

    @Autowired
    private DesignService designService;

    /**
     * 上传设计方案
     * @param designData 设计数据
     * @return 结果
     */
    @PostMapping("/upload")
    @RateLimit(permitsPerSecond = 10.0)
    public Result uploadDesign(@RequestBody DesignData designData) {
        try {
            // 保存设计方案
            Long schemeId = designService.saveDesignScheme(designData);

            // 保存站点数据
            designService.saveSites(schemeId, designData.getSites());

            return Result.success("上传成功", schemeId);
        } catch (Exception e) {
            return Result.error("上传失败: " + e.getMessage());
        }
    }

    /**
     * 获取设计方案
     * @param projectId 项目ID
     * @return 设计方案
     */
    @GetMapping("/{projectId}")
    public Result getDesign(@PathVariable Long projectId) {
        try {
            DesignScheme scheme = designService.getDesignScheme(projectId);
            if (scheme == null) {
                return Result.error("未找到设计方案");
            }
            return Result.success(scheme);
        } catch (Exception e) {
            return Result.error("获取失败: " + e.getMessage());
        }
    }

    /**
     * 上传站点数据
     * @param schemeId 方案ID
     * @param siteData 站点数据
     * @return 结果
     */
    @PostMapping("/{schemeId}/sites")
    @RateLimit(permitsPerSecond = 10.0)
    public Result uploadSite(@PathVariable Long schemeId, @RequestBody SiteData siteData) {
        try {
            designService.saveSite(schemeId, siteData);
            return Result.success("上传成功");
        } catch (Exception e) {
            return Result.error("上传失败: " + e.getMessage());
        }
    }

    /**
     * 获取站点数据
     * @param schemeId 方案ID
     * @return 站点列表
     */
    @GetMapping("/{schemeId}/sites")
    public Result getSites(@PathVariable Long schemeId) {
        try {
            List<Site> sites = designService.getSites(schemeId);
            return Result.success(sites);
        } catch (Exception e) {
            return Result.error("获取失败: " + e.getMessage());
        }
    }

    /**
     * 获取GeoJSON数据
     * @param projectId 项目ID
     * @return GeoJSON数据
     */
    @GetMapping("/{projectId}/geojson")
    public Result getGeoJson(@PathVariable Long projectId) {
        try {
            String geoJson = designService.getGeoJson(projectId);
            return Result.success(geoJson);
        } catch (Exception e) {
            return Result.error("获取失败: " + e.getMessage());
        }
    }

    /**
     * 删除设计方案
     * @param schemeId 方案ID
     * @return 结果
     */
    @DeleteMapping("/{schemeId}")
    public Result deleteDesign(@PathVariable Long schemeId) {
        try {
            designService.deleteDesignScheme(schemeId);
            return Result.success("删除成功");
        } catch (Exception e) {
            return Result.error("删除失败: " + e.getMessage());
        }
    }
}
