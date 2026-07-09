"""底图加载工具 — 支持高德卫星图、OSM等

关键：QGIS的XYZ连接URI中，URL里的 & 必须用 %26 编码，
否则QGIS会把它当作连接参数分隔符导致加载失败。
"""

from qgis.core import (
    QgsProject, QgsRasterLayer, QgsCoordinateReferenceSystem,
    QgsSettings,
)


# 高德卫星图 - URL中 & 已编码为 %26
GAODE_TILE_URL = (
    "https://webst02.is.autonavi.com/appmaptile?"
    "style=6%26x={x}%26y={y}%26z={z}"
)

GAODE_URI = (
    "type=xyz"
    "&zmin=3&zmax=18"
    f"&url={GAODE_TILE_URL}"
)

OSM_URI = (
    "type=xyz"
    "&zmin=0&zmax=19"
    "&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png"
)


def _write_xyz_settings(name, tile_url, zmin=0, zmax=18):
    """将XYZ连接写入QGIS设置（用户在GUI里也能看到）"""
    settings = QgsSettings()
    base_key = f"qgis/connections-xyz/{name}"
    settings.setValue(f"{base_key}/url", tile_url)
    settings.setValue(f"{base_key}/zmin", str(zmin))
    settings.setValue(f"{base_key}/zmax", str(zmax))


def add_basemap(uri, name, crs_epsg="EPSG:3857"):
    """添加底图图层（先移除旧同名图层避免叠加）"""
    project = QgsProject.instance()
    for old in project.mapLayersByName(name):
        project.removeMapLayer(old)

    layer = QgsRasterLayer(uri, name, "wms")
    if not layer.isValid():
        err = layer.error().message()
        return False, f"图层 '{name}' 加载失败: {err}"
    if crs_epsg:
        layer.setCrs(QgsCoordinateReferenceSystem(crs_epsg))
    QgsProject.instance().addMapLayer(layer)
    return True, f"'{name}' 已添加"


def add_gaode_satellite():
    """添加高德卫星底图（国内可用，无需VPN）"""
    # 同时写入QGIS设置，用户可在 图层→添加XYZ图层 中手动选择
    _write_xyz_settings(
        "高德卫星",
        "https://webst02.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}",
        zmin=3, zmax=18
    )
    return add_basemap(GAODE_URI, "高德卫星图")


def add_osm():
    """添加OpenStreetMap底图"""
    _write_xyz_settings(
        "OpenStreetMap",
        "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        zmin=0, zmax=19
    )
    return add_basemap(OSM_URI, "OpenStreetMap")
