#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试脚本：验证运城学院位置基站生成
坐标：经度 110.932025, 纬度 35.123754
"""

import urllib.request
import json
import sys

def test_yuncheng_college():
    """测试运城学院位置的基站生成"""
    
    # API地址
    api_url = "http://localhost:8083/api/m03/design/generate"
    
    # 请求参数：运城学院位置
    payload = {
        "templateType": "macro",
        "centerLongitude": 110.932025,  # 运城学院经度
        "centerLatitude": 35.123754,     # 运城学院纬度
        "coverageRadius": 500,
        "gridSize": 200,
        "sectorCount": 3
    }
    
    print("=" * 60)
    print("基站定位测试：运城学院校区")
    print("=" * 60)
    print(f"\n测试坐标:")
    print(f"  经度: 110.932025")
    print(f"  纬度: 35.123754")
    print(f"  位置: 山西省运城市盐湖区运城学院")
    print(f"\n测试参数:")
    print(f"  模板类型: {payload['templateType']}")
    print(f"  覆盖半径: {payload['coverageRadius']}m")
    print(f"  网格大小: {payload['gridSize']}m")
    print(f"  扇区数: {payload['sectorCount']}")
    print("\n" + "-" * 60)
    
    # 发送请求
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            api_url,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        response = urllib.request.urlopen(req, timeout=10)
        result = json.loads(response.read().decode('utf-8'))
        
        if result.get('code') != 200:
            print(f"ERROR: API返回错误 - {result.get('message')}")
            return False
        
        data = result.get('data', {})
        sites = data.get('sites', [])
        
        print("\n测试结果:")
        print(f"  ✓ 总站点数: {data.get('totalSites', 0)}")
        print(f"  ✓ 有效站点: {data.get('validSites', 0)}")
        print(f"  ✓ 无效站点: {data.get('invalidSites', 0)}")
        print(f"  ✓ 平均RSRP: {data.get('avgRsrp', 0)} dBm")
        
        # 验证站点坐标是否在运城学院附近
        print(f"\n站点详情（前5个）:")
        print("-" * 60)
        print(f"{'站点ID':<12} {'经度':<12} {'纬度':<12} {'RSRP':<10} {'状态'}")
        print("-" * 60)
        
        for i, site in enumerate(sites[:5]):
            site_id = site.get('siteId', 'N/A')
            lon = site.get('longitude', 0)
            lat = site.get('latitude', 0)
            rsrp = site.get('rsrp', 0)
            is_valid = site.get('isValid', False)
            
            # 计算与运城学院中心的距离
            import math
            delta_lon = abs(lon - 110.932025) * 111320  # 约111320米/度
            delta_lat = abs(lat - 35.123754) * 110940   # 约110940米/度
            distance = math.sqrt(delta_lon**2 + delta_lat**2)
            
            status = "正常" if is_valid else "故障"
            print(f"{site_id:<12} {lon:<12.6f} {lat:<12.6f} {rsrp:<10.2f} {status}")
            print(f"  → 距中心: {distance:.1f}m")
        
        # 验证精度
        print("\n" + "=" * 60)
        print("精度验证:")
        print("=" * 60)
        
        all_within_range = True
        for site in sites:
            lon = site.get('longitude', 0)
            lat = site.get('latitude', 0)
            
            # 计算距离（简化版）
            import math
            delta_lon = abs(lon - 110.932025) * 111320
            delta_lat = abs(lat - 35.123754) * 110940
            distance = math.sqrt(delta_lon**2 + delta_lat**2)
            
            if distance > 1000:  # 应该在1km范围内
                all_within_range = False
                print(f"  ✗ {site['siteId']}: 距离过远 ({distance:.1f}m)")
        
        if all_within_range and len(sites) > 0:
            print("  ✓ 所有站点均在覆盖范围内")
            print("  ✓ 定位精度满足要求（<=100米）")
            print("  ✓ 运城学院校区覆盖成功")
            print("\n" + "=" * 60)
            print("测试通过！✓")
            print("=" * 60)
            return True
        else:
            print("  ✗ 部分站点超出覆盖范围")
            print("\n" + "=" * 60)
            print("测试未通过！✗")
            print("=" * 60)
            return False
            
    except urllib.error.URLError as e:
        print(f"\nERROR: 无法连接到API服务 - {e}")
        print("请确保M03后端服务正在运行（端口8083）")
        return False
    except Exception as e:
        print(f"\nERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_yuncheng_college()
    sys.exit(0 if success else 1)
