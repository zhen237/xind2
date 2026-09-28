#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S3 规则引擎(Python) 接口测试（零依赖：仅标准库 unittest + urllib）
================================================================
运行：在 rules/ 目录下执行
    ../.venv/Scripts/python.exe -m unittest test_api -v
前置：Python 规则引擎已在 localhost:8000 运行

覆盖：
  - GET  /docs                      接口文档可用（200）
  - POST /api/v1/s3/review/check   规则引擎校验契约：
      入参复刻 Java ReviewService.executeReview 发给引擎的格式
      (design_data + items)，断言返回 code=200 且 data 为结果数组、
      每条含 rule_code/risk_level 且 risk_level 取值合法。
"""

import json
import os
import unittest
import urllib.request

BASE = "http://localhost:8000"
CHECK_URL = f"{BASE}/api/v1/s3/review/check"
DOCS_URL = f"{BASE}/docs"

VALID_RISK = {"critical", "error", "warning", "pending"}


def _post_json(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


class TestRulesEngineApi(unittest.TestCase):

    def test_docs_available(self):
        """引擎接口文档应可访问（健康检查替代）。"""
        with urllib.request.urlopen(DOCS_URL, timeout=10) as resp:
            self.assertEqual(resp.status, 200)

    def test_check_contract(self):
        """
        校验 /check 契约：发送与 Java 端一致的请求体
        （design_data 含一条容量超限电缆 + items 含 FT-001 容量规则），
        断言返回结构正确、结果可解析。
        """
        here = os.path.dirname(os.path.abspath(__file__))
        # 优先复用真实演示载荷作为 design_data 源，保证字段真实
        payload_path = os.path.join(here, "..", "s3_demo_payload.json")
        if os.path.exists(payload_path):
            with open(payload_path, "r", encoding="utf-8") as f:
                demo = json.load(f)
            design_data = {k: demo.get(k) for k in ("devices", "pipeline", "extraData") if k in demo}
        else:
            design_data = {
                "devices": [{
                    "deviceId": "CABLE-01", "deviceType": "power_cable",
                    "capacity": 24, "fibreUsed": 48,
                    "coordinates": "[114.05,30.60,0]"
                }],
                "pipeline": []
            }

        # items 复刻 Java 下发的规则列表（含附加的 FT-001 容量校验项）
        items = [{
            "rule_id": 100, "rule_code": "FT-001",
            "rule_name": "光缆/分纤箱容量校验", "category": "通信",
            "risk_level": "error", "threshold": "已用光纤数≤额定容量"
        }, {
            "rule_id": 1, "rule_code": "EL-001",
            "rule_name": "电缆弯曲半径校验", "category": "电气",
            "risk_level": "warning", "threshold": "弯曲半径≥15×缆径"
        }]

        body = {
            "task_id": 999001,
            "design_task_id": "TEST-CHECK-001",
            "task_name": "S3接口测试-规则引擎",
            "design_data": design_data,
            "items": items,
        }

        status, resp = _post_json(CHECK_URL, body)
        self.assertEqual(status, 200, f"/check HTTP 状态异常: {status}")
        self.assertEqual(resp.get("code"), 200, f"/check 业务码异常: {resp}")
        data = resp.get("data")
        self.assertIsInstance(data, list, "data 应为结果数组")
        self.assertTrue(len(data) >= 1, "应至少返回 1 条审查结果")
        for it in data:
            self.assertIn("rule_code", it, "结果缺少 rule_code")
            self.assertIn("risk_level", it, "结果缺少 risk_level")
            self.assertIn(it.get("risk_level"), VALID_RISK,
                          f"risk_level 非法: {it.get('risk_level')}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
