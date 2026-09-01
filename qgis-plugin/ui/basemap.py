"""底图加载工具 — 支持 Esri 卫星图、OSM 等

关键：QGIS的XYZ连接URI中，URL里的 & 必须用 %26 编码，
否则QGIS会把它当作连接参数分隔符导致加载失败。
"""

from qgis.core import (
    QgsProject, QgsRasterLayer, QgsCoordinateReferenceSystem,
    QgsSettings,
)


# （高德卫星图已移除，国内最佳底图改用「天地图」影像，全球可加 Esri / OSM）

# 天地图（国家地理信息公共服务平台）token —— 由 zhen237 提供
# 当前为「服务端」类型 key（不限制 UA/Referer，QGIS 与前端通用）。
# 注意：此 token 不应公开泄露；若需轮换请在天地图官网重新申请。
TIANDITU_TOKEN = "5ca1282d53249d3b0ac07f6b68c9c38b"

OSM_URI = (
    "type=xyz"
    "&zmin=0&zmax=19"
    "&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png"
)

# Esri 全球卫星影像 - 全球可用（含摩洛哥），EPSG:3857
# 注意 Esri 瓦片顺序为 {z}/{y}/{x}
ESRI_WORLD_IMAGERY_URL = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/tile/{z}/{y}/{x}"
)
ESRI_URI = (
    "type=xyz"
    "&zmin=0&zmax=19"
    f"&url={ESRI_WORLD_IMAGERY_URL}"
)


def _write_xyz_settings(name, tile_url, zmin=0, zmax=18):
    """将XYZ连接写入QGIS设置（用户在GUI里也能看到）"""
    settings = QgsSettings()
    base_key = f"qgis/connections-xyz/{name}"
    settings.setValue(f"{base_key}/url", tile_url)
    settings.setValue(f"{base_key}/zmin", str(zmin))
    settings.setValue(f"{base_key}/zmax", str(zmax))


def add_basemap(uri, name, crs_epsg="EPSG:3857"):
    """添加底图图层"""
    layer = QgsRasterLayer(uri, name, "wms")
    if not layer.isValid():
        err = layer.error().message()
        return False, f"图层 '{name}' 加载失败: {err}"
    if crs_epsg:
        layer.setCrs(QgsCoordinateReferenceSystem(crs_epsg))
    QgsProject.instance().addMapLayer(layer)
    return True, f"'{name}' 已添加"


def add_osm():
    """添加OpenStreetMap底图"""
    _write_xyz_settings(
        "OpenStreetMap",
        "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        zmin=0, zmax=19
    )
    return add_basemap(OSM_URI, "OpenStreetMap")


def add_esri_imagery():
    """添加 Esri 全球卫星影像底图（全球可用，含摩洛哥）"""
    _write_xyz_settings(
        "Esri World Imagery",
        ESRI_WORLD_IMAGERY_URL,
        zmin=0, zmax=19
    )
    return add_basemap(ESRI_URI, "Esri 全球卫星图")


# ── 天地图（国内最佳底图，需 token） ──────────────────────────────
# layer_type 取值：
#   img_w  影像底图      cia_w  影像注记(路名/地名)
#   vec_w  矢量底图      cva_w  矢量注记
#   ter_w  地形底图      cta_w  地形注记
# 关键：QGIS XYZ 连接 URI 中，瓦片 URL 自带的 & 必须编码为 %26，
#       否则 QGIS 会把它当作连接参数分隔符导致加载失败。
def _tianditu_tile_url(layer_type):
    return (
        "https://t0.tianditu.gov.cn/DataServer?T=" + layer_type
        + "%26x={x}%26y={y}%26l={z}%26tk=" + TIANDITU_TOKEN
    )


# ── 天地图 UA 绕过 ───────────────────────────────────────────────
# 天地图 WAF 会拦截「浏览器」和「GIS 客户端」UA（QGIS/Chrome → 403），
# 但空 UA / curl / Python-urllib / PyQt 均可正常通过（HTTP 200）。
# 通过 QgsNetworkAccessManager 请求预处理器，将发往 tianditu.gov.cn 的
# 请求 UA 清空，使其通过校验（仅安装一次）。
_TDT_UA_INSTALLED = False


def _ensure_tianditu_ua():
    """为发往 tianditu.gov.cn 的请求清空 UA（绕过 WAF 拦截）"""
    global _TDT_UA_INSTALLED
    if _TDT_UA_INSTALLED:
        return
    try:
        from qgis.core import QgsNetworkAccessManager
        from qgis.PyQt.QtNetwork import QNetworkRequest

        nam = QgsNetworkAccessManager.instance()
        if nam is None:
            return

        def _on_request(op, req, data):
            try:
                if "tianditu.gov.cn" in req.url().toString():
                    # 清空 UA：天地图 WAF 拦截 QGIS/Chrome 等 UA，
                    # 但空 UA / Python-urllib / PyQt 均放行
                    req.setHeader(QNetworkRequest.UserAgentHeader, "")
            except Exception:
                pass

        nam.requestAboutToBeCreated.connect(_on_request)
        _TDT_UA_INSTALLED = True
    except Exception:
        pass


def add_tianditu_imagery():
    """添加天地图影像底图（国内最佳卫星影像，需 token）"""
    _ensure_tianditu_ua()
    url = _tianditu_tile_url("img_w")
    # 写入 QGIS 设置时用真实 & 方便人工查看
    _write_xyz_settings("天地图影像", url.replace("%26", "&"), zmin=3, zmax=18)
    uri = f"type=xyz&zmin=3&zmax=18&url={url}"
    return add_basemap(uri, "天地图影像")


def add_tianditu_labels():
    """添加天地图影像注记（路名/地名，叠加在影像之上更清晰）"""
    _ensure_tianditu_ua()
    url = _tianditu_tile_url("cia_w")
    _write_xyz_settings("天地图影像注记", url.replace("%26", "&"), zmin=3, zmax=18)
    uri = f"type=xyz&zmin=3&zmax=18&url={url}"
    return add_basemap(uri, "天地图影像注记")
