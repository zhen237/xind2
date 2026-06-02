# CV 视觉检测微服务

## 子赛题5：施工安全违章识别（人D负责）

独立 FastAPI 服务，端口 8088。

## 启动

```bash
pip install -r requirements.txt
python main.py
```

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/cv/detect | 单张图片检测 |
| POST | /api/cv/detect/batch | 批量检测 |
| GET | /api/cv/health | 健康检查 |
