# M07 — AI 视觉检测引擎

**类型**: Python FastAPI 微服务
**端口**: 8088
**归属**: S5 — 施工过程智能监管
**负责人**: 李

## ⚠️ 当前状态：骨架（待开发）

目录结构已创建，但尚未填充业务代码。S5 开发时填充。

## 计划职责

- 安全帽佩戴检测（YOLOv8）
- 施工违章识别（围挡/违规操作）
- 隐蔽工程影像分析（管径/埋深/间距测量）
- 数字化验真（SHA256 哈希链）

## 启动（骨架）

```bash
cd packages/m07-cv-engine
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8088 --reload
```

## 依赖

- Python 3.10
- FastAPI + Uvicorn
- YOLOv8 (ultralytics)
- OpenCV
- MinIO（影像文件存储）
