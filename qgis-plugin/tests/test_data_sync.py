"""data_sync 上传可靠性单元测试

证明两项核心保证:
1. 断网重传不丢 —— 首次 ConnectionError 后重试成功，数据完整上传
2. 上传失败数据不丢 —— 全部重试失败，数据保留在本地队列可重发
"""
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests  # noqa: E402  (data_sync 依赖 requests)
from design_engine.data_sync import DataSync, _QUEUE_FILE, _queue_load  # noqa: E402


def _make_sites(n=3):
    return [
        {
            "siteId": f"BTS-{i:03d}",
            "siteName": f"站{i}",
            "longitude": 114.0 + i * 0.01,
            "latitude": 30.0,
            "rsrp": -70.0,
            "isValid": True,
        }
        for i in range(n)
    ]


def _ok_upload(scheme_id=1, inserted=3):
    m = MagicMock()
    m.status_code = 200
    m.json.return_value = {
        "code": 200,
        "data": {"schemeId": scheme_id, "inserted": inserted, "dup": False},
    }
    return m


def _ok_sites(sites):
    m = MagicMock()
    m.status_code = 200
    m.json.return_value = {"code": 200, "data": sites}
    return m


def _reset_queue():
    if _QUEUE_FILE.exists():
        _QUEUE_FILE.unlink()


def test_retry_after_connection_error():
    """首次断网(ConnectionError)，第二次成功 -> 上传成功，方案ID正确，队列标记done"""
    sites = _make_sites(3)
    params = {"scheme_name": "t", "band": "3.5GHz", "tower_height": 35,
              "grid_size": "4x4", "avg_rsrp": -70}
    _reset_queue()
    sync = DataSync(api_url="http://fake")

    with patch("design_engine.data_sync.requests.post",
               side_effect=[requests.exceptions.ConnectionError(), _ok_upload()]), \
         patch("design_engine.data_sync.requests.get",
               return_value=_ok_sites(sites)), \
         patch("design_engine.data_sync.time.sleep", return_value=None):
        ok, detail = sync.upload_design(1, sites, params)

    assert ok is True, f"应上传成功, 实际返回: {detail}"
    assert detail["scheme_id"] == 1
    assert detail["verified"] is True, "校验回环应确认服务端收全"
    q = _queue_load()
    assert any(it["status"] == "done" for it in q), "缓存队列应标记该条为 done"
    print("  [PASS] 断网重传不丢: 首次 ConnectionError 后重试成功, 校验回环通过")


def test_failure_keeps_data():
    """全部重试失败 -> 返回 False, 但数据保留在本地队列(failed)可重发, 不丢"""
    sites = _make_sites(3)
    params = {"scheme_name": "t", "band": "3.5GHz", "tower_height": 35,
              "grid_size": "4x4", "avg_rsrp": -70}
    _reset_queue()
    sync = DataSync(api_url="http://fake")

    with patch("design_engine.data_sync.requests.post",
               side_effect=requests.exceptions.ConnectionError()), \
         patch("design_engine.data_sync.time.sleep", return_value=None):
        ok, msg = sync.upload_design(1, sites, params)

    assert ok is False
    q = _queue_load()
    failed = [it for it in q if it["status"] == "failed"]
    assert len(failed) == 1, "应有一条 failed 记录"
    assert failed[0]["totalSites"] == 3, "数据不应丢失"
    assert "idempotencyKey" in failed[0], "应带幂等键便于重发去重"
    print("  [PASS] 上传失败数据不丢: 条目保留在本地队列, 含幂等键可重发")


def test_verify_loop_flags_missing_sites():
    """校验回环能发现服务端站点缺失: 上传3个但服务端只回2个 -> 校验判定失败"""
    sites = _make_sites(3)
    sync = DataSync(api_url="http://fake")
    with patch("design_engine.data_sync.requests.get",
               return_value=_ok_sites(sites[:2])):  # 服务端只回 2 个
        ok = sync._verify_upload(1, 3, [s["siteId"] for s in sites])
    assert ok is False, "服务端少站应判定校验失败"
    print("  [PASS] 校验回环能发现服务端站点缺失(正确性质控)")


if __name__ == "__main__":
    test_retry_after_connection_error()
    test_failure_keeps_data()
    test_verify_loop_flags_missing_sites()
    print("\n全部 data_sync 可靠性测试通过 ✅")
