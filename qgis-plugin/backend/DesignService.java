package com.comm.m03.design.service;

import com.comm.m03.design.entity.DesignScheme;
import com.comm.m03.design.entity.Site;
import com.comm.m03.design.mapper.DesignSchemeMapper;
import com.comm.m03.design.mapper.SiteMapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 设计数据服务
 * 负责处理设计数据的业务逻辑
 */
@Service
public class DesignService {

    @Autowired
    private DesignSchemeMapper designSchemeMapper;

    @Autowired
    private SiteMapper siteMapper;

    @Autowired
    private ObjectMapper objectMapper;

    /**
     * 保存设计方案
     * @param designData 设计数据
     * @return 方案ID
     */
    @Transactional
    public Long saveDesignScheme(DesignData designData) {
        DesignScheme scheme = new DesignScheme();
        scheme.setProjectId(designData.getProjectId());
        scheme.setSchemeName(designData.getSchemeName());
        scheme.setFrequencyBand(designData.getFrequencyBand());
        scheme.setTowerHeight(designData.getTowerHeight());
        scheme.setGridSize(designData.getGridSize());
        scheme.setTotalSites(designData.getTotalSites());
        scheme.setValidSites(designData.getValidSites());
        scheme.setInvalidSites(designData.getInvalidSites());
        scheme.setAvgRsrp(designData.getAvgRsrp());

        designSchemeMapper.insert(scheme);
        return scheme.getId();
    }

    /**
     * 保存站点数据
     * @param schemeId 方案ID
     * @param sites 站点列表
     */
    @Transactional
    public void saveSites(Long schemeId, List<SiteData> sites) {
        for (SiteData siteData : sites) {
            Site site = new Site();
            site.setSchemeId(schemeId);
            site.setSiteId(siteData.getSiteId());
            site.setSiteName(siteData.getSiteName());
            site.setLongitude(siteData.getLongitude());
            site.setLatitude(siteData.getLatitude());
            site.setTowerHeight(siteData.getTowerHeight());
            site.setSiteType(siteData.getSiteType());
            site.setScenario(siteData.getScenario());
            site.setRsrp(siteData.getRsrp());
            site.setIsValid(siteData.getIsValid() ? 1 : 0);
            site.setInvalidReason(siteData.getInvalidReason());

            siteMapper.insert(site);
        }
    }

    /**
     * 获取设计方案
     * @param projectId 项目ID
     * @return 设计方案
     */
    public DesignScheme getDesignScheme(Long projectId) {
        return designSchemeMapper.selectByProjectId(projectId);
    }

    /**
     * 获取站点数据
     * @param schemeId 方案ID
     * @return 站点列表
     */
    public List<Site> getSites(Long schemeId) {
        return siteMapper.selectBySchemeId(schemeId);
    }

    /**
     * 获取GeoJSON数据
     * @param projectId 项目ID
     * @return GeoJSON字符串
     */
    public String getGeoJson(Long projectId) {
        DesignScheme scheme = designSchemeMapper.selectByProjectId(projectId);
        if (scheme == null) {
            return null;
        }

        List<Site> sites = siteMapper.selectBySchemeId(scheme.getId());

        // 构建GeoJSON
        Map<String, Object> geoJson = new HashMap<>();
        geoJson.put("type", "FeatureCollection");

        // 构建Features
        List<Map<String, Object>> features = new java.util.ArrayList<>();
        for (Site site : sites) {
            Map<String, Object> feature = new HashMap<>();
            feature.put("type", "Feature");

            // Geometry
            Map<String, Object> geometry = new HashMap<>();
            geometry.put("type", "Point");
            geometry.put("coordinates", new double[]{site.getLongitude(), site.getLatitude()});
            feature.put("geometry", geometry);

            // Properties
            Map<String, Object> properties = new HashMap<>();
            properties.put("siteId", site.getSiteId());
            properties.put("siteName", site.getSiteName());
            properties.put("towerHeight", site.getTowerHeight());
            properties.put("siteType", site.getSiteType());
            properties.put("scenario", site.getScenario());
            properties.put("rsrp", site.getRsrp());
            properties.put("isValid", site.getIsValid() == 1);
            feature.put("properties", properties);

            features.add(feature);
        }
        geoJson.put("features", features);

        // Metadata
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("projectId", projectId);
        metadata.put("schemeName", scheme.getSchemeName());
        metadata.put("totalSites", scheme.getTotalSites());
        metadata.put("validSites", scheme.getValidSites());
        metadata.put("invalidSites", scheme.getInvalidSites());
        metadata.put("avgRsrp", scheme.getAvgRsrp());
        geoJson.put("metadata", metadata);

        try {
            return objectMapper.writeValueAsString(geoJson);
        } catch (Exception e) {
            return null;
        }
    }

    /**
     * 删除设计方案
     * @param schemeId 方案ID
     */
    @Transactional
    public void deleteDesignScheme(Long schemeId) {
        // 删除站点数据
        siteMapper.deleteBySchemeId(schemeId);
        // 删除设计方案
        designSchemeMapper.deleteById(schemeId);
    }
}
