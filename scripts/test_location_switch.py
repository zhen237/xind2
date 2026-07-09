#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
位置切换功能测试脚本
测试点击位置选择器后能否正确切换到武汉
"""

import urllib.request
import json
import sys

def test_wuhan_location():
    """测试武汉位置生成"""
    
    print("=" * 60)
    print("位置切换测试：武汉")
    print("=" * 60)
    
    # 武汉坐标
    wuhan_config = {
        "templateType": "macro",
        "centerLongitude": 114.39,
        "centerLatitude": 30.506,
        "coverageRadius": 500,
        "gridSize": 200,
        "sectorCount": 3
    }
    
    print(f"\n测试参数:")
    print(f"  位置: 武汉")
    print(f"  经度: {wuhan_config['centerLongitude']}")
    print(f"  纬度: {wuhan_config['centerLatitude']}")
    print(f"  覆盖半径: {wuhan_config['coverageRadius']}m")
    print()
    
    api_url = "http://localhost:8083/api/m03/design/generate"
    
    try:
        data = json.dumps(wuhan_config).encode('utf-8')
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
        
        gen_data = result.get('data', {})
        sites = gen_data.get('sites', [])
        
        print("测试结果:")
        print(f"  ✓ 总站点数: {gen_data.get('totalSites', 0)}")
        print(f"  ✓ 有效站点: {gen_data.get('validSites', 0)}")
        print(f"  ✓ 平均RSRP: {gen_data.get('avgRsrp', 0)} dBm")
        
        # 验证站点坐标
        if sites:
            first_site = sites[0]
            lon = first_site.get('longitude', 0)
            lat = first_site.get('latitude', 0)
            
            print(f"\n  首站坐标:")
            print(f"    经度: {lon}")
            print(f"    纬度: {lat}")
            
            # 检查是否在武汉附近
            delta_lon = abs(lon - 114.39)
            delta_lat = abs(lat - 30.506)
            
            if delta_lon < 0.01 and delta_lat < 0.01:
                print(f"    ✓ 坐标在武汉范围内（误差<1km）")
            else:
                print(f"    ✗ 坐标偏离武汉！")
                return False
        
        print("\n" + "=" * 60)
        print("位置切换测试通过！✓")
        print("=" * 60)
        print("\n前端操作流程:")
        print("  1. 打开页面 http://localhost:5174/modules/m03/")
        print("  2. 点击左下角位置选择器（显示'运城学院'）")
        print("  3. 在弹出菜单中选择'📍 武汉'")
        print("  4. 确认切换（如有站点数据）")
        print("  5. 地图自动飞到武汉位置")
        print("  6. 点击'生成方案'生成武汉基站布局")
        return True
        
    except Exception as e:
        print(f"\nERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_wuhan_location()
    sys.exit(0 if success else 1)
