// 生成多种天线类型的 glTF 模型文件
import { writeFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

// ── 基础几何体生成工具 ──

function createBox(sx, sy, sz) {
  const x = sx / 2, y = sy / 2, z = sz / 2;
  // 24 vertices (4 per face, 6 faces)
  const positions = [
    // +Z front
    -x,-y,z, x,-y,z, x,y,z, -x,y,z,
    // -Z back
    x,-y,-z, -x,-y,-z, -x,y,-z, x,y,-z,
    // +X right
    x,-y,z, x,-y,-z, x,y,-z, x,y,z,
    // -X left
    -x,-y,-z, -x,-y,z, -x,y,z, -x,y,-z,
    // +Y top
    -x,y,z, x,y,z, x,y,-z, -x,y,-z,
    // -Y bottom
    -x,-y,-z, x,-y,-z, x,-y,z, -x,-y,z,
  ];
  const normals = [
    0,0,1, 0,0,1, 0,0,1, 0,0,1,
    0,0,-1, 0,0,-1, 0,0,-1, 0,0,-1,
    1,0,0, 1,0,0, 1,0,0, 1,0,0,
    -1,0,0, -1,0,0, -1,0,0, -1,0,0,
    0,1,0, 0,1,0, 0,1,0, 0,1,0,
    0,-1,0, 0,-1,0, 0,-1,0, 0,-1,0,
  ];
  const indices = [];
  for (let f = 0; f < 6; f++) {
    const o = f * 4;
    indices.push(o,o+1,o+2, o,o+2,o+3);
  }
  return { positions: new Float32Array(positions), normals: new Float32Array(normals), indices: new Uint16Array(indices) };
}

function createCylinder(radiusTop, radiusBottom, height, segments = 16) {
  const positions = [];
  const normals = [];
  const indices = [];
  const halfH = height / 2;

  // Side vertices
  for (let i = 0; i <= segments; i++) {
    const theta = (i / segments) * Math.PI * 2;
    const cos = Math.cos(theta), sin = Math.sin(theta);
    // top ring
    positions.push(radiusTop * cos, halfH, radiusTop * sin);
    const nx = cos, nz = sin;
    const slope = (radiusBottom - radiusTop) / height;
    const len = Math.sqrt(nx*nx + slope*slope + nz*nz);
    normals.push(nx/len, slope/len, nz/len);
    // bottom ring
    positions.push(radiusBottom * cos, -halfH, radiusBottom * sin);
    normals.push(nx/len, slope/len, nz/len);
  }
  for (let i = 0; i < segments; i++) {
    const a = i * 2, b = a + 1, c = a + 2, d = a + 3;
    indices.push(a, b, d, a, d, c);
  }

  // Top cap
  const topCenter = positions.length / 3;
  positions.push(0, halfH, 0);
  normals.push(0, 1, 0);
  for (let i = 0; i <= segments; i++) {
    const theta = (i / segments) * Math.PI * 2;
    positions.push(radiusTop * Math.cos(theta), halfH, radiusTop * Math.sin(theta));
    normals.push(0, 1, 0);
  }
  for (let i = 0; i < segments; i++) {
    indices.push(topCenter, topCenter + 1 + i, topCenter + 2 + i);
  }

  // Bottom cap
  const botCenter = positions.length / 3;
  positions.push(0, -halfH, 0);
  normals.push(0, -1, 0);
  for (let i = 0; i <= segments; i++) {
    const theta = (i / segments) * Math.PI * 2;
    positions.push(radiusBottom * Math.cos(theta), -halfH, radiusBottom * Math.sin(theta));
    normals.push(0, -1, 0);
  }
  for (let i = 0; i < segments; i++) {
    indices.push(botCenter, botCenter + 2 + i, botCenter + 1 + i);
  }

  return { positions: new Float32Array(positions), normals: new Float32Array(normals), indices: new Uint16Array(indices) };
}

function mergeMeshes(meshes, transforms = []) {
  const allPos = [], allNorm = [], allIdx = [];
  let vertexOffset = 0;
  meshes.forEach((m, i) => {
    const t = transforms[i] || { tx:0, ty:0, tz:0, sx:1, sy:1, sz:1 };
    for (let v = 0; v < m.positions.length; v += 3) {
      allPos.push(m.positions[v]*t.sx + t.tx, m.positions[v+1]*t.sy + t.ty, m.positions[v+2]*t.sz + t.tz);
      allNorm.push(m.normals[v], m.normals[v+1], m.normals[v+2]);
    }
    for (let idx = 0; idx < m.indices.length; idx++) {
      allIdx.push(m.indices[idx] + vertexOffset);
    }
    vertexOffset += m.positions.length / 3;
  });
  return { positions: new Float32Array(allPos), normals: new Float32Array(allNorm), indices: new Uint16Array(allIdx) };
}

function buildGltf(mesh) {
  const posBuf = Buffer.from(mesh.positions.buffer);
  const normBuf = Buffer.from(mesh.normals.buffer);
  const idxBuf = Buffer.from(mesh.indices.buffer);
  // Pad each buffer to 4-byte alignment
  const pad = (buf) => {
    const rem = buf.byteLength % 4;
    return rem === 0 ? buf : Buffer.concat([buf, Buffer.alloc(4 - rem)]);
  };
  const pPos = pad(posBuf), pNorm = pad(normBuf), pIdx = pad(idxBuf);
  const totalSize = pPos.byteLength + pNorm.byteLength + pIdx.byteLength;

  const pMin = [Infinity, Infinity, Infinity], pMax = [-Infinity, -Infinity, -Infinity];
  for (let i = 0; i < mesh.positions.length; i += 3) {
    for (let j = 0; j < 3; j++) {
      pMin[j] = Math.min(pMin[j], mesh.positions[i+j]);
      pMax[j] = Math.max(pMax[j], mesh.positions[i+j]);
    }
  }

  const bufferData = Buffer.concat([pPos, pNorm, pIdx]);

  const gltf = {
    asset: { version: "2.0", generator: "antenna-generator" },
    scene: 0,
    scenes: [{ nodes: [0] }],
    nodes: [{ mesh: 0 }],
    meshes: [{
      primitives: [{
        attributes: { POSITION: 0, NORMAL: 1 },
        indices: 2,
        material: 0
      }]
    }],
    materials: [{
      pbrMetallicRoughness: {
        baseColorFactor: [0.7, 0.75, 0.8, 1.0],
        metallicFactor: 0.6,
        roughnessFactor: 0.4
      },
      name: "antenna_material"
    }],
    accessors: [
      { bufferView: 0, componentType: 5126, count: mesh.positions.length / 3, type: "VEC3", max: pMax, min: pMin },
      { bufferView: 1, componentType: 5126, count: mesh.normals.length / 3, type: "VEC3" },
      { bufferView: 2, componentType: 5123, count: mesh.indices.length, type: "SCALAR" }
    ],
    bufferViews: [
      { buffer: 0, byteOffset: 0, byteLength: pPos.byteLength, target: 34962 },
      { buffer: 0, byteOffset: pPos.byteLength, byteLength: pNorm.byteLength, target: 34962 },
      { buffer: 0, byteOffset: pPos.byteLength + pNorm.byteLength, byteLength: pIdx.byteLength, target: 34963 }
    ],
    buffers: [{
      uri: `data:application/octet-stream;base64,${bufferData.toString('base64')}`,
      byteLength: totalSize
    }]
  };
  return JSON.stringify(gltf);
}

// ── 1. 板状天线 (Panel Antenna) ──
// 典型的5G/4G基站板状天线，矩形面板 + 馈线接口 + 安装支架
function createPanelAntenna() {
  const parts = [];
  const transforms = [];

  // 主面板（长方形薄板）
  parts.push(createBox(0.8, 2.2, 0.15));
  transforms.push({ tx:0, ty:1.1, tz:0, sx:1, sy:1, sz:1 });

  // 面板前面板凸起（辐射单元阵列，4行x3列）
  for (let row = 0; row < 4; row++) {
    for (let col = 0; col < 3; col++) {
      parts.push(createBox(0.18, 0.35, 0.04));
      transforms.push({
        tx: -0.25 + col * 0.25,
        ty: 0.4 + row * 0.5,
        tz: 0.095,
        sx: 1, sy: 1, sz: 1
      });
    }
  }

  // 背部散热片
  for (let i = 0; i < 6; i++) {
    parts.push(createBox(0.7, 0.03, 0.12));
    transforms.push({ tx:0, ty: 0.3 + i * 0.35, tz: -0.13, sx:1, sy:1, sz:1 });
  }

  // 安装支架（U形卡扣）
  parts.push(createBox(0.12, 0.12, 0.4));
  transforms.push({ tx:0, ty:0.1, tz:-0.27, sx:1, sy:1, sz:1 });
  parts.push(createBox(0.12, 0.12, 0.4));
  transforms.push({ tx:0, ty:2.1, tz:-0.27, sx:1, sy:1, sz:1 });

  // 馈线接口（底部3个圆形接头）
  for (let i = 0; i < 3; i++) {
    parts.push(createCylinder(0.04, 0.04, 0.15, 8));
    transforms.push({ tx: -0.2 + i * 0.2, ty: -0.07, tz: 0, sx:1, sy:1, sz:1 });
  }

  return buildGltf(mergeMeshes(parts, transforms));
}

// ── 2. 八木天线 (Yagi Antenna) ──
// 定向天线，长杆 + 多个交叉振子 + 反射器
function createYagiAntenna() {
  const parts = [];
  const transforms = [];

  // 主杆（长圆柱）
  parts.push(createCylinder(0.04, 0.04, 4.0, 8));
  transforms.push({ tx:0, ty:2.0, tz:0, sx:1, sy:1, sz:1 });

  // 反射器（尾部最长振子）
  parts.push(createBox(1.6, 0.06, 0.06));
  transforms.push({ tx:0, ty:0.3, tz:0, sx:1, sy:1, sz:1 });

  // 引向器（7根，逐渐变短）
  const directorLengths = [1.2, 1.1, 1.0, 0.9, 0.85, 0.8, 0.75];
  directorLengths.forEach((len, i) => {
    parts.push(createBox(len, 0.05, 0.05));
    transforms.push({ tx:0, ty: 0.8 + i * 0.45, tz:0, sx:1, sy:1, sz:1 });
  });

  // 有源振子（中间的折合振子）
  parts.push(createBox(1.3, 0.08, 0.08));
  transforms.push({ tx:0, ty:0.55, tz:0, sx:1, sy:1, sz:1 });
  // 振子中间绝缘间隙
  parts.push(createBox(0.05, 0.12, 0.12));
  transforms.push({ tx:0, ty:0.55, tz:0, sx:1, sy:1, sz:1 });

  // 安装夹（与主杆连接的圆环）
  for (let i = 0; i < 3; i++) {
    parts.push(createCylinder(0.08, 0.08, 0.06, 8));
    transforms.push({ tx:0, ty: 0.1 + i * 2.0, tz:0, sx:1, sy:1, sz:1 });
  }

  return buildGltf(mergeMeshes(parts, transforms));
}

// ── 3. 全向天线 (Omni Antenna) ──
// 圆柱形全向天线，用于室内覆盖或微基站
function createOmniAntenna() {
  const parts = [];
  const transforms = [];

  // 主体圆柱（辐射体）
  parts.push(createCylinder(0.12, 0.12, 1.8, 16));
  transforms.push({ tx:0, ty:0.9, tz:0, sx:1, sy:1, sz:1 });

  // 顶部封盖
  parts.push(createCylinder(0.08, 0.12, 0.15, 16));
  transforms.push({ tx:0, ty:1.875, tz:0, sx:1, sy:1, sz:1 });

  // 顶部天线帽（锥形）
  parts.push(createCylinder(0.02, 0.08, 0.2, 12));
  transforms.push({ tx:0, ty:2.075, tz:0, sx:1, sy:1, sz:1 });

  // 底部安装法兰盘
  parts.push(createCylinder(0.25, 0.25, 0.08, 16));
  transforms.push({ tx:0, ty:-0.04, tz:0, sx:1, sy:1, sz:1 });

  // 底部螺栓（4个）
  for (let i = 0; i < 4; i++) {
    const angle = (i / 4) * Math.PI * 2;
    parts.push(createCylinder(0.025, 0.025, 0.12, 6));
    transforms.push({
      tx: Math.cos(angle) * 0.18,
      ty: -0.06,
      tz: Math.sin(angle) * 0.18,
      sx:1, sy:1, sz:1
    });
  }

  // 馈线接口
  parts.push(createCylinder(0.04, 0.04, 0.2, 8));
  transforms.push({ tx:0, ty:-0.14, tz:0.15, sx:1, sy:1, sz:1 });

  // 辐射体表面环形装饰（特征环）
  for (let i = 0; i < 5; i++) {
    parts.push(createCylinder(0.135, 0.135, 0.02, 16));
    transforms.push({ tx:0, ty: 0.3 + i * 0.35, tz:0, sx:1, sy:1, sz:1 });
  }

  return buildGltf(mergeMeshes(parts, transforms));
}

// ── 4. 抛物面天线 (Dish Antenna) ──
// 卫星通信/微波中继用的碟形天线
function createDishAntenna() {
  const parts = [];
  const transforms = [];

  // 抛物面（用多层圆盘模拟弧度）
  const dishLayers = 10;
  for (let i = 0; i < dishLayers; i++) {
    const t = i / dishLayers;
    const r = 0.3 + t * 1.0;
    const h = 0.08 - t * 0.04;
    parts.push(createCylinder(r, r + 0.12, h, 24));
    transforms.push({ tx:0, ty: 0.5 + t * 0.3, tz:0, sx:1, sy:1, sz:1 });
  }

  // 馈源喇叭（中心小喇叭）
  parts.push(createCylinder(0.06, 0.12, 0.25, 10));
  transforms.push({ tx:0, ty:0.35, tz:0, sx:1, sy:1, sz:1 });

  // 馈源支架（3根细杆）
  for (let i = 0; i < 3; i++) {
    const angle = (i / 3) * Math.PI * 2;
    const r1 = 0.15, r2 = 1.2;
    const midR = (r1 + r2) / 2;
    const len = r2 - r1;
    parts.push(createCylinder(0.015, 0.015, len, 6));
    transforms.push({
      tx: Math.cos(angle) * midR,
      ty: 0.45,
      tz: Math.sin(angle) * midR,
      sx: 1, sy: 1, sz: 1
    });
  }

  // 底座支架
  parts.push(createCylinder(0.08, 0.08, 1.5, 8));
  transforms.push({ tx:0, ty:-0.75, tz:0, sx:1, sy:1, sz:1 });

  // 方位旋转座
  parts.push(createBox(0.5, 0.3, 0.5));
  transforms.push({ tx:0, ty:-1.65, tz:0, sx:1, sy:1, sz:1 });

  // 底座法兰
  parts.push(createCylinder(0.35, 0.35, 0.1, 12));
  transforms.push({ tx:0, ty:-1.85, tz:0, sx:1, sy:1, sz:1 });

  return buildGltf(mergeMeshes(parts, transforms));
}

// ── 5. RRU设备 (Remote Radio Unit) ──
// 挂在铁塔上的长方体射频拉远单元
function createRRUUnit() {
  const parts = [];
  const transforms = [];

  // 主体外壳
  parts.push(createBox(0.5, 0.8, 0.3));
  transforms.push({ tx:0, ty:0.4, tz:0, sx:1, sy:1, sz:1 });

  // 前面板（略凸起）
  parts.push(createBox(0.46, 0.76, 0.02));
  transforms.push({ tx:0, ty:0.4, tz:0.16, sx:1, sy:1, sz:1 });

  // 指示灯（3个小圆点）
  for (let i = 0; i < 3; i++) {
    parts.push(createCylinder(0.02, 0.02, 0.02, 8));
    transforms.push({ tx:-0.12 + i * 0.12, ty:0.75, tz:0.17, sx:1, sy:1, sz:1 });
  }

  // 散热鳍片（背面）
  for (let i = 0; i < 8; i++) {
    parts.push(createBox(0.02, 0.6, 0.06));
    transforms.push({ tx:-0.2 + i * 0.058, ty:0.4, tz:-0.18, sx:1, sy:1, sz:1 });
  }

  // 顶部防水接头（光纤/电源）
  parts.push(createCylinder(0.04, 0.04, 0.1, 8));
  transforms.push({ tx:-0.1, ty:0.85, tz:0, sx:1, sy:1, sz:1 });
  parts.push(createCylinder(0.04, 0.04, 0.1, 8));
  transforms.push({ tx:0.1, ty:0.85, tz:0, sx:1, sy:1, sz:1 });

  // 底部馈线接口（6个N型接头）
  for (let i = 0; i < 6; i++) {
    parts.push(createCylinder(0.025, 0.025, 0.08, 8));
    transforms.push({ tx:-0.15 + i * 0.06, ty:-0.04, tz:0, sx:1, sy:1, sz:1 });
  }

  // 安装导轨（两侧）
  parts.push(createBox(0.04, 0.85, 0.35));
  transforms.push({ tx:-0.27, ty:0.4, tz:0, sx:1, sy:1, sz:1 });
  parts.push(createBox(0.04, 0.85, 0.35));
  transforms.push({ tx:0.27, ty:0.4, tz:0, sx:1, sy:1, sz:1 });

  return buildGltf(mergeMeshes(parts, transforms));
}

// ── 6. 微基站天线 (Small Cell Antenna) ──
// 5G小基站，紧凑型一体化设计
function createSmallCellAntenna() {
  const parts = [];
  const transforms = [];

  // 主体（圆角长方体模拟）
  parts.push(createBox(0.25, 0.5, 0.12));
  transforms.push({ tx:0, ty:0.25, tz:0, sx:1, sy:1, sz:1 });

  // 前面板天线阵列（3行x2列小辐射单元）
  for (let r = 0; r < 3; r++) {
    for (let c = 0; c < 2; c++) {
      parts.push(createBox(0.06, 0.1, 0.015));
      transforms.push({
        tx: -0.05 + c * 0.1,
        ty: 0.1 + r * 0.15,
        tz: 0.068,
        sx:1, sy:1, sz:1
      });
    }
  }

  // 挂钩（顶部安装用）
  parts.push(createBox(0.15, 0.04, 0.08));
  transforms.push({ tx:0, ty:0.52, tz:0, sx:1, sy:1, sz:1 });

  // 底部接口
  parts.push(createCylinder(0.025, 0.025, 0.08, 6));
  transforms.push({ tx:0, ty:-0.04, tz:0, sx:1, sy:1, sz:1 });

  // LED指示灯
  parts.push(createCylinder(0.015, 0.015, 0.01, 8));
  transforms.push({ tx:0, ty:0.48, tz:0.065, sx:1, sy:1, sz:1 });

  return buildGltf(mergeMeshes(parts, transforms));
}

// ── 生成所有文件 ──
const antennas = {
  'panel_antenna': { fn: createPanelAntenna, name: '板状天线 (5G/4G Panel)', desc: '典型基站板状天线，含辐射单元阵列、散热片、安装支架和馈线接口' },
  'yagi_antenna': { fn: createYagiAntenna, name: '八木天线 (Yagi Directional)', desc: '高增益定向天线，含反射器、有源振子、多级引向器' },
  'omni_antenna': { fn: createOmniAntenna, name: '全向天线 (Omni-directional)', desc: '360度覆盖全向天线，含法兰盘安装底座和馈线接口' },
  'dish_antenna': { fn: createDishAntenna, name: '抛物面天线 (Parabolic Dish)', desc: '卫星/微波中继碟形天线，含馈源喇叭、支架、方位旋转座' },
  'rru_unit': { fn: createRRUUnit, name: 'RRU射频拉远单元 (Remote Radio Unit)', desc: '挂塔式RRU设备，含散热鳍片、光纤/电源接口、N型馈线接口' },
  'small_cell_antenna': { fn: createSmallCellAntenna, name: '微基站天线 (5G Small Cell)', desc: '5G小基站一体化天线，紧凑设计含阵列辐射单元' },
};

console.log('Generating antenna glTF models...\n');

for (const [key, { fn, name, desc }] of Object.entries(antennas)) {
  const gltfJson = fn();
  const filePath = join(__dirname, `${key}.gltf`);
  writeFileSync(filePath, gltfJson, 'utf-8');
  console.log(`  ✓ ${key}.gltf — ${name}`);
  console.log(`    ${desc}`);
}

console.log(`\nDone! Generated ${Object.keys(antennas).length} antenna models.`);
