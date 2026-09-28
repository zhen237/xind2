# -*- coding: utf-8 -*-
"""字段取值兼容层（dict 与对象两种形态）。

背景
----
设计引擎里"站点/机房"这类实体的取值存在两种数据形态：

1. **dict**：``design_dock`` 的 ``self.generated_sites`` 是 dict 列表，
   元素形如 ``{'site_id': 'BTS-001', 'name': '演示基站1', ...}``；
2. **对象**：``self.machine_rooms`` 是 ``models.room.MachineRoom`` 实例列表。

图册导出（``layout_export``）早期一律用 ``getattr(obj, key, default)`` 取值，
而 ``getattr(dict_instance, 'name', '')`` **不会报错**，会静默返回默认值
——于是真实传入的 dict 站点，站名恒为"基站"、塔型恒为"MONOPOLE"、
塔高恒为 35.0m，用户真实数据被悄悄丢弃。

本模块提供 **零外部依赖**（不 import qgis / PyQt / 任何第三方库）的
``field()``，统一按对象真实类型取值，使上述两种形态都能拿到正确结果。
放在独立模块里的目的：**可脱离 QGIS 环境直接单测**。

语义（务必逐条对齐测试）
----------------------
- ``obj`` 为 dict（含其子类）  → 走 ``obj.get(key, default)``；
- 其它对象                    → 走 ``getattr(obj, key, default)``；
- ``obj is None``             → 直接返回 ``default``（不抛错）；
- **dict 中键存在但值为 None** → 返回 ``None``（按"取到了 None"处理，
  不把 None 视为缺失再去取 ``default``）——这是 ``dict.get`` 的天然语义，
  也是与旧 ``getattr`` 行为一致的地方，测试需覆盖。
"""

from __future__ import annotations

from typing import Any, Mapping

__all__ = ["field"]


def field(obj: Any, key: str, default: Any = None) -> Any:
    """兼容 dict 与对象取字段。

    Args:
        obj: 取值来源，可为 dict / Mapping 子类、任意对象，或 ``None``。
        key: 字段名 / 字典键。
        default: 取不到时返回的默认值。

    Returns:
        命中时返回真实值；未命中（或 ``obj is None``）返回 ``default``。
        dict 命中但值为 ``None`` 时返回 ``None``（不当缺失处理）。

    Examples:
        >>> field({"name": "基站A"}, "name")
        '基站A'
        >>> field({"name": "基站A"}, "missing", "默认")
        '默认'
        >>> field({"name": None}, "name", "默认") is None
        True
        >>> field(None, "name", "默认")
        '默认'
    """
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)
