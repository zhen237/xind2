# Spec - S1 #5 设计场景分类（范式轴 × 技术轴）

> 生成日期：2026-08-13
> 基于：S1功能增强路线图.md #5 段 + 本次代码现状调研（design_dock.py / models/site.py / models/machine_room.py / design_engine/pipeline.py / ftth/）
> 状态：待用户确认
> 专家团纪律：P2 架构级；分阶段 + 门禁；不破坏现有「现网补盲」演示；P0 规则（禁用 emoji 图标 / 紫粉渐变 / AI 模板味）

---

## 1. 产品定义

- **一句话**：在现有「建设模式（现网补盲/新区新建）」之上，叠一层**通信技术制式（4G/5G）维度**，并用它驱动覆盖半径、站间距、单站容量、塔桅/BOM 形态；同时让 greenfield 模式真正接入"由机房+管线自动生成 FTTH 设计"。
- **目标用户**：挑战杯评委 / 通信设计演示者。
- **核心问题**：当前一刀切——无论 4G 还是 5G 都给同一套参数，且 greenfield 只做了半截（禁用步骤 + 横幅，无真实生成）。

## 2. MVP 范围（锁定——不在此列表的功能一律不做）

| 优先级 | 功能 | 验收标准摘要 | 阶段 |
|--------|------|-------------|------|
| P0 | 技术制式维度（4G/5G/4G+5G协同）| 基站参数步可选制式；覆盖半径/建议站间距/单站容量/塔桅形态随制式变；默认保留现状行为 | Phase A |
| P0 | greenfield 真正生成 FTTH 设计 | 机房+管线布置后，点"生成FTTH设计"产出 OLT→分光→入户的光缆设计，可渲染/导出 | Phase B |

## 3. 明确不做（Out-of-Scope）

| 不做的功能 | 原因 | 何时考虑 |
|------------|------|----------|
| 真实网络规划优化（自动选站址寻优）| 超出 S1 演示范围，属算法研究 | 后续赛题 |
| 毫米波波束级仿真 | 数据/算力依赖重 | v2 |
| 自动生成建筑轮廓（无底图时）| 需第三方矢量底图；v1 用合成网格或复用已有 IMB 层 | 有底图后 |

## 4. 技术架构（锁定）

| 层 | 技术 | 说明 |
|----|------|------|
| 模型 | `models/site.py` 加 `tech_generation` + `coverage_radius` + `capacity` 字段 | 向后兼容（旧 GeoJSON 缺字段则取默认） |
| 模型 | 新增 `TechGeneration` 枚举（独立模块 `models/tech.py`）| 4G LTE / 5G Sub-6 / 5G mmWave / 4G+5G协同 |
| 引擎 | `design_engine/pipeline.py`（已光纤感知）| greenfield 走管线复用，不改动 |
| 生成器(新) | `ftth/design_generator.py` | 纯新增模块，greenfield 专用 |
| UI | `ui/design_dock.py` | 技术制式下拉 + greenfield "生成FTTH设计"按钮；沿用现有深色 slate 主题，禁用 emoji/P0 规则 |

## 5. 参数基线（技术轴 —— 示例值，待校准）

| 制式 | 典型频段 | 覆盖半径(宏站) | 建议站间距 | 单站容量参考 | 塔桅/设备形态 |
|------|----------|----------------|------------|--------------|----------------|
| 4G LTE | 1.8–2.1GHz | 1.0–3.0 km | 0.8–1.5 km | 中 | RRU + 天线 |
| 5G NR(Sub-6) | 3.5GHz | 0.25–0.5 km | 0.2–0.4 km | 高 | AAU(有源天线) |
| 5G NR(mmWave) | 26/28GHz | 0.1–0.2 km | 0.1–0.15 km | 极高 | 小微站/灯杆站 |
| 4G+5G 协同 | 多频 | 取短板(≈5G) | 取 5G 间距 | 叠加 | 多频天线/AAU |

> 代码侧以 dict 形式存于 `models/tech.py:TECH_BASELINE`，键=枚举，值含 `coverage_radius_km`/`suggested_spacing_km`/`capacity_ref`/`tower_form`/`antenna_items`（用于 BOM）。

## 6. Phase A 详细设计（技术制式维度，低风险增量）

### 6.1 模型层 `models/tech.py`（新增）
- `class TechGeneration(Enum)`: `LTE4G="4G LTE"`, `NR5G_SUB6="5G NR(Sub-6)"`, `NR5G_MMWAVE="5G NR(mmWave)"`, `MULTI="4G+5G协同"`。
- `TECH_BASELINE: dict`：上表参数，单位/取值集中此处，单点可校准。

### 6.2 模型层 `models/site.py`（增量）
- 新增字段 `tech_generation: str = "4G+5G协同"`、`coverage_radius: float = 0.0`（0 表示"按制式基线算"）、`capacity: float = 0.0`。
- `to_geojson_feature` / `from_geojson_feature` 增加对应 properties（**旧数据缺键则回退默认，零破坏**）。
- `bill_of_materials()` 扩展：当 `tech_generation` 含 5G 时，追加 AAU 设备项；纯 4G 时 RRU+天线项；`tower_form` 来自基线。

### 6.3 UI 层 `design_dock.py`（增量）
- 基站参数步（step 4）新增「技术制式」`QComboBox`（4 选项，默认"4G+5G协同"）。
- 选定制式后：回填 `coverage_radius` 建议值（供覆盖分析/站间距提示）、`capacity` 建议值；影响 `bill_of_materials` 输出。
- **默认值策略**：默认 MULTI = 与现状行为一致 → brownfield 旧演示完全不受影响。

### 6.4 引擎联动（增量，不破坏）
- `coverage.py`（Okumura-Hata）/ `coverage_gap.py`（缺口聚类粒度、建议站间距）：读取 Site 的 `coverage_radius`（或基线），替代当前写死值。
- 缺口聚类粒度随覆盖半径缩放（半径小→网格更细）。

### 6.5 Phase A 验收（门禁）
- `py_compile` 通过；旧 GeoJSON 复现默认行为（diff 为零）；新选 5G Sub-6 时覆盖半径/站间距/BOM 的 AAU 项正确出现；tech 字段在 GeoJSON 往返一致。

## 7. Phase B 详细设计（greenfield FTTH 自动生成，高风险）

### 7.1 新模块 `ftth/design_generator.py`（纯新增，不碰 brownfield 路径）
输入：`MachineRoom`(OLT 锚点) + 设计区域面 + 管线图（`generate_shared_pipelines` 产物）+ 建筑轮廓来源（v1：区域内合成网格 / 或复用已有 IMB 层）。
逻辑：
1. OLT 逻辑节点落机房；`ZNRO`（OLT 覆盖范围面）= 以机房为心的圆（半径取接入层）。
2. 沿管线节点布放 `FD`（光分纤箱）级联点（分光比示意 1:8/1:16）。
3. `drop` 光缆：每个建筑轮廓 → 最近 FD/管线节点，复用 `generate_pipeline_to_room` 的路线生成（fiber 默认 G.652D）。
4. 输出 `FtthDesignProject`（兼容现有 `ftth/deliverables/ftth_json.py` 的字段：ZNRO/IMB/CABLE…），可被 `ftth/gis_style` 渲染 + 导出。

### 7.2 UI 层 `design_dock.py`（增量，gated）
- greenfield 模式下：启用第②/③步的替代——新增「生成 FTTH 设计」按钮（step 5/6 附近），点击调用 `design_generator`；移除"规划中"横幅改为"已生成"状态。
- 仅 greenfield 可见/可用；brownfield 全程不触碰。

### 7.3 护栏（不破坏现有演示）
- 新增模块与按钮均 `if self._build_mode == "greenfield"` 包裹；brownfield 代码路径字节级不变。
- `design_generator` 失败（无机房/无管线）给出明确提示，不抛未捕获异常。

### 7.4 Phase B 验收（门禁）
- greenfield 下：布置 1 机房 + 几条管线 → 点生成 → 地图出现 ZNRO/IMB/CABLE 且可导出 JSON；brownfield 演示流程与原先逐字节一致（回归）。
- `py_compile` + 离线逻辑自测（mock 机房/管线 → 生成结构非空、字段齐全）。

## 8. 端到端验证步骤
```bash
# 1. 编译
python -m py_compile models/tech.py models/site.py ui/design_dock.py ftth/design_generator.py design_engine/pipeline.py

# 2. Phase A 自测：tech 字段往返 + 5G BOM 含 AAU
python - <<'PY'
from models.site import Site
from models.tech import TechGeneration, TECH_BASELINE
s = Site(site_id="T1", name="t", longitude=111, latitude=35, tech_generation="5G NR(Sub-6)")
assert "AAU" in str(s.bill_of_materials())
f = s.to_geojson_feature(); s2 = Site.from_geojson_feature(f)
assert s2.tech_generation == s.tech_generation
print("PhaseA_OK")
PY

# 3. Phase B 自测（mock）：生成结构非空
python - <<'PY'
from ftth.design_generator import generate_ftth_design
proj = generate_ftth_design(room={"room_id":"R1","longitude":111,"latitude":35},
                            area_poly=[...], pipelines=[...])
assert proj and proj.get("ZNRO")
print("PhaseB_OK")
PY
```

## 9. 变更记录
| 日期 | 变更内容 | 原因 | 影响范围 |
|------|----------|------|----------|
| 2026-08-13 | 初版 Spec | #5 落地前的契约与门禁 | 全 S1 模块（增量） |
