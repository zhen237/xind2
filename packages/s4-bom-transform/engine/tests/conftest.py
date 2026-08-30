"""pytest 路径配置 — 把 engine 根目录加入 sys.path，使 app 包可导入。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
