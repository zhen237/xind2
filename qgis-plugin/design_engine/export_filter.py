# -*- coding: utf-8 -*-
"""导出需排除的诊断图层口径（单一事实来源）。

背景
----
「补盲补热」诊断会产生两个**真矢量图层**（名字固定，带中点）：

- ``诊断·弱覆盖区``
- ``诊断·建议补站``

它们是**诊断结论层**，口径与交付图纸不同：交付图纸（PDF/PNG/CAD）要的是
「现状 + 设计成果」，若把诊断层一并导出，橙色弱区块、三角形建议站会与真实
站点蓝点在**同一位置打架**，图纸无法交付。

因此约定：**标准图纸（PDF/PNG）与 CAD（DXF/DWG）导出时，统一排除名字以
``诊断·`` 开头的图层**。

注意（行为边界）
----------------
- **图册不走本口径**：``_export_standard_drawset`` → ``create_standard_engineering_sheet``
  是纯矢量 SVG 重绘，完全不读工程图层，天然不受影响，本模块不参与。
- **「覆盖热力图」不归本模块管**：它在 PDF 里本来就排除（既有行为，保持不变），
  在 CAD 里本来就**不排除**（既有行为，保持不变）。本模块**只**负责 ``诊断·`` 前缀层。

本模块**零 QGIS 依赖**（不 import qgis / qgis.core / PyQt），因此可脱离 QGIS
环境直接单测。
"""

from __future__ import annotations

__all__ = ["DIAGNOSIS_LAYER_PREFIX", "is_diagnosis_layer"]

# 诊断结论图层统一前缀（含中点「·」）。导出 PDF/CAD 时排除以此开头的图层。
DIAGNOSIS_LAYER_PREFIX = "诊断·"


def is_diagnosis_layer(layer_name) -> bool:
    """判断图层名是否属于「导出需排除的诊断图层」。

    Args:
        layer_name: 图层名称。**非字符串（含 None/bytes/数字/列表等）与空串一律返回
            False**，绝不抛异常 —— 谓词应当是全域的。

    Returns:
        当 ``layer_name`` 为非空字符串且以 :data:`DIAGNOSIS_LAYER_PREFIX` 开头时
        返回 ``True``，否则 ``False``（含非字符串输入）。

    Examples:
        >>> is_diagnosis_layer("诊断·弱覆盖区")
        True
        >>> is_diagnosis_layer("诊断·建议补站")
        True
        >>> is_diagnosis_layer("基站设计")
        False
        >>> is_diagnosis_layer("诊断弱覆盖区")   # 缺中点，不算诊断层
        False
        >>> is_diagnosis_layer(None)
        False
        >>> is_diagnosis_layer(123)
        False
    """
    if not isinstance(layer_name, str) or not layer_name:
        return False
    return layer_name.startswith(DIAGNOSIS_LAYER_PREFIX)
