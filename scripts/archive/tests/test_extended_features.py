#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 2 & Phase 3 扩展功能综合测试脚本
验证所有新增功能的完整性和稳定性
"""

import os
import sys
import json
import time
from pathlib import Path

class ExtendedFeaturesTester:
    def __init__(self):
        self.frontend_path = r"d:\homework\xind2\xind2\packages\m03-bim-gis\frontend"
        self.results = []
        self.test_count = 0
        self.pass_count = 0
        
    def log_result(self, test_name, passed, details=""):
        self.test_count += 1
        if passed:
            self.pass_count += 1
        status = "✓ PASS" if passed else "✗ FAIL"
        self.results.append({
            'test': test_name,
            'passed': passed,
            'details': details
        })
        print(f"  [{status}] {test_name}")
        if details:
            print(f"         {details}")
    
    def test_phase2_file_structure(self):
        """测试Phase 2文件结构"""
        print("\n" + "="*70)
        print("Phase 2: 核心功能文件验证")
        print("="*70)
        
        required_files = [
            ('utils/projectManager.js', '项目持久化管理'),
            ('utils/exportUtils.js', '多格式导出'),
            ('utils/coverageAnalyzer.js', '覆盖分析'),
            ('components/ProjectManagementUI.vue', '项目管理UI'),
            ('components/WorkflowGuide.vue', '工作流引导')
        ]
        
        for rel_path, desc in required_files:
            full_path = os.path.join(self.frontend_path, rel_path)
            exists = os.path.exists(full_path)
            self.log_result(
                f"{desc} - {os.path.basename(rel_path)}",
                exists,
                f"路径: {rel_path}" if exists else "文件不存在"
            )
    
    def test_phase2_functionality(self):
        """测试Phase 2功能实现"""
        print("\n" + "="*70)
        print("Phase 2: 功能实现验证")
        print("="*70)
        
        # 测试projectManager.js
        pm_path = os.path.join(self.frontend_path, 'src/utils/projectManager.js')
        if os.path.exists(pm_path):
            with open(pm_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            checks = [
                ('saveProject方法', 'saveProject' in content),
                ('loadProject方法', 'loadProject' in content),
                ('deleteProject方法', 'deleteProject' in content),
                ('localStorage集成', 'localStorage' in content),
                ('自动ID生成', 'generateId' in content),
                ('时间戳管理', 'createdAt' in content and 'updatedAt' in content)
            ]
            
            for name, passed in checks:
                self.log_result(f"ProjectManager - {name}", passed)
        else:
            self.log_result("ProjectManager文件", False, "文件不存在")
        
        # 测试exportUtils.js
        eu_path = os.path.join(self.frontend_path, 'src/utils/exportUtils.js')
        if os.path.exists(eu_path):
            with open(eu_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            checks = [
                ('JSON导出', 'exportAsJSON' in content),
                ('CSV导出', 'exportAsCSV' in content),
                ('GeoJSON导出', 'exportAsGeoJSON' in content),
                ('文件下载', 'downloadFile' in content)
            ]
            
            for name, passed in checks:
                self.log_result(f"ExportUtils - {name}", passed)
        else:
            self.log_result("ExportUtils文件", False, "文件不存在")
        
        # 测试coverageAnalyzer.js
        ca_path = os.path.join(self.frontend_path, 'src/utils/coverageAnalyzer.js')
        if os.path.exists(ca_path):
            with open(ca_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            checks = [
                ('覆盖指标计算', 'calculateCoverageMetrics' in content),
                ('盲区检测', 'detectCoverageGaps' in content),
                ('报告生成', 'generateCoverageReport' in content),
                ('蒙特卡洛采样', 'monte' in content.lower() or 'sample' in content.lower())
            ]
            
            for name, passed in checks:
                self.log_result(f"CoverageAnalyzer - {name}", passed)
        else:
            self.log_result("CoverageAnalyzer文件", False, "文件不存在")
    
    def test_phase3_components(self):
        """测试Phase 3组件实现"""
        print("\n" + "="*70)
        print("Phase 3: 组件实现验证")
        print("="*70)
        
        # 测试ProjectManagementUI.vue
        pmui_path = os.path.join(self.frontend_path, 'src/components/ProjectManagementUI.vue')
        if os.path.exists(pmui_path):
            with open(pmui_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            checks = [
                ('项目列表表格', 'el-table' in content),
                ('搜索功能', 'searchKeyword' in content),
                ('筛选功能', 'filterLocation' in content),
                ('保存项目', 'saveCurrentAsProject' in content),
                ('加载项目', 'loadProjectAction' in content),
                ('删除项目', 'deleteProjectAction' in content),
                ('统计信息', 'project-stats' in content or '统计' in content)
            ]
            
            for name, passed in checks:
                self.log_result(f"ProjectManagementUI - {name}", passed)
        else:
            self.log_result("ProjectManagementUI文件", False, "文件不存在")
        
        # 测试WorkflowGuide.vue
        wg_path = os.path.join(self.frontend_path, 'src/components/WorkflowGuide.vue')
        if os.path.exists(wg_path):
            with open(wg_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            checks = [
                ('步骤导航', 'currentStep' in content),
                ('下一步按钮', 'handleNext' in content),
                ('上一步按钮', 'handlePrev' in content),
                ('跳过引导', 'skipGuide' in content),
                ('自动播放', 'startAutoPlay' in content),
                ('完成标记', 'guide_completed' in content)
            ]
            
            for name, passed in checks:
                self.log_result(f"WorkflowGuide - {name}", passed)
        else:
            self.log_result("WorkflowGuide文件", False, "文件不存在")
    
    def test_integration(self):
        """测试集成情况"""
        print("\n" + "="*70)
        print("集成验证")
        print("="*70)
        
        design_vue_path = os.path.join(self.frontend_path, 'src/views/Design.vue')
        if os.path.exists(design_vue_path):
            with open(design_vue_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            imports = [
                ('ProjectManager导入', 'projectManager' in content),
                ('ExportUtils导入', 'exportUtils' in content),
                ('CoverageAnalyzer导入', 'coverageAnalyzer' in content),
                ('项目保存函数', 'saveProject' in content),
                ('项目加载函数', 'loadProject' in content),
                ('导出函数', 'exportProject' in content),
                ('覆盖报告函数', 'showCoverageReport' in content)
            ]
            
            for name, passed in imports:
                self.log_result(f"Design.vue集成 - {name}", passed)
        else:
            self.log_result("Design.vue文件", False, "文件不存在")
    
    def test_code_quality(self):
        """测试代码质量"""
        print("\n" + "="*70)
        print("代码质量检查")
        print("="*70)
        
        utils_dir = os.path.join(self.frontend_path, 'src/utils')
        components_dir = os.path.join(self.frontend_path, 'src/components')
        
        # 检查注释
        files_to_check = [
            os.path.join(utils_dir, 'projectManager.js'),
            os.path.join(utils_dir, 'exportUtils.js'),
            os.path.join(utils_dir, 'coverageAnalyzer.js')
        ]
        
        for file_path in files_to_check:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                has_comments = '//' in content or '/*' in content or '/**' in content
                self.log_result(
                    f"{os.path.basename(file_path)} - 代码注释",
                    has_comments,
                    "包含注释" if has_comments else "缺少注释"
                )
    
    def test_performance_metrics(self):
        """测试性能指标"""
        print("\n" + "="*70)
        print("性能指标验证")
        print("="*70)
        
        # 检查文件大小
        files = [
            'src/utils/projectManager.js',
            'src/utils/exportUtils.js',
            'src/utils/coverageAnalyzer.js',
            'src/components/ProjectManagementUI.vue',
            'src/components/WorkflowGuide.vue'
        ]
        
        total_lines = 0
        for file_rel in files:
            file_path = os.path.join(self.frontend_path, file_rel)
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = len(f.readlines())
                    total_lines += lines
                    self.log_result(
                        f"{os.path.basename(file_rel)} - {lines}行",
                        lines < 500,  # 单个文件不超过500行
                        f"文件大小: {lines}行"
                    )
        
        self.log_result(
            "总代码行数",
            total_lines < 2000,
            f"累计{total_lines}行"
        )
    
    def generate_summary_report(self):
        """生成汇总报告"""
        print("\n" + "="*70)
        print("测试汇总报告")
        print("="*70)
        
        print(f"\n总测试数: {self.test_count}")
        print(f"通过数: {self.pass_count}")
        print(f"失败数: {self.test_count - self.pass_count}")
        print(f"通过率: {self.pass_count/self.test_count*100:.1f}%")
        
        failed_tests = [r for r in self.results if not r['passed']]
        if failed_tests:
            print("\n失败的测试:")
            for test in failed_tests:
                print(f"  ✗ {test['test']}: {test['details']}")
        
        print("\n" + "="*70)
        if self.pass_count == self.test_count:
            print("所有测试通过！✓")
        else:
            print(f"有 {self.test_count - self.pass_count} 个测试未通过")
        print("="*70)
        
        return self.pass_count == self.test_count

def main():
    print("="*70)
    print("M03模块 Phase 2 & Phase 3 扩展功能综合测试")
    print("="*70)
    
    tester = ExtendedFeaturesTester()
    
    # 执行测试
    tester.test_phase2_file_structure()
    tester.test_phase2_functionality()
    tester.test_phase3_components()
    tester.test_integration()
    tester.test_code_quality()
    tester.test_performance_metrics()
    
    # 生成报告
    all_passed = tester.generate_summary_report()
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
