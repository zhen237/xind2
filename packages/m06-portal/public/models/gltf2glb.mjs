// 将 gltf (内嵌 base64 buffer) 转为 glb 二进制格式（逐文件处理，避免内存溢出）
import { readFileSync, writeFileSync, readdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

function convertOne(filePath) {
  const raw = readFileSync(filePath, 'utf-8');
  const gltf = JSON.parse(raw);

  // 提取 base64 buffer 并立即释放 JSON 中的大字符串
  const base64Data = gltf.buffers[0].uri.split(',')[1];
  gltf.buffers[0].byteLength = Buffer.byteLength(base64Data, 'base64');
  delete gltf.buffers[0].uri;
  const binBuffer = Buffer.from(base64Data, 'base64');
  // bin chunk 需要 4-byte 对齐
  const binPadding = (4 - (binBuffer.byteLength % 4)) % 4;
  const binChunk = binPadding > 0
    ? Buffer.concat([binBuffer, Buffer.alloc(binPadding)])
    : binBuffer;

  // JSON chunk
  let jsonStr = JSON.stringify(gltf);
  while (Buffer.byteLength(jsonStr, 'utf-8') % 4 !== 0) jsonStr += ' ';
  const jsonChunk = Buffer.from(jsonStr, 'utf-8');

  // GLB: header(12) + json_header(8) + json + bin_header(8) + bin
  const totalLength = 12 + 8 + jsonChunk.byteLength + 8 + binChunk.byteLength;
  const glb = Buffer.alloc(totalLength);
  let o = 0;

  // Header
  glb.writeUInt32LE(0x46546C67, o); o += 4; // "glTF"
  glb.writeUInt32LE(2, o); o += 4;
  glb.writeUInt32LE(totalLength, o); o += 4;

  // JSON chunk
  glb.writeUInt32LE(jsonChunk.byteLength, o); o += 4;
  glb.writeUInt32LE(0x4E4F534A, o); o += 4; // "JSON"
  jsonChunk.copy(glb, o); o += jsonChunk.byteLength;

  // BIN chunk
  glb.writeUInt32LE(binChunk.byteLength, o); o += 4;
  glb.writeUInt32LE(0x004E4942, o); o += 4; // "BIN\0"
  binChunk.copy(glb, o);

  return glb;
}

const files = readdirSync(__dirname).filter(f => f.endsWith('.gltf') && !f.includes('scene'));
console.log(`Converting ${files.length} gltf → glb...\n`);

for (const file of files) {
  const src = join(__dirname, file);
  const dst = join(__dirname, file.replace('.gltf', '.glb'));
  try {
    const glb = convertOne(src);
    writeFileSync(dst, glb);
    console.log(`  ✓ ${file.replace('.gltf', '.glb')}  (${(glb.byteLength / 1024).toFixed(1)}KB)`);
  } catch (e) {
    console.error(`  ✗ ${file}: ${e.message}`);
  }
}
console.log('\nDone!');
