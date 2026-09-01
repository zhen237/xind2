"""
纤芯分配表生成 — ODF 端口 → BBU/PTN → AAU/RRU 光纤链路分配。
"""
import logging
from typing import Optional

logger = logging.getLogger("s4-engine.fiber")


def generate_fiber_allocation(devices: list[dict]) -> list[dict]:
    """
    基于设备清单生成纤芯分配表。

    规则：
    - 每个 AAU (eCPRI): 2 芯（主备）
    - 每个 RRU (CPRI):  2 芯（主备）
    - 传输设备 (PTN): 每对上联 2 芯
    - GPS: 1 芯同轴（算作纤芯）

    返回 ODF 端口分配表。
    """
    odf_capacity = 72  # ODF-72C
    results = []
    port = 0

    # 找 BBU 和传输设备
    bbu_devices = [d for d in devices if d.get("type") == "bbu"]
    transmission_devices = [d for d in devices if d.get("type") == "transmission"]
    gps_devices = [d for d in devices if d.get("type") == "antenna" and "GPS" in d.get("name", "")]

    # 收集所有需要光纤连接的远端设备 (AAU/RRU)
    aau_rru_devices = [d for d in devices if d.get("type") in ("antenna", "rru") and "GPS" not in d.get("name", "")]

    for remote in aau_rru_devices:
        device_type = "AAU (eCPRI)" if remote["type"] == "antenna" else "RRU (CPRI)"
        # 主光纤
        port += 1
        results.append({
            "ODF端口": f"ODF-{port:02d}",
            "纤芯号": f"{port}",
            "起始设备": bbu_devices[0]["name"] if bbu_devices else "BBU",
            "起始端口": f"BBU-Slot{port}",
            "终止设备": remote["name"],
            "终止端口": "CPRI-1" if remote["type"] == "rru" else "eCPRI-1",
            "纤芯类型": "G.652D 单模",
            "纤芯用途": f"{remote['name']} 主链路 ({device_type})",
            "长度(m)": "--（由线缆估算给出）",
        })
        # 备光纤
        port += 1
        results.append({
            "ODF端口": f"ODF-{port:02d}",
            "纤芯号": f"{port}",
            "起始设备": bbu_devices[0]["name"] if bbu_devices else "BBU",
            "起始端口": f"BBU-Slot{port}",
            "终止设备": remote["name"],
            "终止端口": "CPRI-2" if remote["type"] == "rru" else "eCPRI-2",
            "纤芯类型": "G.652D 单模",
            "纤芯用途": f"{remote['name']} 备链路 ({device_type})",
            "长度(m)": "--（由线缆估算给出）",
        })

    # 传输设备：PTN 的每个端口可能需要纤芯，ODF 本身是配线架不需要
    for trn in transmission_devices:
        ports_spec = trn.get("ports", {})
        # 如果 ports 是纯数字（如 ODF-72C 的 72），跳过——它本身是配线架
        if isinstance(ports_spec, int):
            continue
        for speed_key, cnt in ports_spec.items():
            for _ in range(cnt):
                port += 1
                results.append({
                    "ODF端口": f"ODF-{port:02d}",
                    "纤芯号": f"{port}",
                    "起始设备": trn["name"],
                    "起始端口": f"{speed_key}-{_ + 1}",
                    "终止设备": "上层传输设备",
                    "终止端口": f"Uplink-{port}",
                    "纤芯类型": "G.652D 单模",
                    "纤芯用途": f"{trn['name']} {speed_key} 上联",
                    "长度(m)": "--（到上层设备距离）",
                })

    # GPS: 1 芯同轴
    for gps in gps_devices:
        port += 1
        results.append({
            "ODF端口": f"ODF-{port:02d}",
            "纤芯号": f"{port}",
            "起始设备": "BBU",
            "起始端口": "GPS-IN",
            "终止设备": gps["name"],
            "终止端口": "OUT",
            "纤芯类型": "1/2英寸同轴电缆",
            "纤芯用途": "GPS 天馈信号",
            "长度(m)": "--（塔顶到 BBU）",
        })

    summary = {
        "total_cores_assigned": port,
        "odf_capacity": odf_capacity,
        "odf_usage_rate": f"{port / odf_capacity * 100:.1f}%",
        "reserve_cores": odf_capacity - port,
    }

    logger.info(f"Fiber allocation: {port} cores assigned ({summary['odf_usage_rate']})")
    return results, summary
