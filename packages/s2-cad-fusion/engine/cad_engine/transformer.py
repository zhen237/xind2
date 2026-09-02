"""坐标系转换（FR-4 / FR-5）

支持三类坐标系互转并统一归一到 WGS84：
  - WGS84   (EPSG:4326)
  - CGCS2000(EPSG:4490，地理坐标) / CGCS2000 高斯投影（3度带）
  - 地方坐标系（CAD 本地平面坐标）

转换手段：
  - pyproj EPSG/自定义投影（常规投影换算）
  - 七参数（Helmert，地心平移+旋转+缩放）—— pyproj pipeline
  - 四参数（平面相似变换：平移+旋转+缩放），可由控制点对最小二乘求解
"""

import json

from pyproj import CRS, Transformer

# 预置坐标系别名 → pyproj 定义
CRS_ALIASES = {
    "wgs84": "EPSG:4326",
    "EPSG:4326": "EPSG:4326",
    "cgcs2000": "EPSG:4490",
    "EPSG:4490": "EPSG:4490",
    # CGCS2000 / 3-degree Gauss-Kruger CM 111E（运城区域常用）
    "cgcs2000_gk111": "+proj=tmerc +lat_0=0 +lon_0=111 +k=1 "
                      "+x_0=500000 +y_0=0 +ellps=GRS80 +units=m +no_defs",
    # CGCS2000 / 3-degree Gauss-Kruger CM 114E
    "cgcs2000_gk114": "+proj=tmerc +lat_0=0 +lon_0=114 +k=1 "
                      "+x_0=500000 +y_0=0 +ellps=GRS80 +units=m +no_defs",
}


def resolve_crs(name):
    """把别名 / EPSG:xxxx / +proj=... 统一解析为 pyproj CRS。"""
    if name in CRS_ALIASES:
        return CRS.from_string(CRS_ALIASES[name])
    if isinstance(name, str) and (name.startswith("+proj=")
                                  or name.upper().startswith("EPSG:")):
        return CRS.from_string(name)
    raise ValueError(f"无法识别的坐标系: {name!r}（支持: wgs84/cgcs2000/"
                     f"cgcs2000_gk111/cgcs2000_gk114/EPSG:xxxx/+proj=...）")


class SevenParam:
    """布尔莎七参数（Helmert position_vector 约定，单位: m / 角秒 / ppm）。

    dx, dy, dz —— 平移（米）
    rx, ry, rz —— 旋转（角秒）
    s          —— 尺度（ppm）
    source/target_ellps —— 源/目标椭球（默认 GRS80 ↔ WGS84）
    """

    def __init__(self, dx=0.0, dy=0.0, dz=0.0, rx=0.0, ry=0.0, rz=0.0,
                 s=0.0, source_ellps="GRS80", target_ellps="WGS84"):
        self.params = dict(dx=dx, dy=dy, dz=dz, rx=rx, ry=ry, rz=rz, s=s)
        self.pipeline = (
            "+proj=pipeline "
            f"+step +proj=cart +ellps={source_ellps} "
            f"+step +proj=helmert +x={dx} +y={dy} +z={dz} "
            f"+rx={rx} +ry={ry} +rz={rz} +s={s} "
            "+convention=position_vector "
            f"+step +proj=cart +inv +ellps={target_ellps}"
        )
        self._transformer = Transformer.from_pipeline(self.pipeline)

    def transform(self, lon, lat):
        return self._transformer.transform(lon, lat)

    @classmethod
    def from_json(cls, obj):
        if isinstance(obj, str):
            obj = json.loads(obj)
        allowed = {"dx", "dy", "dz", "rx", "ry", "rz", "s",
                   "source_ellps", "target_ellps"}
        return cls(**{k: v for k, v in obj.items() if k in allowed})


class FourParam:
    """平面四参数（二维相似变换）：x' = a·x − b·y + dx, y' = b·x + a·y + dy。

    a = k·cosθ, b = k·sinθ（k 为尺度，θ 为旋转角）。
    支持直接给参数，或由 ≥2 对控制点最小二乘求解。
    """

    def __init__(self, a=1.0, b=0.0, dx=0.0, dy=0.0):
        self.a, self.b, self.dx, self.dy = a, b, dx, dy

    # ---------- 最小二乘 ----------
    def estimate(cls_points):
        """由控制点对 [(x1,y1, X1,Y1), ...] 最小二乘求解四参数。"""
        n = len(cls_points)
        if n < 2:
            raise ValueError("四参数求解至少需要 2 对控制点")
        # 线性方程：X = a·x − b·y + dx ; Y = b·x + a·y + dy
        # 未知数 [a, b, dx, dy]，对每个点写两行
        import math
        A, B = [], []
        for (x, y, X, Y) in cls_points:
            A.append([x, -y, 1, 0]); B.append(X)
            A.append([y, x, 0, 1]); B.append(Y)
        # 正规方程 (AᵗA)u = AᵗB
        m = 4
        ata = [[0.0] * m for _ in range(m)]
        atb = [0.0] * m
        for row, rhs in zip(A, B):
            for i in range(m):
                atb[i] += row[i] * rhs
                for j in range(m):
                    ata[i][j] += row[i] * row[j]
        # 高斯消元
        for i in range(m):
            piv = max(range(i, m), key=lambda r: abs(ata[r][i]))
            if abs(ata[piv][i]) < 1e-12:
                raise ValueError("控制点共线或重合，无法求解四参数")
            ata[i], ata[piv] = ata[piv], ata[i]
            atb[i], atb[piv] = atb[piv], atb[i]
            for r in range(i + 1, m):
                f = ata[r][i] / ata[i][i]
                for c in range(i, m):
                    ata[r][c] -= f * ata[i][c]
                atb[r] -= f * atb[i]
        u = [0.0] * m
        for i in range(m - 1, -1, -1):
            u[i] = (atb[i] - sum(ata[i][c] * u[c] for c in range(i + 1, m))) / ata[i][i]
        return FourParam(a=u[0], b=u[1], dx=u[2], dy=u[3])

    estimate = classmethod(estimate)

    def apply(self, x, y):
        return (self.a * x - self.b * y + self.dx,
                self.b * x + self.a * y + self.dy)

    @property
    def scale(self):
        return (self.a ** 2 + self.b ** 2) ** 0.5

    @property
    def rotation_deg(self):
        import math
        return math.degrees(math.atan2(self.b, self.a))

    def to_dict(self):
        return {"a": self.a, "b": self.b, "dx": self.dx, "dy": self.dy,
                "scale": self.scale, "rotation_deg": self.rotation_deg}

    @classmethod
    def from_json(cls, obj):
        if isinstance(obj, str):
            obj = json.loads(obj)
        if "points" in obj:  # 控制点形式 [{"local":[x,y],"national":[X,Y]},...]
            pts = [(p["local"][0], p["local"][1],
                    p["national"][0], p["national"][1]) for p in obj["points"]]
            return cls.estimate(pts)
        allowed = {"a", "b", "dx", "dy"}
        return cls(**{k: v for k, v in obj.items() if k in allowed})


class CoordinateTransformer:
    """坐标转换门面。

    典型链路（FR-5）：
      地方系 --四参数--> CGCS2000 高斯面 --pyproj--> WGS84 经纬度 --七参数--> 目标基准
    """

    def __init__(self, source="cgcs2000_gk111", target="EPSG:4326",
                 seven_param=None, four_param=None):
        self.source = source
        self.target = target
        self.seven_param = seven_param
        self.four_param = four_param
        if source != "local" and target != "local":
            src, dst = resolve_crs(source), resolve_crs(target)
            self._proj = Transformer.from_crs(src, dst, always_xy=True)
        else:
            self._proj = None

    def transform_point(self, x, y):
        """单点转换，返回 (lon_or_x, lat_or_y)。"""
        # ① 地方系 → 国家坐标系：先做四参数
        if self.source == "local":
            if self.four_param is None:
                raise ValueError("源为地方坐标系（local）时必须提供四参数 "
                                 "（four_param 或控制点）")
            x, y = self.four_param.apply(x, y)
            # 四参数后进入 CGCS2000 高斯面
            gk = Transformer.from_crs(
                resolve_crs("cgcs2000_gk111"), resolve_crs("EPSG:4326"),
                always_xy=True)
            x, y = gk.transform(x, y)
            if self.target == "EPSG:4326" or self.target == "wgs84":
                if self.seven_param:
                    x, y = self.seven_param.transform(x, y)
                return x, y
            src, dst = resolve_crs("EPSG:4326"), resolve_crs(self.target)
            return Transformer.from_crs(src, dst, always_xy=True).transform(x, y)

        # ② 常规投影转换
        if self._proj is None:
            raise ValueError("非法坐标系组合")
        lon, lat = self._proj.transform(x, y)
        # ③ 需要七参数精化（源为 CGCS2000、目标 WGS84）
        if self.seven_param and _is_geographic_lonlat(lon, lat):
            lon, lat = self.seven_param.transform(lon, lat)
        return lon, lat

    def transform_points(self, points):
        return [self.transform_point(x, y) for (x, y) in points]


def _is_geographic_lonlat(x, y):
    return -360 < x < 360 and -90 < y < 90
