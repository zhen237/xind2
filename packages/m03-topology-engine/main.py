from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Tuple
import math
import json

app = FastAPI(title="拓扑规划引擎", description="通信基站参数化设计微服务")


class DevicePosition(BaseModel):
    device_name: str
    device_type: str
    model_spec: str
    longitude: float
    latitude: float
    altitude: float = 0.0
    azimuth: float = 0.0
    downtilt: float = 0.0
    mount_height: Optional[float] = None
    coverage_radius: Optional[float] = None
    parent_device: Optional[str] = None
    extra_params: Optional[Dict] = None
    position_id: Optional[str] = None


class GeneratedLayout(BaseModel):
    task_id: str
    devices: List[DevicePosition]


class GenerateRequest(BaseModel):
    project_id: Optional[int] = None
    scheme_name: Optional[str] = None
    template_type: Optional[str] = "macro"
    center_longitude: float = 116.4074
    center_latitude: float = 39.9042
    coverage_radius: float = 1000.0
    frequency_band: Optional[str] = "fdd-lte-1800"
    tower_height: float = 30.0
    grid_size: int = 200
    antenna_height: Optional[int] = 25
    sector_count: Optional[int] = 3
    scenario: Optional[str] = "urban"
    site_count: Optional[int] = None


class SiteData(BaseModel):
    site_id: str
    site_name: str
    longitude: float
    latitude: float
    tower_height: float
    site_type: str
    scenario: str
    rsrp: float
    is_valid: bool
    invalid_reason: Optional[str] = None
    devices: List[DevicePosition] = []
    coverage_polygons: List[List[Tuple[float, float]]] = []


class DesignData(BaseModel):
    project_id: Optional[int] = None
    scheme_name: Optional[str] = None
    frequency_band: Optional[str] = None
    tower_height: float
    grid_size: str
    total_sites: int
    valid_sites: int
    invalid_sites: int
    avg_rsrp: float
    sites: List[SiteData]
    layout: Optional[GeneratedLayout] = None


TEMPLATE_CONFIGS = {
    "macro": {
        "name": "标准宏基站(三扇区)",
        "devices": [
            {"type": "tower", "name": "通信铁塔", "model": "TOWER-35M", "quantity": 1, "position_rule": "center", "height": 35},
            {"type": "antenna", "name": "扇区天线", "model": "ANT-1710-2170-65-18i", "quantity": 3, "position_rule": "sector_top", "offset_radius": 1.5, "height": 30, "downtilt": 6, "beamwidth_h": 65, "beamwidth_v": 7, "gain": 18, "parent": "tower"},
            {"type": "rru", "name": "射频拉远单元", "model": "RRU-3942", "quantity": 3, "position_rule": "below_antenna", "offset_z": -2, "parent": "antenna"},
            {"type": "bbu", "name": "基带处理单元", "model": "BBU-5900", "quantity": 1, "position_rule": "cabinet_center"},
            {"type": "power", "name": "电源柜", "model": "PWR-48V-200A", "quantity": 1, "position_rule": "cabinet_west", "offset_x": -3},
            {"type": "transmission", "name": "传输柜", "model": "TRANS-ODF-48", "quantity": 1, "position_rule": "cabinet_east", "offset_x": 5},
        ],
        "topology_rule": "sector_120",
        "default_params": {"antenna_height": 30, "coverage_radius": 500, "frequency": 2100, "sector_count": 3},
    },
    "micro": {
        "name": "微基站(单扇区)",
        "devices": [
            {"type": "antenna", "name": "一体化天线", "model": "ANT-3300-3800-65-15i", "quantity": 1, "position_rule": "center", "height": 6, "downtilt": 4, "beamwidth_h": 65, "gain": 15},
            {"type": "rru", "name": "RRU", "model": "RRU-MICRO-5G", "quantity": 1, "position_rule": "below_antenna", "offset_z": -1, "parent": "antenna"},
            {"type": "bbu", "name": "BBU", "model": "BBU-MICRO", "quantity": 1, "position_rule": "cabinet_center"},
        ],
        "topology_rule": "single_point",
        "default_params": {"antenna_height": 6, "coverage_radius": 200, "frequency": 3500, "sector_count": 1},
    },
    "indoor": {
        "name": "室内分布系统(单层)",
        "devices": [
            {"type": "rru", "name": "信源RRU", "model": "RRU-INDOOR", "quantity": 1, "position_rule": "equipment_room"},
            {"type": "splitter", "name": "功分器", "model": "SPL-2WAY", "quantity": 2, "position_rule": "distributed_calc", "calc_basis": "floor_area", "parent": "rru"},
            {"type": "antenna", "name": "室分天线", "model": "ANT-CEILING-OMNI", "quantity": 8, "position_rule": "grid", "spacing": 15, "height": 3.0, "gain": 3, "parent": "splitter"},
        ],
        "topology_rule": "grid",
        "default_params": {"floor_area": 1000, "ceiling_height": 3.5, "antenna_spacing": 15, "frequency": 2100},
    },
}


def get_frequency_mhz(frequency_band: str) -> float:
    freq_map = {
        "fdd-lte-800": 850,
        "fdd-lte-900": 900,
        "fdd-lte-1800": 1800,
        "tdd-lte-2300": 2300,
        "tdd-lte-2600": 2600,
        "5g-n79": 4900,
        "5g-n41": 2500,
    }
    return freq_map.get(frequency_band.lower(), 2000)


def calculate_okumura_hata_path_loss(frequency_mhz: float, distance_km: float, tx_height_m: float, rx_height_m: float = 1.5, environment: str = "URBAN") -> float:
    if environment == "URBAN":
        if frequency_mhz <= 200:
            a_hr = 8.29 * (math.log10(1.54 * rx_height_m)) ** 2 - 1.1
        else:
            a_hr = 3.2 * (math.log10(11.75 * rx_height_m)) ** 2 - 4.97
    else:
        a_hr = (1.1 * math.log10(frequency_mhz) - 0.7) * rx_height_m - (1.56 * math.log10(frequency_mhz) - 0.8)

    L_urban = (69.55 + 26.16 * math.log10(frequency_mhz) - 13.82 * math.log10(tx_height_m)
               + (44.9 - 6.55 * math.log10(tx_height_m)) * math.log10(max(distance_km, 0.01)) - a_hr)

    if environment == "SUBURBAN":
        L = L_urban - 2 * (math.log10(frequency_mhz / 28)) ** 2 - 5.4
    elif environment == "RURAL":
        L = L_urban - 4.78 * (math.log10(frequency_mhz)) ** 2 + 18.33 * math.log10(frequency_mhz) - 40.94
    else:
        L = L_urban

    return L


def calculate_rsrp(frequency_mhz: float, tower_height: float, distance_km: float = 0.5, tx_power_w: float = 200.0, antenna_gain_dbi: float = 24.0) -> float:
    path_loss = calculate_okumura_hata_path_loss(frequency_mhz, distance_km, tower_height)
    tx_power_dbm = 10 * math.log10(tx_power_w * 1000) if tx_power_w > 0 else 0
    rsrp = tx_power_dbm + antenna_gain_dbi - path_loss - 8.0
    return round(rsrp, 1)


def generate_hex_grid(request: GenerateRequest) -> List[Tuple[float, float]]:
    center_lon = request.center_longitude
    center_lat = request.center_latitude
    radius_m = request.coverage_radius
    grid_size_m = request.grid_size

    grid_size_km = grid_size_m / 1000.0
    radius_km = radius_m / 1000.0

    hex_radius = grid_size_km / math.sqrt(3)
    max_ring = int(math.ceil(radius_km / (2 * hex_radius)))

    centers = []
    centers.append((center_lon, center_lat))

    for ring in range(1, max_ring + 1):
        points_on_ring = 6 * ring
        for i in range(points_on_ring):
            angle = (math.pi / 3) * i - math.pi / 6
            dist = ring * 2 * hex_radius

            dx = dist * math.cos(angle)
            dy = dist * math.sin(angle)

            lat_rad = math.radians(center_lat)
            lon_delta = dx / (111.32 * math.cos(lat_rad))
            lat_delta = dy / 111.32

            new_lon = center_lon + lon_delta
            new_lat = center_lat + lat_delta

            site_dist = math.sqrt(dx * dx + dy * dy)
            if site_dist <= radius_km + 0.1:
                centers.append((round(new_lon, 6), round(new_lat, 6)))

    return centers


def generate_device_positions(template_type: str, site_lon: float, site_lat: float, site_idx: int, request: GenerateRequest) -> List[DevicePosition]:
    template = TEMPLATE_CONFIGS.get(template_type, TEMPLATE_CONFIGS["macro"])
    devices = []
    device_index = 0

    for dev_config in template["devices"]:
        quantity = dev_config.get("quantity", 1)
        for q in range(quantity):
            device_index += 1
            device_name = f"{dev_config['name']}-{site_idx:03d}-{device_index:02d}"
            device_type = dev_config["type"]
            model_spec = dev_config["model"]
            position_rule = dev_config.get("position_rule", "center")

            lon, lat, alt = site_lon, site_lat, 0.0
            azimuth = 0.0
            downtilt = dev_config.get("downtilt", 0.0)
            mount_height = dev_config.get("height")
            coverage_radius = dev_config.get("coverage_radius")

            if position_rule == "center":
                lon, lat = site_lon, site_lat
                alt = mount_height or 0.0

            elif position_rule == "sector_top":
                sector_count = request.sector_count or template["default_params"].get("sector_count", 3)
                if sector_count > 0:
                    azimuth = (360.0 / sector_count) * q
                lon = site_lon + (dev_config.get("offset_radius", 0) / 111320.0) * math.cos(math.radians(azimuth))
                lat = site_lat + (dev_config.get("offset_radius", 0) / 111320.0) * math.sin(math.radians(azimuth))
                alt = mount_height or 0.0

            elif position_rule == "below_antenna":
                alt = (mount_height or 0.0) + dev_config.get("offset_z", -2.0)
                lon, lat = site_lon, site_lat

            elif position_rule == "cabinet_center":
                lon, lat = site_lon, site_lat
                alt = 0.0

            elif position_rule == "cabinet_west":
                lon = site_lon + dev_config.get("offset_x", -3) / 111320.0
                lat = site_lat
                alt = 0.0

            elif position_rule == "cabinet_east":
                lon = site_lon + dev_config.get("offset_x", 5) / 111320.0
                lat = site_lat
                alt = 0.0

            elif position_rule == "equipment_room":
                lon, lat = site_lon, site_lat
                alt = 0.0

            elif position_rule == "grid":
                spacing = dev_config.get("spacing", 15)
                grid_cols = int(math.ceil(math.sqrt(template["default_params"].get("floor_area", 1000)) / spacing))
                grid_rows = int(math.ceil(quantity / grid_cols))
                row_idx = q // grid_cols
                col_idx = q % grid_cols
                lon = site_lon + (col_idx - grid_cols / 2) * spacing / 111320.0
                lat = site_lat + (row_idx - grid_rows / 2) * spacing / 111320.0
                alt = mount_height or 0.0

            extra_params = {k: v for k, v in dev_config.items() if k not in ["type", "name", "model", "quantity", "position_rule", "height", "downtilt", "beamwidth_h", "beamwidth_v", "gain", "offset_radius", "offset_z", "offset_x", "parent"]}

            devices.append(DevicePosition(
                device_name=device_name,
                device_type=device_type,
                model_spec=model_spec,
                longitude=round(lon, 7),
                latitude=round(lat, 7),
                altitude=round(alt, 2),
                azimuth=round(azimuth, 1),
                downtilt=round(downtilt, 1),
                mount_height=round(mount_height, 2) if mount_height else None,
                coverage_radius=coverage_radius,
                parent_device=dev_config.get("parent"),
                extra_params=extra_params if extra_params else None
            ))

    return devices


def generate_sites_with_layout(request: GenerateRequest) -> List[SiteData]:
    grid_points = generate_hex_grid(request)

    if request.site_count and request.site_count > 0:
        grid_points = grid_points[:request.site_count]

    sites = []
    for idx, (lon, lat) in enumerate(grid_points, 1):
        template = TEMPLATE_CONFIGS.get(request.template_type, TEMPLATE_CONFIGS["macro"])
        default_params = template["default_params"]

        frequency_mhz = get_frequency_mhz(request.frequency_band)
        tx_height_m = request.antenna_height or default_params.get("antenna_height", 30)
        rsrp = calculate_rsrp(frequency_mhz, tx_height_m)

        devices = generate_device_positions(request.template_type, lon, lat, idx, request)
        polygons = site_coverage_polygons(request.template_type, lon, lat, request)

        sites.append(SiteData(
            site_id=f"SITE-{idx:04d}",
            site_name=f"基站{idx}",
            longitude=lon,
            latitude=lat,
            tower_height=request.tower_height,
            site_type=request.template_type,
            scenario=request.scenario,
            rsrp=rsrp,
            is_valid=rsrp > -120,
            invalid_reason=None if rsrp > -120 else "RSRP低于阈值",
            devices=devices,
            coverage_polygons=polygons
        ))

    return sites


def generate_coverage_polygon(site_lon: float, site_lat: float, azimuth: float, beamwidth_h: float, coverage_radius_m: float) -> List[Tuple[float, float]]:
    points = []
    num_points = 36

    start_angle = azimuth - beamwidth_h / 2
    end_angle = azimuth + beamwidth_h / 2

    for i in range(num_points + 1):
        angle = start_angle + (end_angle - start_angle) * (i / num_points)
        angle_rad = math.radians(angle)

        dx = (coverage_radius_m / 1000) * math.sin(angle_rad)
        dy = (coverage_radius_m / 1000) * math.cos(angle_rad)

        lat_rad = math.radians(site_lat)
        lon_delta = dx / (111.32 * math.cos(lat_rad))
        lat_delta = dy / 111.32

        points.append((round(site_lon + lon_delta, 7), round(site_lat + lat_delta, 7)))

    return points


def site_coverage_polygons(template_type: str, site_lon: float, site_lat: float, request: GenerateRequest) -> List[List[Tuple[float, float]]]:
    """按模板拓扑规则，为单站生成各扇区的覆盖多边形(坐标环)。

    - sector_120: 三扇区(默认)按 360/sector_count 均分方位角，每扇区一条扇形多边形
    - single_point: 单扇区
    - 其他(如 indoor grid): 以站点为中心画一个 360° 全向覆盖圆
    多边形坐标直接由已有的 generate_coverage_polygon 计算，保证与前端/QGIS 渲染一致。
    """
    template = TEMPLATE_CONFIGS.get(template_type, TEMPLATE_CONFIGS["macro"])
    rule = template.get("topology_rule", "sector_120")
    default = template.get("default_params", {})
    radius = float(default.get("coverage_radius", 500))
    polygons: List[List[Tuple[float, float]]] = []

    if rule == "sector_120":
        sector_count = request.sector_count or default.get("sector_count", 3)
        beamwidth = 65.0
        for i in range(sector_count):
            az = (360.0 / sector_count) * i
            polygons.append(generate_coverage_polygon(site_lon, site_lat, az, beamwidth, radius))
    elif rule == "single_point":
        polygons.append(generate_coverage_polygon(site_lon, site_lat, 0.0, 65.0, radius))
    else:
        # indoor grid / 其他：以站点为中心画一个覆盖圆（360° 全向）
        polygons.append(generate_coverage_polygon(site_lon, site_lat, 0.0, 360.0, radius))
    return polygons


@app.post("/generate", response_model=DesignData, summary="参数化生成设计方案")
async def generate_design(request: GenerateRequest):
    try:
        sites = generate_sites_with_layout(request)

        total_sites = len(sites)
        valid_sites = sum(1 for s in sites if s.is_valid)
        invalid_sites = total_sites - valid_sites
        avg_rsrp = round(sum(s.rsrp for s in sites) / total_sites, 2) if total_sites > 0 else 0.0

        all_devices = []
        for site in sites:
            for device in site.devices:
                device.position_id = f"{site.site_id}-{device.device_name}"
                all_devices.append(device)

        layout = GeneratedLayout(task_id=f"TASK-{request.project_id or '000'}", devices=all_devices)

        return DesignData(
            project_id=request.project_id,
            scheme_name=request.scheme_name,
            frequency_band=request.frequency_band,
            tower_height=request.tower_height,
            grid_size=str(request.grid_size),
            total_sites=total_sites,
            valid_sites=valid_sites,
            invalid_sites=invalid_sites,
            avg_rsrp=avg_rsrp,
            sites=sites,
            layout=layout
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@app.post("/generate_layout", response_model=GeneratedLayout, summary="生成设备布局")
async def generate_layout(request: GenerateRequest):
    try:
        sites = generate_sites_with_layout(request)

        all_devices = []
        for site in sites:
            for device in site.devices:
                device.position_id = f"{site.site_id}-{device.device_name}"
                all_devices.append(device)

        return GeneratedLayout(task_id=f"TASK-{request.project_id or '000'}", devices=all_devices)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@app.get("/templates", summary="获取所有模板配置")
async def get_templates():
    return TEMPLATE_CONFIGS


@app.get("/template/{template_type}", summary="获取指定模板配置")
async def get_template(template_type: str):
    template = TEMPLATE_CONFIGS.get(template_type)
    if not template:
        raise HTTPException(status_code=404, detail=f"模板 {template_type} 不存在")
    return template


@app.get("/coverage_polygon", summary="生成覆盖多边形")
async def get_coverage_polygon(site_lon: float, site_lat: float, azimuth: float = 0.0, beamwidth_h: float = 65.0, coverage_radius_m: float = 500.0):
    polygon = generate_coverage_polygon(site_lon, site_lat, azimuth, beamwidth_h, coverage_radius_m)
    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [polygon]
        },
        "properties": {
            "siteLocation": [site_lon, site_lat],
            "azimuth": azimuth,
            "beamwidth": beamwidth_h,
            "radius": coverage_radius_m
        }
    }


@app.get("/health", summary="健康检查")
async def health_check():
    return {"status": "ok", "service": "topology-engine"}


if __name__ == "__main__":
    import uvicorn
    # 仅监听本机回环：拓扑引擎只供同机 M03 后端(localhost:9001)调用，
    # 不暴露公网，避免开放 9001 端口与鉴权问题。
    uvicorn.run(app, host="127.0.0.1", port=9001)