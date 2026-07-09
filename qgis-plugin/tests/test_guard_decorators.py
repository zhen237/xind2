# -*- coding: utf-8 -*-
"""基础冒烟测试 — ui.guards 装饰器"""

import unittest
from unittest.mock import MagicMock, patch, PropertyMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock QGIS 模块（CI 环境无 QGIS）
sys.modules['qgis'] = MagicMock()
sys.modules['qgis.PyQt'] = MagicMock()
sys.modules['qgis.PyQt.QtWidgets'] = MagicMock()
sys.modules['qgis.PyQt.QtCore'] = MagicMock()
sys.modules['PyQt5'] = MagicMock()
sys.modules['PyQt5.QtCore'] = MagicMock()

from ui.guards import require_sites, require_extent, require_sites_count, safe_execute, log_call


class TestGuardDecorators(unittest.TestCase):

    def setUp(self):
        self.obj = MagicMock()
        self.obj.generated_sites = None
        self.obj.selected_extent = None

    def test_require_sites_blocks_when_empty(self):
        @require_sites("请先生成基站")
        def action(self):
            return "ok"

        result = action(self.obj)
        self.assertIsNone(result)

    def test_require_sites_passes_when_present(self):
        self.obj.generated_sites = [{"id": 1}]

        @require_sites("请先生成基站")
        def action(self):
            return "ok"

        result = action(self.obj)
        self.assertEqual(result, "ok")

    def test_require_extent_blocks_when_none(self):
        @require_extent("请先选择区域")
        def action(self):
            return "ok"

        result = action(self.obj)
        self.assertIsNone(result)

    def test_safe_execute_catches_errors(self):
        @safe_execute(show_errors=False)
        def boom(self):
            raise ValueError("test error")

        result = boom(self.obj)
        self.assertIsNone(result)

    def test_log_call_preserves_return(self):
        @log_call()
        def add(self, a, b):
            return a + b

        result = add(self.obj, 3, 5)
        self.assertEqual(result, 8)


class TestGridWorkerSmoke(unittest.TestCase):
    """GridWorker 信号连接冒烟测试"""

    def test_worker_signals_exist(self):
        from tools.grid_worker import GridWorkerSignals
        signals = GridWorkerSignals()
        self.assertTrue(hasattr(signals, 'progress'))
        self.assertTrue(hasattr(signals, 'finished'))
        self.assertTrue(hasattr(signals, 'error'))


if __name__ == '__main__':
    unittest.main()
