"""m02-cad-fusion Python 解析引擎

多源异构工程数据融合（CAD → GIS）：
  parser      —— ezdxf 解析 DXF（R2010+），提取实体几何
  classifier  —— 按 cad_layer_mapping.yml 识别 6 类要素并映射属性（FR-2/FR-3）
  transformer —— pyproj 坐标系转换 + 七参数/四参数（FR-4/FR-5）
  fusion      —— CAD+GIS 融合：GIS 优先 / <5m 去重 / 冲突标记（FR-6/FR-7）
  cli         —— 命令行全链路入口
  server      —— FastAPI HTTP 服务（方案A：Java 经 HTTP 调用）
"""

__version__ = "1.0.0"
