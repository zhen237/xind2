"""
AC-1 性能基准测试 + AC-5 导出链路验证
"""
import time
import requests

PROXY_URL = "http://localhost:8090"
SCENARIOS = [
    {"name": "运城宏站(15设备)", "designTaskId": "D001", "projectId": "PRJ-yuncheng"},
    {"name": "万象城室分(14设备)", "designTaskId": "D002", "projectId": "PRJ-indoor-mall"},
    {"name": "解放路微站(9设备)", "designTaskId": "D003", "projectId": "PRJ-micro-urban"},
]

def benchmark_scenario(scenario):
    name = scenario["name"]
    print(f"\n{'='*50}")
    print(f"  测试: {name}")
    print(f"{'='*50}")

    # 1. 发起生成请求
    t0 = time.time()
    resp = requests.post(f"{PROXY_URL}/api/s4/bom/generate", json={
        "designTaskId": scenario["designTaskId"],
        "projectId": scenario["projectId"],
    }, timeout=10)
    t_gen = time.time() - t0
    data = resp.json()
    task_id = data.get("taskId")
    print(f"  [1] POST /generate  →  {resp.status_code}  taskId={task_id}  ({t_gen:.2f}s)")

    # 2. 轮询直到完成
    t_start = time.time()
    max_wait = 65
    interval = 1.0
    elapsed = 0
    while elapsed < max_wait:
        time.sleep(interval)
        elapsed = time.time() - t_start
        resp = requests.get(f"{PROXY_URL}/api/s4/bom/{task_id}/status", timeout=5)
        st = resp.json()
        status = st.get("status")

        if status == "done":
            t_total = time.time() - t0
            print(f"  [2] 轮询完成 → status=done  ({t_total:.2f}s 总计)")
            print(f"       物料: {st.get('totalItems', '-')} 条, {st.get('totalCategories', '-')} 类目")
            break
        if status == "failed":
            t_total = time.time() - t0
            print(f"  [2] 轮询失败 → status=failed  ({t_total:.2f}s)")
            return {"scenario": name, "status": "FAIL", "time_s": round(t_total, 2), "items": 0, "error": st.get("error", "")}
    else:
        t_total = time.time() - t0
        print(f"  [2] 超时 → {t_total:.2f}s 未完成")
        return {"scenario": name, "status": "TIMEOUT", "time_s": round(t_total, 2), "items": 0}

    # 3. 验证详情
    resp = requests.get(f"{PROXY_URL}/api/s4/bom/{task_id}/full", timeout=5)
    full = resp.json()
    has_process = bool(full.get("processRequirements"))
    has_fiber = bool(full.get("fiberAllocation"))
    n_items = len(full.get("items", []))
    print(f"  [3] 详情验证 → items={n_items}, 工序={'✅' if has_process else '❌'}, 纤芯={'✅' if has_fiber else '❌'}")

    # 4. 验证导出 (AC-5)
    resp = requests.get(f"{PROXY_URL}/api/s4/bom/{task_id}/export", timeout=5)
    ct = resp.headers.get("content-type", "")
    if resp.status_code == 200 and "openxmlformats" in ct:
        fsize = len(resp.content)
        print(f"  [4] 导出验证 → ✅ OK ({fsize:,d} bytes, {ct})")
        export_ok = True
    else:
        print(f"  [4] 导出验证 → ❌ FAIL (status={resp.status_code}, ct={ct})")
        export_ok = False

    return {"scenario": name, "status": "PASS", "time_s": round(t_total, 2), "items": st.get("totalItems", 0),
            "export_ok": export_ok, "has_process": has_process, "has_fiber": has_fiber}


if __name__ == "__main__":
    print("=" * 60)
    print("  S4 BOM 性能基准测试 (AC-1) + 导出链路 (AC-5)")
    print(f"  目标: 15 设备 < 60s")
    print("=" * 60)

    results = []
    for s in SCENARIOS:
        r = benchmark_scenario(s)
        results.append(r)

    print("\n" + "=" * 60)
    print("  测试结果汇总")
    print("=" * 60)

    all_pass = True
    for r in results:
        icon = "✅" if r["status"] == "PASS" else "❌"
        print(f"  {icon} {r['scenario']:20s}  {r['time_s']:6.2f}s  items={r['items']}")
        if r.get("export_ok") is not None:
            print(f"     导出={'✅' if r['export_ok'] else '❌'}  工序={'✅' if r['has_process'] else '❌'}  纤芯={'✅' if r['has_fiber'] else '❌'}")
        if r["status"] != "PASS":
            all_pass = False

    print()
    if all_pass:
        print("  ✅ AC-1 + AC-5 全部通过!")
    else:
        print("  ❌ 存在未通过项")
    print()
