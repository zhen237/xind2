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


def _s(v) -> str:
    """安全地把 dbf 字段值(可能为 int/float/None)转成去空白字符串。"""
    return "" if v is None else str(v).strip()


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
                    rp = _s(c.get("REF_PM"))
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
            o = _s(c.get("ORIGINE"))
            e = _s(c.get("EXTREMITE"))
            if o and e:
                adj.setdefault(o, []).append((code, e))
                adj.setdefault(e, []).append((code, o))
        self._adj = adj

    def _build_tree(self) -> None:
        """从 PM 根节点 BFS 构建有向树(父/子关系)，用于下游聚合(如箱体→住户)。"""
        if getattr(self, "_children", None) is not None:
            return
        self._build_adjacency()
        from collections import deque
        self._children: dict[str, list] = {}
        self._parent: dict[str, str | None] = {}
        root = self.pm_code
        if root and root in self._adj:
            q = deque([root])
            self._parent[root] = None
            while q:
                cur = q.popleft()
                for _cab, nxt in self._adj.get(cur, []):
                    if nxt not in self._parent:
                        self._parent[nxt] = cur
                        self._children.setdefault(cur, []).append(nxt)
                        q.append(nxt)

    def _descendants(self, boite_code: str) -> set[str]:
        """返回某箱体的全部下游后代(不含自身)，基于光缆树。"""
        self._build_tree()
        out: set[str] = set()
        stack = list(self._children.get(boite_code, []))
        while stack:
            n = stack.pop()
            if n in out:
                continue
            out.add(n)
            stack.extend(self._children.get(n, []))
        return out

    def _ancestors(self, boite_code: str) -> set[str]:
        """返回某箱体的全部上游祖先(不含自身)，基于光缆树(父链向上到 PM)。"""
        self._build_tree()
        out: set[str] = set()
        node = self._parent.get(boite_code)
        while node is not None:
            out.add(node)
            node = self._parent.get(node)
        return out

    def imbs_under_boite(self, boite_code: str) -> list[dict]:
        """
        返回某箱体所服务住户(IMB)记录。
        真实数据里 IMB.BPE_CODE 存的是 PBO 编码，且 BPE 常同时直连 PM 与多个 PBO
        (非干净树形)，故采用「有界 BFS 收集服务该箱体的 PBO 邻居(以 PBO 为终止，
        不向 PM 枢纽/其它 BPE 继续扩散)」来聚合 IMB，避免把整张网络统计进来。
        """
        self._build_adjacency()
        nodes = {boite_code}
        from collections import deque
        seen = {boite_code}
        q = deque([(boite_code, 0)])
        max_depth = 3
        while q:
            cur, d = q.popleft()
            if d >= max_depth:
                continue
            for _cab, nxt in self._adj.get(cur, []):
                if nxt in seen:
                    continue
                seen.add(nxt)
                if _s(self.boites.get(nxt, {}).get("TYPE")) == "PBO":
                    nodes.add(nxt)  # PBO 终止，不再从其扩散
                else:
                    q.append((nxt, d + 1))
        return [r for r in self.imbs.values()
                if _s(r.get("BPE_CODE")) in nodes]

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

    # ---- S1-A: 交付物生成辅助查询 ----
    def pm_codes(self) -> list[str]:
        """返回全部 PM/SRO 根节点编码(按 ZPM，否则聚合 BOITE.CABLE 的 REF_PM)。"""
        if self.zpm:
            return sorted(self.zpm.keys())
        s: set[str] = set()
        for b in self.boites.values():
            rp = _s(b.get("REF_PM"))
            if rp:
                s.add(rp)
        for c in self.cables.values():
            rp = _s(c.get("REF_PM"))
            if rp:
                s.add(rp)
        return sorted(s)

    def _pm_key(self, boite_code: str) -> str:
        """推断某箱体归属的 PM 编码: 优先 BOITE.REF_PM，否则路由 pm。"""
        b = self.boites.get(boite_code, {})
        rp = _s(b.get("REF_PM"))
        if rp:
            return rp
        r = self.route_for_boite(boite_code)
        return (r or {}).get("pm") or ""

    def boites_for_pm(self, pm_code: str) -> list[str]:
        """返回归属该 PM 的箱体 CODE 列表(按 REF_PM 直接归属，否则按路由 pm)。"""
        direct = [c for c, b in self.boites.items()
                  if _s(b.get("REF_PM")) == pm_code]
        if direct:
            return sorted(direct)
        res = [c for c in self.boites if self._pm_key(c) == pm_code]
        return sorted(res)

    def pm_of_boite(self, boite_code: str) -> str:
        """
        返回某箱体归一化后的归属 PM 编码:
          优先 BOITE.REF_PM，但仅当该值落在已知 PM 集合(pm_codes)内，
          否则回退到路由推导的 pm(避免真实脏数据如 'JAD-MAR1076' 产生幽灵分组)。
        """
        known = set(self.pm_codes())
        rp = _s(self.boites.get(boite_code, {}).get("REF_PM"))
        if rp and rp in known:
            return rp
        r = self.route_for_boite(boite_code)
        if r and r.get("pm"):
            return r["pm"]
        return _s(self.pm_code)

    def logements_of_boite(self, boite_code: str) -> int:
        """
        箱体下住户(prises/logements)数: 优先 BOITE.NB_LOGEMEN，否则累加其下游树
        (含自身及子 PBO)下挂 IMB 的 NB_LOC_TOT。
        """
        b = self.boites.get(boite_code, {})
        v = _s(b.get("NB_LOGEMEN"))
        if v:
            try:
                n = int(float(v))
                if n > 0:
                    return n  # 仅当显式给出正户数时才短路，否则回退到 IMB 聚合
            except (TypeError, ValueError):
                pass
        total = 0
        for imb in self.imbs_under_boite(boite_code):
            for f in ("NB_LOC_TOT", "NB_LOC_RES", "NB_LOC_PRO"):
                vv = _s(imb.get(f))
                if vv:
                    try:
                        total += int(float(vv))
                        break
                    except (TypeError, ValueError):
                        continue
        return total

    def total_prises(self) -> int:
        """全网总芯数(prises): 累加 ZPM.NB_PRISES 与 ZNRO.NB_PRISES。"""
        total = 0
        for z in list(self.zpm.values()) + list(self.znro.values()):
            v = _s(z.get("NB_PRISES"))
            if v:
                try:
                    total += int(float(v))
                except (TypeError, ValueError):
                    continue
        return total

    def connected_cables_for_pm(self, pm_code: str) -> list[str]:
        """
        该 PM 子树内出现的所有光缆 CODE(去重，按 CODE 排序)。
        用于 Plan_de_Baie / Synoptique 的缆段清单。
        """
        codes: set[str] = set()
        for boite in self.boites_for_pm(pm_code):
            r = self.route_for_boite(boite)
            if not r:
                continue
            for cable_code, _to, _length, _cas in r["hops"]:
                if cable_code:
                    codes.add(cable_code)
        return sorted(codes)

    def dominant_localisation(self) -> str:
        """从 IMB 的 VILLE 字段推断主导局站地名(无则回退空串)。"""
        from collections import Counter
        cnt: Counter = Counter()
        for imb in self.imbs.values():
            v = _s(imb.get("VILLE"))
            if v:
                cnt[v] += 1
        if cnt:
            return cnt.most_common(1)[0][0]
        return ""

    def node_position(self, code: str):
        """返回某节点(箱体或站点)的 (x经度, y纬度) float 元组，缺失返回 None。"""
        code = (code or "").strip()
        b = self.boites.get(code)
        if b is not None:
            try:
                return (float(b.get("X")), float(b.get("Y")))
            except (TypeError, ValueError):
                return None
        s = self.sites.get(code)
        if s is not None:
            try:
                return (float(s.get("X")), float(s.get("Y")))
            except (TypeError, ValueError):
                return None
        return None

    def summary(self) -> dict:
        return {
            "source": self.source,
            "IMB": len(self.imbs), "SITE": len(self.sites), "BOITE": len(self.boites),
            "CABLE": len(self.cables), "PTECH": len(self.ptechs),
            "INFRASTRUCTURE": len(self.infras), "ZNRO": len(self.znro), "ZPM": len(self.zpm),
            "pm_code": self.pm_code,
        }
