# -*- coding: utf-8 -*-
"""
FTTH 数据模型与拓扑装配 (model.py)
===================================

把 8 图层原始记录(截断字段名 dict)封装为 FtthProject，并提供拓扑查询:
  - 按 CODE 索引各图层
  - upstream_chain(box): 从某箱体经 CABLE_AMON 向上追溯光缆链直到 PM 根节点
  - imbs_by_boite(code): 查某箱体下挂的住户(IMB)
  - pm_code: 推断 PM/NRO 根节点编码

所有字段访问走原始截断名 (见 field_map.LAYER_FIELDS)，保持与 .dbf 一致。
"""

from __future__ import annotations


class FtthProject:
    """一份 FTTH 竣工/设计数据集的内存模型。"""

    def __init__(self):
        self.imbs: dict[str, dict] = {}
        self.sites: dict[str, dict] = {}
        self.boites: dict[str, dict] = {}
        self.cables: dict[str, dict] = {}
        self.ptechs: dict[str, dict] = {}
        self.infras: dict[str, dict] = {}
        self.znro: dict[str, dict] = {}
        self.zpm: dict[str, dict] = {}
        self.source = ""          # 数据集来源目录/名称
        self._pm_code: str | None = None
        self._adj: dict | None = None  # 光缆邻接表(懒构建)

    # ---- 装载 (由 loader 调用) ----
    def add_records(self, layer: str, rows: list[dict]) -> None:
        store = {
            "IMB": self.imbs, "SITE": self.sites, "BOITE": self.boites,
            "CABLE": self.cables, "PTECH": self.ptechs,
            "INFRASTRUCTURE": self.infras, "ZNRO": self.znro, "ZPM": self.zpm,
        }[layer]
        for r in rows:
            code = (r.get("CODE") or "").strip()
            if code:
                store[code] = r

    # ---- 索引查询 ----
    def get_boite(self, code: str) -> dict | None:
        return self.boites.get(code)

    def get_cable(self, code: str) -> dict | None:
        return self.cables.get(code)

    def imbs_by_boite(self, boite_code: str) -> list[dict]:
        return [r for r in self.imbs.values() if (r.get("BPE_CODE") or "").strip() == boite_code]

    @property
    def pm_code(self) -> str | None:
        """推断 PM/NRO 根节点: 优先 ZPM.CODE，否则取任意 CABLE.REF_PM。"""
        if self._pm_code is None:
            if self.zpm:
                self._pm_code = next(iter(self.zpm.keys()))
            else:
                for c in self.cables.values():
                    rp = (c.get("REF_PM") or "").strip()
                    if rp:
                        self._pm_code = rp
                        break
        return self._pm_code

    def _is_root(self, box_code: str) -> bool:
        """box 是否为 PM/NRO 根节点 (站点或 ZPM 编码)。"""
        return box_code in self.sites or box_code in self.zpm

    def _build_adjacency(self) -> None:
        """构建 箱体<->光缆 邻接表: box -> [(cable_code, other_box), ...]。"""
        if self._adj is not None:
            return
        adj: dict[str, list] = {}
        for code, c in self.cables.items():
            o = (c.get("ORIGINE") or "").strip()
            e = (c.get("EXTREMITE") or "").strip()
            if o and e:
                adj.setdefault(o, []).append((code, e))
                adj.setdefault(e, []).append((code, o))
        self._adj = adj

    def upstream_chain(self, start_box_code: str) -> list[tuple[str, str, str]]:
        """
        从 start_box 沿光缆邻接(ORIGINE/EXTREMITE)向上 BFS 追溯至 PM/NRO 根节点，
        返回该箱体到根节点的唯一路径上各段 [(cable_code, from_box, to_box), ...]。

        说明: 真实数据里 BOITE.CABLE_AMON 常指向不存在的电缆编码(命名体系不一致)，
        故 v1 采用 CABLE 邻接关系做 BFS，更稳定。FTTH 为树状层级，路径唯一。
        """
        self._build_adjacency()
        start = (start_box_code or "").strip()
        if not start:
            return []
        roots = set(self.sites.keys()) | ({self.pm_code} if self.pm_code else set())
        # BFS 从 start 找最近根节点
        from collections import deque
        q = deque([start])
        visited: dict[str, tuple] = {start: None}  # node -> (prev_box, cable)
        parent: dict[str, tuple] = {}
        found = None
        while q:
            cur = q.popleft()
            if cur in roots and cur != start:
                found = cur
                break
            for cable_code, nxt in self._adj.get(cur, []):
                if nxt not in visited:
                    visited[nxt] = (cur, cable_code)
                    parent[nxt] = (cur, cable_code)
                    q.append(nxt)
        if found is None:
            return []
        # 回溯路径 boxes: start -> ... -> found
        path_boxes = [found]
        node = found
        while node != start:
            prev, _cab = parent[node]
            path_boxes.append(prev)
            node = prev
        path_boxes.reverse()  # [start, ..., found]
        chain: list[tuple[str, str, str]] = []
        for i in range(len(path_boxes) - 1):
            a, b = path_boxes[i], path_boxes[i + 1]
            cab = None
            for cc, nxt in self._adj.get(a, []):
                if nxt == b:
                    cab = cc
                    break
            chain.append((cab, a, b))
        return chain

    def route_for_boite(self, boite_code: str) -> dict | None:
        """
        计算某箱体(作为 Destination)的光纤路由骨架:
          pm, destination, total_length, hops[ (cable, to_box, length, cas), ... ]
        cas: PASSAGE=过路箱, EPISSURE=终端熔接, ABONNE=到用户(终段)
        返回 None 表示该箱体不存在。
        """
        if boite_code not in self.boites:
            return None
        pm = self.pm_code or ""
        chain = self.upstream_chain(boite_code)  # serving_box -> ... -> PM
        if not chain:
            return {
                "pm": pm, "destination": boite_code, "total_length": 0.0,
                "hops": [],  # 无上游光缆，仅有 ABONNE 终段
            }
        # chain 为 (cable, from, to) 的 start_box -> ... -> PM 顺序。
        # 重建为 PM 在前的路径再生成段: [PM, ..., boite_code]
        self._build_adjacency()
        path_boxes = [chain[0][1]]  # start_box
        for (_c, _a, b) in chain:
            path_boxes.append(b)
        pb = list(reversed(path_boxes))  # [PM, ..., boite_code]
        chain_pm_first = []
        for i in range(len(pb) - 1):
            a, b = pb[i], pb[i + 1]
            cab = None
            for cc, nxt in (self._adj or {}).get(a, []):
                if nxt == b:
                    cab = cc
                    break
            chain_pm_first.append((cab, a, b))
        hops = []
        total = 0.0
        for cable_code, _from, to_box in chain_pm_first:
            cable = self.cables.get(cable_code, {})
            try:
                length = float(cable.get("LONGUEUR") or 0.0)
            except (TypeError, ValueError):
                length = 0.0
            total += length
            cas = "EPISSURE" if to_box == boite_code else "PASSAGE"
            hops.append((cable_code, to_box, length, cas))
        return {
            "pm": pm, "destination": boite_code, "total_length": total, "hops": hops,
        }

    def summary(self) -> dict:
        return {
            "source": self.source,
            "IMB": len(self.imbs), "SITE": len(self.sites), "BOITE": len(self.boites),
            "CABLE": len(self.cables), "PTECH": len(self.ptechs),
            "INFRASTRUCTURE": len(self.infras), "ZNRO": len(self.znro), "ZPM": len(self.zpm),
            "pm_code": self.pm_code,
        }
