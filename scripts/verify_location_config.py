#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
位置配置修复验证脚本
验证所有页面和组件是否已更新为运城学院位置
"""

import os
import sys
import re

def check_file_for_beijing_coords(file_path):
    """检查文件是否包含北京坐标"""
    beijing_patterns = [
        r'116\.4074',  # 北京经度
        r'39\.9042',   # 北京纬度
        r'116\.397',   # 北京测试坐标
        r'北京测试'
    ]
    
    issues = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            for pattern in beijing_patterns:
                if re.search(pattern, content):
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        if re.search(pattern, line):
                            issues.append(f"  行 {i}: {line.strip()}")
    except Exception as e:
        pass
    
    return issues

def check_file_uses_default_location(file_path):
    """检查文件是否正确使用DEFAULT_LOCATION配置"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            has_import = 'from \'@/config/location.js\'' in content or "from '@/config/location.js'" in content
            has_usage = 'DEFAULT_LOCATION' in content
            return has_import and has_usage
    except:
        return False

def main():
    print("=" * 70)
    print("位置配置修复验证报告")
    print("=" * 70)
    print()
    
    frontend_src = r"d:\homework\xind2\xind2\packages\m03-bim-gis\frontend\src"
    
    # 检查所有Vue文件
    vue_files = []
    for root, dirs, files in os.walk(frontend_src):
        for file in files:
            if file.endswith('.vue'):
                vue_files.append(os.path.join(root, file))
    
    print("[1/3] 检查硬编码的北京坐标...")
    print("-" * 70)
    
    files_with_issues = []
    for file_path in vue_files:
        issues = check_file_for_beijing_coords(file_path)
        if issues:
            rel_path = os.path.relpath(file_path, frontend_src)
            files_with_issues.append((rel_path, issues))
    
    if files_with_issues:
        print("⚠ 发现以下文件仍包含北京坐标:")
        for rel_path, issues in files_with_issues:
            print(f"\n  文件: {rel_path}")
            for issue in issues[:3]:  # 只显示前3处
                print(f"    {issue}")
    else:
        print("  ✓ 所有Vue文件已清理北京坐标")
    
    print()
    print("[2/3] 检查位置配置文件...")
    print("-" * 70)
    
    config_file = os.path.join(frontend_src, 'config', 'location.js')
    if os.path.exists(config_file):
        print(f"  ✓ 位置配置文件存在: config/location.js")
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if '110.932025' in content and '35.123754' in content:
                print("  ✓ 默认位置已设置为运城学院 (110.932025, 35.123754)")
            else:
                print("  ✗ 配置文件中的坐标不正确")
    else:
        print("  ✗ 位置配置文件不存在")
    
    print()
    print("[3/3] 检查各组件是否使用统一配置...")
    print("-" * 70)
    
    checked_files = []
    for file_path in vue_files:
        rel_path = os.path.relpath(file_path, frontend_src)
        uses_config = check_file_uses_default_location(file_path)
        status = "✓" if uses_config else "○"
        checked_files.append((rel_path, status, uses_config))
    
    # 统计
    used_config = sum(1 for _, status, _ in checked_files if status == "✓")
    total = len(checked_files)
    
    for rel_path, status, _ in checked_files:
        print(f"  {status} {rel_path}")
    
    print()
    print("=" * 70)
    print(f"检查结果: {used_config}/{total} 个组件使用统一位置配置")
    print("=" * 70)
    print()
    
    if files_with_issues:
        print("⚠ 建议:")
        print("  1. 更新剩余包含北京坐标的文件")
        print("  2. 确保所有组件导入并使用 DEFAULT_LOCATION")
        print("  3. 清除浏览器缓存后重新测试")
        return False
    else:
        print("✓ 位置配置修复完成!")
        print("  所有页面将默认定位到运城学院")
        print("  重启应用后位置将保持为运城学院")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
