package com.comm.m03.design.service;

import com.comm.common.BusinessException;
import com.comm.m03.design.entity.DesignData;
import com.comm.m03.design.entity.DesignScheme;
import com.comm.m03.design.entity.GenerateRequest;
import com.comm.m03.design.entity.Site;
import com.comm.m03.design.entity.SiteData;
import com.comm.m03.design.entity.ParametricTemplate;
import com.comm.m03.design.entity.DesignTask;
import com.comm.m03.design.entity.GeneratedLayout;
import com.comm.m03.design.mapper.DesignSchemeMapper;
import com.comm.m03.design.mapper.SiteMapper;
import com.comm.m03.design.mapper.ParametricTemplateMapper;
import com.comm.m03.design.mapper.DesignTaskMapper;
import com.comm.m03.design.mapper.GeneratedLayoutMapper;
import com.comm.m03.design.client.TopologyEngineClient;
import com.comm.m03.design.entity.TopologyGenerateResponse;
import com.comm.m03.design.entity.TopologySiteData;
import com.comm.m03.design.entity.TopologyDevicePosition;
import com.comm.m03.design.entity.DevicePositionData;
import com.comm.m03.entity.Project;
import com.comm.m03.mapper.ProjectMapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
public class DesignService {

    private static final Logger log = LoggerFactory.getLogger(DesignService.class);

    // ── 默认值常量 ──────────────────────────────────────────────
    static final BigDecimal DEFAULT_CENTER_LON = BigDecimal.valueOf(116.4074);
    static final BigDecimal DEFAULT_CENTER_LAT = BigDecimal.valueOf(39.9042);
    static final BigDecimal DEFAULT_COVERAGE_RADIUS = BigDecimal.valueOf(1000);
    static final BigDecimal DEFAULT_TOWER_HEIGHT = BigDecimal.valueOf(30);
    static final int DEFAULT_GRID_SIZE = 200;
    static final double DEFAULT_FREQUENCY_MHZ = 2000;
    static final double DEFAULT_DISTANCE_KM = 0.5;
    static final double MOBILE_HEIGHT_M = 1.5;
    static final double RSRP_CONSTANT = 43;
    static final double RSRP_VALID_THRESHOLD = -120;
    static final double GRID_SIZE_FALLBACK = 200;
    static final String DEFAULT_SCENARIO = "urban";
    static final String DEFAULT_TEMPLATE_TYPE = "macro";
    static final int SCALE_PRECISION = 6;
    static final int RSRP_DECIMAL_PLACES = 1;
    static final int AVG_RSRP_SCALE = 2;

    // ── 设计任务状态常量 ─────────────────────────────────────────
    public static final String TASK_STATUS_DRAFT = "draft";
    public static final String TASK_STATUS_GENERATING = "generating";
    public static final String TASK_STATUS_COMPLETED = "completed";
    public static final String TASK_STATUS_FAILED = "failed";

    // ── 设备类型常量 ─────────────────────────────────────────────
    static final String DEVICE_TYPE_SITE = "site";

    @Autowired
    private DesignSchemeMapper designSchemeMapper;

    @Autowired
    private SiteMapper siteMapper;

    @Autowired
    private ParametricTemplateMapper templateMapper;

    @Autowired
    private DesignTaskMapper taskMapper;

    @Autowired
    private GeneratedLayoutMapper layoutMapper;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private ProjectMapper projectMapper;

    @Autowired
    private TopologyEngineClient topologyEngineClient;

    // ========================================================================
    //  设计方案管理
    // ========================================================================

    @Transactional
    @CacheEvict(value = "designSchemes", key = "#designData.projectId")
    public Long saveDesignScheme(DesignData designData) {
        // 确保 projectId 对应的 Project 记录存在（QGIS 插件同步时可能未创建）
        // 注意: m03_project.status 实际为 INT 列, 此处不写字符串(避免 'active' 写入 INT 报错),
        // 交由列默认值/NULL 处理; 若需语义状态应在 hyiene 阶段统一 entity 与 DB 类型。
        Long projectId = designData.getProjectId();
        if (projectId != null && projectMapper.selectById(projectId) == null) {
            Project project = new Project();
            project.setId(projectId);
            project.setProjectName(designData.getSchemeName() != null ? designData.getSchemeName() : "QGIS同步项目");
            project.setProjectCode("QGIS-" + projectId);
            project.setStatus(null);
            project.setCreateTime(LocalDateTime.now());
            project.setUpdateTime(LocalDateTime.now());
            projectMapper.insert(project);
            log.info("自动创建 Project 记录: id={}, name={}", projectId, project.getProjectName());
        }

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

        // 从 QGIS 同步的机房数据中提取主机房位置（取第一个机房作为汇聚点）
        List<Map<String, Object>> rooms = designData.getMachineRooms();
        if (rooms != null && !rooms.isEmpty()) {
            Map<String, Object> mainRoom = rooms.get(0);
            Object lon = mainRoom.get("longitude");
            Object lat = mainRoom.get("latitude");
            Object name = mainRoom.get("name");
            if (lon != null && lat != null) {
                scheme.setRoomLongitude(new BigDecimal(lon.toString()));
                scheme.setRoomLatitude(new BigDecimal(lat.toString()));
                scheme.setRoomName(name != null ? name.toString() : "机房1");
                log.info("保存机房位置: {} ({}, {})", name, lon, lat);
            }
        }

        // 从 QGIS 同步的管线路由类型（direct / manhattan）
        String routeType = designData.getRouteType();
        if (routeType != null && !routeType.isEmpty()) {
            scheme.setRouteType(routeType);
            log.info("保存管线路由类型: {}", routeType);
        }

        // 上传幂等键：重复上传同一键时，下游 uploadDesignFull 据此返回已存在方案
        if (designData.getIdempotencyKey() != null && !designData.getIdempotencyKey().isEmpty()) {
            scheme.setIdempotencyKey(designData.getIdempotencyKey());
        }

        designSchemeMapper.insert(scheme);
        return scheme.getId();
    }

    @Transactional
    public void saveSites(Long schemeId, List<SiteData> sites) {
        if (sites == null) return;
        for (SiteData siteData : sites) {
            saveSite(schemeId, siteData);
        }
    }

    /**
     * 原子化上传设计方案：单事务内写方案 + 全部站点，杜绝"方案已建但站点缺失"的孤儿方案。
     * 幂等：若 DesignData.idempotencyKey 已存在，直接返回已建方案，不重复写入（防网络重试翻倍）。
     * 正确性：对每站做经纬度/RSRP 范围校验，越界站点跳过并计入 errors；落库后与入参 totalSites 对账。
     * 返回明细供 QGIS 插件校验回环使用。
     */
    @Transactional
    public Map<String, Object> uploadDesignFull(DesignData designData) {
        Map<String, Object> result = new HashMap<>();
        String idem = designData.getIdempotencyKey();
        if (idem != null && !idem.trim().isEmpty()) {
            DesignScheme existing = designSchemeMapper.selectByIdempotencyKey(idem.trim());
            if (existing != null) {
                result.put("schemeId", existing.getId());
                result.put("dup", true);
                result.put("received", designData.getSites() == null ? 0 : designData.getSites().size());
                result.put("inserted", existing.getTotalSites() == null ? 0 : existing.getTotalSites());
                result.put("skipped", 0);
                result.put("errors", new ArrayList<String>());
                return result;
            }
        }

        // saveDesignScheme 与本方法同处一个事务（REQUIRED 加入外层事务）
        Long schemeId = saveDesignScheme(designData);

        List<String> errors = new ArrayList<>();
        int received = designData.getSites() == null ? 0 : designData.getSites().size();
        int inserted = 0;
        int skipped = 0;
        if (designData.getSites() != null) {
            for (SiteData sd : designData.getSites()) {
                if (!isSiteInRange(sd, errors)) {
                    skipped++;
                    continue;
                }
                persistSite(schemeId, sd, "simulated");
                inserted++;
            }
        }

        // 落库后计数对账：入参 totalSites 应与 入库+跳过 一致
        Integer total = designData.getTotalSites();
        if (total != null && total != inserted + skipped) {
            log.warn("上传计数对账不一致: 入参totalSites={}, 实际入库={}, 跳过={}", total, inserted, skipped);
        }

        result.put("schemeId", schemeId);
        result.put("dup", false);
        result.put("received", received);
        result.put("inserted", inserted);
        result.put("skipped", skipped);
        result.put("errors", errors);
        return result;
    }

    /**
     * 站点经纬度/RSRP 合理性校验。越界站点不入库，错误信息计入 errors。
     * 经纬度限定中国陆域大致范围；RSRP 缺省不校验，存在时须在 [-140, 0] dBm。
     */
    private boolean isSiteInRange(SiteData sd, List<String> errors) {
        BigDecimal lon = sd.getLongitude();
        BigDecimal lat = sd.getLatitude();
        String sid = sd.getSiteId() == null ? "(未知)" : sd.getSiteId();
        if (lon == null || lat == null) {
            errors.add("站点 " + sid + ": 经纬度缺失");
            return false;
        }
        if (lon.doubleValue() < 73 || lon.doubleValue() > 135) {
            errors.add("站点 " + sid + ": 经度 " + lon + " 超出中国范围[73,135]");
            return false;
        }
        if (lat.doubleValue() < 3 || lat.doubleValue() > 54) {
            errors.add("站点 " + sid + ": 纬度 " + lat + " 超出中国范围[3,54]");
            return false;
        }
        BigDecimal rsrp = sd.getRsrp();
        if (rsrp != null && (rsrp.doubleValue() < -140 || rsrp.doubleValue() > 0)) {
            errors.add("站点 " + sid + ": RSRP " + rsrp + " 超出合理范围[-140,0] dBm");
            return false;
        }
        return true;
    }

    @Transactional
    public void saveSite(Long schemeId, SiteData siteData) {
        persistSite(schemeId, siteData, "simulated");
    }

    @Transactional
    public void saveMeasuredSites(Long schemeId, List<SiteData> sites) {
        if (sites == null) return;
        for (SiteData siteData : sites) {
            persistSite(schemeId, siteData, "measured");
        }
    }

    /**
     * 落库单个站点，并标记 RSRP 来源。
     * simulated=模型仿真(拓扑引擎/本地 Okumura-Hata); measured=实测/现场勘测。
     * 引擎路径与本地路径生成的站点均经 saveSite -> 此处标记 simulated。
     */
    private void persistSite(Long schemeId, SiteData siteData, String rsrpSource) {
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
        site.setRsrpSource(rsrpSource);
        site.setIsValid(siteData.getIsValid() != null && siteData.getIsValid() ? 1 : 0);
        site.setInvalidReason(siteData.getInvalidReason());

        siteMapper.insert(site);
    }

    /**
     * 导入实测站点(CSV)。解析后全部标记为 measured 落库。
     * 解析逻辑抽为静态方法 parseMeasuredCsv，便于无 DB 单元测试。
     */
    public int importMeasuredSitesCsv(Long schemeId, MultipartFile file) throws IOException {
        if (file == null || file.isEmpty()) {
            throw new BusinessException(400, "CSV 文件为空");
        }
        List<SiteData> sites = parseMeasuredCsv(
                new InputStreamReader(file.getInputStream(), StandardCharsets.UTF_8));
        saveMeasuredSites(schemeId, sites);
        return sites.size();
    }

    /**
     * 解析实测站点 CSV(包级可见，供单元测试直接调用)。
     * 列: site_id,site_name,longitude,latitude,tower_height,site_type,scenario,rsrp
     * 必填: longitude, latitude, rsrp。
     */
    static List<SiteData> parseMeasuredCsv(java.io.Reader reader) throws IOException {
        List<SiteData> sites = new ArrayList<>();
        try (BufferedReader br = new BufferedReader(reader)) {
            String header = br.readLine();
            if (header == null) return sites;
            String[] cols = header.split(",");
            Map<String, Integer> idx = new HashMap<>();
            for (int i = 0; i < cols.length; i++) {
                idx.put(cols[i].trim().toLowerCase(), i);
            }
            if (!idx.containsKey("longitude") || !idx.containsKey("latitude") || !idx.containsKey("rsrp")) {
                throw new BusinessException(400, "CSV 必须包含 longitude, latitude, rsrp 列");
            }
            String line;
            int n = 0;
            while ((line = br.readLine()) != null) {
                line = line.trim();
                if (line.isEmpty()) continue;
                String[] values = line.split(",");
                n++;
                SiteData sd = new SiteData();
                sd.setSiteId(cell(idx, values, "site_id", "SITE-M" + String.format("%04d", n)));
                sd.setSiteName(cell(idx, values, "site_name", "实测基站" + n));
                sd.setLongitude(toDecimal(cell(idx, values, "longitude", "")));
                sd.setLatitude(toDecimal(cell(idx, values, "latitude", "")));
                sd.setTowerHeight(toDecimal(cell(idx, values, "tower_height", "")));
                sd.setSiteType(cell(idx, values, "site_type", "macro"));
                sd.setScenario(cell(idx, values, "scenario", "urban"));
                BigDecimal rsrp = toDecimal(cell(idx, values, "rsrp", ""));
                sd.setRsrp(rsrp);
                sd.setIsValid(rsrp != null && rsrp.doubleValue() > RSRP_VALID_THRESHOLD);
                sites.add(sd);
            }
        }
        return sites;
    }

    private static String cell(Map<String, Integer> idx, String[] values, String key, String fallback) {
        Integer i = idx.get(key);
        if (i == null || i >= values.length) return fallback;
        String v = values[i].trim();
        return v.isEmpty() ? fallback : v;
    }

    private static BigDecimal toDecimal(String v) {
        if (v == null || v.trim().isEmpty()) return null;
        try {
            return new BigDecimal(v.trim());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    @Cacheable(value = "designSchemes", key = "#projectId", unless = "#result == null")
    public DesignScheme getDesignScheme(Long projectId) {
        return designSchemeMapper.selectByProjectId(projectId);
    }

    public List<Site> getSites(Long schemeId) {
        return siteMapper.selectBySchemeId(schemeId);
    }

    public String getGeoJson(Long projectId) {
        DesignScheme scheme = designSchemeMapper.selectByProjectId(projectId);
        if (scheme == null) {
            throw new BusinessException(404, "未找到设计方案");
        }

        List<Site> sites = siteMapper.selectBySchemeId(scheme.getId());

        Map<String, Object> geoJson = new HashMap<>();
        geoJson.put("type", "FeatureCollection");

        List<Map<String, Object>> features = new ArrayList<>();
        for (Site site : sites) {
            Map<String, Object> feature = new HashMap<>();
            feature.put("type", "Feature");

            Map<String, Object> geometry = new HashMap<>();
            geometry.put("type", "Point");
            // 防御性空值检查
            BigDecimal lon = site.getLongitude();
            BigDecimal lat = site.getLatitude();
            geometry.put("coordinates", new double[]{
                    lon != null ? lon.doubleValue() : 0,
                    lat != null ? lat.doubleValue() : 0
            });
            feature.put("geometry", geometry);

            Map<String, Object> properties = new HashMap<>();
            properties.put("siteId", site.getSiteId());
            properties.put("siteName", site.getSiteName());
            properties.put("towerHeight", site.getTowerHeight());
            properties.put("siteType", site.getSiteType());
            properties.put("scenario", site.getScenario());
            properties.put("rsrp", site.getRsrp());
            properties.put("rsrpSource", site.getRsrpSource());
            properties.put("isValid", site.getIsValid() != null && site.getIsValid() == 1);
            feature.put("properties", properties);

            features.add(feature);
        }
        geoJson.put("features", features);

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
            log.error("GeoJSON序列化失败: projectId={}", projectId, e);
            throw new BusinessException("GeoJSON生成失败");
        }
    }

    @Transactional
    public void deleteDesignScheme(Long schemeId) {
        siteMapper.deleteBySchemeId(schemeId);
        designSchemeMapper.deleteById(schemeId);
    }

    // ========================================================================
    //  自动设计生成（六边形网格 + Okumura-Hata RSRP）
    // ========================================================================

    /**
     * 自动设计生成：主路径委托 Python 拓扑引擎，失败回退本地算法。
     * T4：先按 templateType 解析参数化模板，用其 default_params 补全缺失参数，
     * 生成后用其 devices_json 展开"模板定义设备清单"（模板为设备权威来源）。
     */
    public DesignData generateDesign(GenerateRequest request) {
        ParametricTemplate template = resolveTemplate(request);
        if (template != null) {
            applyTemplateDefaults(request, template);
            log.info("已应用参数化模板联动: category={}, templateId={}",
                    request.getTemplateType(), template.getId());
        }

        DesignData designData;
        try {
            TopologyGenerateResponse resp = topologyEngineClient.generate(request);
            if (resp != null && resp.getSites() != null && !resp.getSites().isEmpty()) {
                log.info("设计生成由拓扑引擎(Python)完成: projectId={}", request.getProjectId());
                designData = mapFromEngine(resp, request);
            } else {
                designData = generateDesignLocal(request);
            }
        } catch (Exception e) {
            log.warn("拓扑引擎调用失败, 回退本地算法: projectId={}, err={}", request.getProjectId(), e.getMessage());
            designData = generateDesignLocal(request);
        }

        // T4：设备拓扑来源策略
        // - 若设计已由 Python 拓扑引擎生成（resp 含真实 deviceLayout），【保留】引擎产物，不再覆盖；
        //   （引擎侧的模板逻辑已产出铁塔/天线/RRU/BBU/电源/传输全套设备位姿）
        // - 仅当本地回退算法未产出设备清单(deviceLayout == null)且存在参数化模板时，
        //   才用 M03 模板展开作为兜底（满足 AC-2 模板定义设备清单）。
        if (template != null && designData.getDeviceLayout() == null && designData.getSites() != null) {
            List<DevicePositionData> devices = new ArrayList<>();
            for (SiteData site : designData.getSites()) {
                devices.addAll(expandTemplateDevices(template, site));
            }
            designData.setDeviceLayout(devices);
            if (designData.getSchemeName() == null || designData.getSchemeName().isBlank()) {
                designData.setSchemeName(template.getName());
            }
        }

        return designData;
    }

    /**
     * 本地生成算法（兜底）：六边形网格 + Okumura-Hata RSRP
     */
    private DesignData generateDesignLocal(GenerateRequest request) {
        DesignData designData = new DesignData();
        designData.setProjectId(request.getProjectId());
        designData.setSchemeName(request.getSchemeName());
        designData.setFrequencyBand(request.getFrequencyBand());
        designData.setTowerHeight(request.getTowerHeight());
        designData.setGridSize(request.getGridSize() != null ? request.getGridSize().toString() : String.valueOf(DEFAULT_GRID_SIZE));

        List<SiteData> sites = generateHexGridSites(request);
        designData.setSites(sites);
        designData.setTotalSites(sites.size());

        int validCount = 0;
        BigDecimal totalRsrp = BigDecimal.ZERO;
        for (SiteData site : sites) {
            if (site.getIsValid() != null && site.getIsValid()) {
                validCount++;
            }
            if (site.getRsrp() != null) {
                totalRsrp = totalRsrp.add(site.getRsrp());
            }
        }
        designData.setValidSites(validCount);
        designData.setInvalidSites(sites.size() - validCount);
        if (sites.size() > 0) {
            designData.setAvgRsrp(totalRsrp.divide(BigDecimal.valueOf(sites.size()), AVG_RSRP_SCALE, RoundingMode.HALF_UP));
        } else {
            designData.setAvgRsrp(BigDecimal.ZERO);
        }

        return designData;
    }

    // ========================================================================
    //  参数化模板联动（T4）：/generate 真正消费 m03_parametric_template
    // ========================================================================

    /**
     * 按 category(templateType) 解析当前生效的模板；无则返回 null
     */
    private ParametricTemplate resolveTemplate(GenerateRequest request) {
        String category = request.getTemplateType();
        if (category == null || category.isBlank()) {
            return null;
        }
        List<ParametricTemplate> list = templateMapper.selectList(
                new QueryWrapper<ParametricTemplate>().eq("category", category).eq("is_active", 1));
        return list.isEmpty() ? null : list.get(0);
    }

    /**
     * 用模板 default_params 补全请求中缺失的可选参数（塔高/网格/场景/天线高度/扇区数）。
     * 已显式提供的参数不被覆盖（模板作为默认值，而非强制覆盖）。
     */
    private void applyTemplateDefaults(GenerateRequest request, ParametricTemplate template) {
        String paramsJson = template.getDefaultParams();
        if (paramsJson == null || paramsJson.isBlank()) {
            return;
        }
        try {
            Map<String, Object> params = objectMapper.readValue(paramsJson, Map.class);
            if (request.getTowerHeight() == null && params.containsKey("antenna_height")) {
                request.setTowerHeight(toBigDecimal(params.get("antenna_height")));
            }
            if (request.getGridSize() == null && params.containsKey("grid_size")) {
                request.setGridSize(((Number) params.get("grid_size")).intValue());
            }
            if (request.getScenario() == null) {
                // coverage_type: outdoor/indoor → 统一采用 Okumura-Hata 城市模型
                request.setScenario("urban");
            }
            if (request.getAntennaHeight() == null && params.containsKey("antenna_height")) {
                request.setAntennaHeight(((Number) params.get("antenna_height")).intValue());
            }
            if (request.getSectorCount() == null && params.containsKey("sector_count")) {
                request.setSectorCount(((Number) params.get("sector_count")).intValue());
            }
        } catch (Exception e) {
            log.warn("模板 default_params 解析失败, 跳过模板联动: templateId={}, err={}",
                    template.getId(), e.getMessage());
        }
    }

    private BigDecimal toBigDecimal(Object o) {
        if (o == null) {
            return null;
        }
        if (o instanceof Number) {
            return BigDecimal.valueOf(((Number) o).doubleValue());
        }
        try {
            return new BigDecimal(o.toString());
        } catch (Exception e) {
            return null;
        }
    }

    /**
     * 依据模板 devices_json 为单个站点展开设备拓扑（T4 核心：结果含模板定义设备清单）。
     * 复用 T2 的 DevicePositionData 落库结构。多数量设备按扇区/序号分布。
     */
    private List<DevicePositionData> expandTemplateDevices(ParametricTemplate template, SiteData site) {
        List<DevicePositionData> result = new ArrayList<>();
        String devicesJson = template.getDevicesJson();
        if (devicesJson == null || devicesJson.isBlank()) {
            return result;
        }

        double siteLon = site.getLongitude() != null ? site.getLongitude().doubleValue() : 0;
        double siteLat = site.getLatitude() != null ? site.getLatitude().doubleValue() : 0;
        double latRad = Math.toRadians(siteLat);
        double metersPerDegLon = 111320.0 * Math.cos(latRad);

        try {
            Map<String, Object> root = objectMapper.readValue(devicesJson, Map.class);
            Object devicesObj = root.get("devices");
            if (!(devicesObj instanceof List)) {
                return result;
            }
            for (Object devObj : (List<?>) devicesObj) {
                Map<String, Object> dev = (Map<String, Object>) devObj;
                int quantity = dev.get("quantity") != null ? ((Number) dev.get("quantity")).intValue() : 1;
                String type = (String) dev.get("type");
                String name = (String) dev.get("name");
                String model = (String) dev.get("model");
                double offsetX = dev.get("offset_x") != null ? ((Number) dev.get("offset_x")).doubleValue() : 0.0;
                Double height = dev.get("height") != null ? ((Number) dev.get("height")).doubleValue() : null;
                double downtilt = dev.get("downtilt") != null ? ((Number) dev.get("downtilt")).doubleValue() : 0.0;
                String parent = (String) dev.get("parent");

                double baseLon = siteLon + offsetX / metersPerDegLon;

                for (int i = 0; i < quantity; i++) {
                    double azimuth = quantity > 1 ? i * (360.0 / quantity) : 0.0;
                    DevicePositionData d = new DevicePositionData();
                    d.setDeviceName(name + (quantity > 1 ? "-" + (i + 1) : ""));
                    d.setDeviceType(type);
                    d.setModelSpec(model);
                    d.setLongitude(BigDecimal.valueOf(Math.round(baseLon * 1e6) / 1e6));
                    d.setLatitude(BigDecimal.valueOf(Math.round(siteLat * 1e6) / 1e6));
                    d.setAltitude(height != null ? BigDecimal.valueOf(height) : null);
                    d.setMountHeight(height != null ? BigDecimal.valueOf(height) : null);
                    d.setAzimuth(BigDecimal.valueOf(azimuth));
                    d.setDowntilt(BigDecimal.valueOf(downtilt));
                    d.setCoverageRadius(site.getTowerHeight());
                    d.setParentDevice(parent);
                    d.setPositionId(type + "-" + (i + 1));
                    result.add(d);
                }
            }
        } catch (Exception e) {
            log.warn("模板 devices_json 解析失败: templateId={}, err={}", template.getId(), e.getMessage());
        }
        return result;
    }

    /**
     * 将 Python 拓扑引擎响应映射为 M03 DesignData（含设备拓扑 deviceLayout）
     */
    private DesignData mapFromEngine(TopologyGenerateResponse resp, GenerateRequest request) {
        DesignData designData = new DesignData();
        designData.setProjectId(request.getProjectId());
        designData.setSchemeName(request.getSchemeName());
        designData.setFrequencyBand(request.getFrequencyBand());
        designData.setTowerHeight(request.getTowerHeight());
        designData.setGridSize(resp.getGridSize());

        List<SiteData> sites = new ArrayList<>();
        List<DevicePositionData> deviceLayout = new ArrayList<>();
        for (TopologySiteData ts : resp.getSites()) {
            SiteData site = new SiteData();
            site.setSiteId(ts.getSiteId());
            site.setSiteName(ts.getSiteName());
            site.setLongitude(ts.getLongitude());
            site.setLatitude(ts.getLatitude());
            site.setTowerHeight(ts.getTowerHeight());
            site.setSiteType(ts.getSiteType());
            site.setScenario(ts.getScenario());
            site.setRsrp(ts.getRsrp());
            site.setIsValid(ts.getIsValid());
            site.setInvalidReason(ts.getInvalidReason());
            site.setCoveragePolygons(ts.getCoveragePolygons());
            sites.add(site);
            if (ts.getDevices() != null) {
                for (TopologyDevicePosition dp : ts.getDevices()) {
                    deviceLayout.add(mapDevice(dp));
                }
            }
        }
        designData.setSites(sites);
        designData.setTotalSites(resp.getTotalSites());
        designData.setValidSites(resp.getValidSites());
        designData.setInvalidSites(resp.getInvalidSites());
        designData.setAvgRsrp(resp.getAvgRsrp());
        designData.setDeviceLayout(deviceLayout);
        return designData;
    }

    private DevicePositionData mapDevice(TopologyDevicePosition dp) {
        DevicePositionData d = new DevicePositionData();
        d.setDeviceName(dp.getDeviceName());
        d.setDeviceType(dp.getDeviceType());
        d.setModelSpec(dp.getModelSpec());
        d.setLongitude(dp.getLongitude());
        d.setLatitude(dp.getLatitude());
        d.setAltitude(dp.getAltitude());
        d.setAzimuth(dp.getAzimuth());
        d.setDowntilt(dp.getDowntilt());
        d.setMountHeight(dp.getMountHeight());
        d.setCoverageRadius(dp.getCoverageRadius());
        d.setParentDevice(dp.getParentDevice());
        d.setPositionId(dp.getPositionId());
        d.setExtraParams(dp.getExtraParams());
        return d;
    }

    private List<SiteData> generateHexGridSites(GenerateRequest request) {
        List<SiteData> sites = new ArrayList<>();

        BigDecimal centerLon = request.getCenterLongitude();
        BigDecimal centerLat = request.getCenterLatitude();
        BigDecimal radius = request.getCoverageRadius();
        int gridSize = request.getGridSize() != null ? request.getGridSize() : DEFAULT_GRID_SIZE;

        if (centerLon == null || centerLat == null) {
            centerLon = DEFAULT_CENTER_LON;
            centerLat = DEFAULT_CENTER_LAT;
        }
        if (radius == null) {
            radius = DEFAULT_COVERAGE_RADIUS;
        }

        double gridSizeKm = gridSize / 1000.0;
        double radiusKm = radius.doubleValue() / 1000.0;
        double hexRadius = gridSizeKm / Math.sqrt(3);
        int maxRing = (int) Math.ceil(radiusKm / (2 * hexRadius));

        int siteNum = 1;
        sites.add(createSite(siteNum++, centerLon, centerLat, request));

        for (int ring = 1; ring <= maxRing; ring++) {
            int pointsOnRing = 6 * ring;
            for (int i = 0; i < pointsOnRing; i++) {
                double angle = (Math.PI / 3) * i - Math.PI / 6;
                double dist = ring * 2 * hexRadius;

                double dx = dist * Math.cos(angle);
                double dy = dist * Math.sin(angle);

                double latRad = centerLat.doubleValue() * Math.PI / 180;
                double lonDelta = dx / (111.32 * Math.cos(latRad));
                double latDelta = dy / 111.32;

                BigDecimal newLon = BigDecimal.valueOf(centerLon.doubleValue() + lonDelta);
                BigDecimal newLat = BigDecimal.valueOf(centerLat.doubleValue() + latDelta);

                double siteDist = Math.sqrt(dx * dx + dy * dy);
                if (siteDist <= radiusKm + 0.1) {
                    sites.add(createSite(siteNum++, newLon, newLat, request));
                }
            }
        }

        // 限制最大生成站点数：网格过密（如 gridSize=20m）会生成数万站点，
        // 前端需为每个站点创建 5 个 Cesium 实体，一次性渲染会卡崩浏览器。
        final int MAX_GENERATED_SITES = 500;
        if (sites.size() > MAX_GENERATED_SITES) {
            sites = new ArrayList<>(sites.subList(0, MAX_GENERATED_SITES));
        }

        return sites;
    }

    private SiteData createSite(int siteNum, BigDecimal lon, BigDecimal lat, GenerateRequest request) {
        SiteData site = new SiteData();
        site.setSiteId("SITE-" + String.format("%04d", siteNum));
        site.setSiteName("基站" + siteNum);
        site.setLongitude(BigDecimal.valueOf(Math.round(lon.doubleValue() * Math.pow(10, SCALE_PRECISION)) / Math.pow(10, SCALE_PRECISION)));
        site.setLatitude(BigDecimal.valueOf(Math.round(lat.doubleValue() * Math.pow(10, SCALE_PRECISION)) / Math.pow(10, SCALE_PRECISION)));
        site.setTowerHeight(request.getTowerHeight() != null ? request.getTowerHeight() : DEFAULT_TOWER_HEIGHT);
        site.setSiteType(request.getTemplateType() != null ? request.getTemplateType() : DEFAULT_TEMPLATE_TYPE);
        site.setScenario(request.getScenario() != null ? request.getScenario() : DEFAULT_SCENARIO);

        BigDecimal rsrp = calculateRsrp(request, site.getTowerHeight());
        site.setRsrp(rsrp);
        site.setIsValid(rsrp != null && rsrp.doubleValue() > RSRP_VALID_THRESHOLD);

        return site;
    }

    /**
     * 纯函数：Okumura-Hata 路径损耗计算（包级可见，供单元测试直接调用，无需 Spring 容器）
     * 与 Python 拓扑引擎 calculate_okumura_hata_path_loss 公式一致（URBAN 场景），
     * 两者共享同一权威基准：f=900MHz, hb=30m, hm=1.5m, d=1km, 城区 → 路径损耗 ≈ 126.4 dB。
     */
    static double computePathLossDb(double frequencyMHz, double distanceKm, double txHeightM, double rxHeightM, String scenario) {
        // 移动台天线高度修正因子 a(hr)
        double aHr;
        if (frequencyMHz <= 200) {
            aHr = 8.29 * Math.pow(Math.log10(1.54 * rxHeightM), 2) - 1.1;
        } else {
            aHr = 3.2 * Math.pow(Math.log10(11.75 * rxHeightM), 2) - 4.97;
        }

        // Okumura-Hata 城市路径损耗
        double lUrban = 69.55 + 26.16 * Math.log10(frequencyMHz) - 13.82 * Math.log10(txHeightM)
                + (44.9 - 6.55 * Math.log10(txHeightM)) * Math.log10(Math.max(distanceKm, 0.01))
                - aHr;

        // 环境修正
        String env = scenario != null ? scenario.toLowerCase() : DEFAULT_SCENARIO;
        double pathLoss;
        switch (env) {
            case "suburban":
                pathLoss = lUrban - 2 * Math.pow(Math.log10(frequencyMHz / 28.0), 2) - 5.4;
                break;
            case "rural":
                pathLoss = lUrban - 4.78 * Math.pow(Math.log10(frequencyMHz), 2)
                        + 18.33 * Math.log10(frequencyMHz) - 40.94;
                break;
            default: // urban
                pathLoss = lUrban;
                break;
        }
        return pathLoss;
    }

    /**
     * Okumura-Hata传播模型计算RSRP（含urban/suburban/rural环境修正）
     */
    BigDecimal calculateRsrp(GenerateRequest request, BigDecimal towerHeight) {
        try {
            double frequency = getFrequencyMHz(request.getFrequencyBand());
            double hBase = towerHeight != null ? towerHeight.doubleValue() : DEFAULT_TOWER_HEIGHT.doubleValue();

            double pathLoss = computePathLossDb(frequency, DEFAULT_DISTANCE_KM, hBase, MOBILE_HEIGHT_M,
                    request.getScenario() != null ? request.getScenario() : DEFAULT_SCENARIO);

            double rsrp = -pathLoss + RSRP_CONSTANT;
            return BigDecimal.valueOf(Math.round(rsrp * Math.pow(10, RSRP_DECIMAL_PLACES)) / Math.pow(10, RSRP_DECIMAL_PLACES));
        } catch (Exception e) {
            log.warn("RSRP计算异常, 使用默认值: freqBand={}, height={}", request.getFrequencyBand(), towerHeight, e);
            return BigDecimal.valueOf(-95);
        }
    }

    private double getFrequencyMHz(String frequencyBand) {
        if (frequencyBand == null) return DEFAULT_FREQUENCY_MHZ;
        switch (frequencyBand.toLowerCase()) {
            case "fdd-lte-800":  return 850;
            case "fdd-lte-900":  return 900;
            case "fdd-lte-1800": return 1800;
            case "tdd-lte-2300": return 2300;
            case "tdd-lte-2600": return 2600;
            case "5g-n79":       return 4900;
            case "5g-n41":       return 2500;
            default:             return DEFAULT_FREQUENCY_MHZ;
        }
    }

    // ========================================================================
    //  参数化模板管理
    // ========================================================================

    @Cacheable(value = "templates")
    public List<ParametricTemplate> getTemplates() {
        return templateMapper.selectList(null);
    }

    @Cacheable(value = "templates", key = "#templateId")
    public ParametricTemplate getTemplate(Long templateId) {
        return templateMapper.selectById(templateId);
    }

    @Transactional
    @CacheEvict(value = "templates", allEntries = true)
    public void createTemplate(ParametricTemplate template) {
        template.setIsActive(1);
        LocalDateTime now = LocalDateTime.now();
        template.setCreatedAt(now);
        template.setUpdatedAt(now);
        templateMapper.insert(template);
    }

    @Transactional
    @CacheEvict(value = "templates", allEntries = true)
    public void updateTemplate(ParametricTemplate template) {
        template.setUpdatedAt(LocalDateTime.now());
        templateMapper.updateById(template);
    }

    @Transactional
    @CacheEvict(value = "templates", allEntries = true)
    public void deleteTemplate(Long templateId) {
        templateMapper.deleteById(templateId);
    }

    // ========================================================================
    //  设计任务管理
    // ========================================================================

    @Transactional
    public void createDesignTask(DesignTask task) {
        if (task.getTaskNo() == null || task.getTaskNo().isBlank()) {
            task.setTaskNo("DT-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase());
        }
        if (task.getStatus() == null || task.getStatus().isBlank()) {
            task.setStatus(TASK_STATUS_DRAFT);
        }
        LocalDateTime now = LocalDateTime.now();
        task.setCreatedAt(now);
        task.setUpdatedAt(now);
        taskMapper.insert(task);
    }

    public List<DesignTask> getDesignTasks(String status) {
        if (status == null || status.isBlank()) {
            return taskMapper.selectList(null);
        }
        return taskMapper.selectByStatus(status);
    }

    public DesignTask getDesignTask(Long taskId) {
        return taskMapper.selectById(taskId);
    }

    @Transactional
    public void updateTaskStatus(Long taskId, String status) {
        DesignTask task = taskMapper.selectById(taskId);
        if (task == null) {
            throw new BusinessException(404, "任务不存在");
        }
        task.setStatus(status);
        task.setUpdatedAt(LocalDateTime.now());
        taskMapper.updateById(task);
    }

    @Transactional
    public void deleteDesignTask(Long taskId) {
        layoutMapper.deleteByTaskId(taskId);
        taskMapper.deleteById(taskId);
    }

    @Transactional
    public DesignData executeDesignTask(Long taskId) {
        DesignTask task = taskMapper.selectById(taskId);
        if (task == null) {
            throw new BusinessException(404, "任务不存在");
        }

        if (task.getParamsJson() == null || task.getParamsJson().isBlank()) {
            throw new BusinessException(400, "任务参数为空，无法执行");
        }

        task.setStatus(TASK_STATUS_GENERATING);
        task.setUpdatedAt(LocalDateTime.now());
        taskMapper.updateById(task);

        try {
            GenerateRequest request = objectMapper.readValue(task.getParamsJson(), GenerateRequest.class);
            DesignData designData = generateDesign(request);

            task.setResultJson(objectMapper.writeValueAsString(designData));
            task.setStatus(TASK_STATUS_COMPLETED);
            task.setUpdatedAt(LocalDateTime.now());
            taskMapper.updateById(task);

            saveLayout(taskId, designData);

            return designData;
        } catch (BusinessException e) {
            task.setStatus(TASK_STATUS_FAILED);
            task.setUpdatedAt(LocalDateTime.now());
            taskMapper.updateById(task);
            throw e;
        } catch (Exception e) {
            log.error("任务执行失败: taskId={}", taskId, e);
            task.setStatus(TASK_STATUS_FAILED);
            task.setUpdatedAt(LocalDateTime.now());
            taskMapper.updateById(task);
            throw new BusinessException(500, "任务执行失败，请稍后重试", e);
        }
    }

    // ========================================================================
    //  生成布局
    // ========================================================================

    @Transactional
    public void saveLayout(Long taskId, DesignData designData) {
        layoutMapper.deleteByTaskId(taskId);

        if (designData.getSites() == null || designData.getSites().isEmpty()) return;

        int sortOrder = 0;
        for (SiteData site : designData.getSites()) {
            GeneratedLayout layout = new GeneratedLayout();
            layout.setTaskId(taskId);
            layout.setDeviceName(site.getSiteName());
            layout.setDeviceType(DEVICE_TYPE_SITE);
            layout.setModelSpec(site.getSiteType());
            layout.setLongitude(site.getLongitude() != null ? site.getLongitude().doubleValue() : 0);
            layout.setLatitude(site.getLatitude() != null ? site.getLatitude().doubleValue() : 0);
            layout.setAltitude(site.getTowerHeight() != null ? site.getTowerHeight().doubleValue() : 0);
            layout.setMountHeight(site.getTowerHeight() != null ? site.getTowerHeight().doubleValue() : null);
            layout.setCoverageRadius(parseGridSizeSafely(designData.getGridSize()));
            layout.setSortOrder(sortOrder++);
            layoutMapper.insert(layout);
        }

        // 设备拓扑（来自 Python 拓扑引擎）：落库到 m03_generated_layout
        List<DevicePositionData> devices = designData.getDeviceLayout();
        if (devices != null) {
            for (DevicePositionData dev : devices) {
                GeneratedLayout layout = new GeneratedLayout();
                layout.setTaskId(taskId);
                layout.setDeviceName(dev.getDeviceName());
                layout.setDeviceType(dev.getDeviceType());
                layout.setModelSpec(dev.getModelSpec());
                layout.setLongitude(dev.getLongitude() != null ? dev.getLongitude().doubleValue() : 0);
                layout.setLatitude(dev.getLatitude() != null ? dev.getLatitude().doubleValue() : 0);
                layout.setAltitude(dev.getAltitude() != null ? dev.getAltitude().doubleValue() : 0);
                layout.setAzimuth(dev.getAzimuth() != null ? dev.getAzimuth().doubleValue() : null);
                layout.setDowntilt(dev.getDowntilt() != null ? dev.getDowntilt().doubleValue() : null);
                layout.setMountHeight(dev.getMountHeight() != null ? dev.getMountHeight().doubleValue() : null);
                layout.setCoverageRadius(dev.getCoverageRadius() != null ? dev.getCoverageRadius().doubleValue() : null);
                layout.setParentDevice(dev.getParentDevice());
                layout.setSortOrder(sortOrder++);
                layoutMapper.insert(layout);
            }
        }
    }

    private double parseGridSizeSafely(String gridSizeStr) {
        if (gridSizeStr == null || gridSizeStr.isBlank()) {
            return GRID_SIZE_FALLBACK;
        }
        try {
            return Double.parseDouble(gridSizeStr);
        } catch (NumberFormatException e) {
            log.warn("网格大小解析失败, 使用默认值: input={}", gridSizeStr);
            return GRID_SIZE_FALLBACK;
        }
    }
}
