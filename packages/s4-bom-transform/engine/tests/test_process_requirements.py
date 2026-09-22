"""关键工序工艺模板库导入与生成逻辑单元测试。"""
import pytest

from app.services.process_requirements import generate_process_requirements, _load_templates


class TestLoadTemplates:
    def test_load_returns_dict_and_list(self):
        templates, global_processes = _load_templates()
        assert isinstance(templates, dict)
        assert isinstance(global_processes, list)
        assert len(templates) > 0
        assert len(global_processes) > 0

    def test_template_structure(self):
        templates, _ = _load_templates()
        for dtype, template in templates.items():
            assert "steps" in template
            assert isinstance(template["steps"], list)
            for step in template["steps"]:
                assert "工序名称" in step
                assert "工艺要求" in step
                assert "验收标准" in step


class TestGenerateProcessRequirements:
    def test_single_device_type(self):
        result = generate_process_requirements(["antenna"])
        # antenna 4 道工序 + 4 条站点级通用工序
        assert len(result) == 8
        assert result[0]["工序名称"] == "天线吊装"
        assert result[0]["适用设备类型"] == "antenna"
        # 站点级工序追加在最后
        assert result[-1]["工序名称"] == "施工现场清理"

    def test_deduplication(self):
        result = generate_process_requirements(["rru", "rru", "bbu"])
        rru_steps = [s for s in result if s.get("适用设备类型") == "rru"]
        bbu_steps = [s for s in result if s.get("适用设备类型") == "bbu"]
        assert len(rru_steps) == 4
        assert len(bbu_steps) == 4

    def test_unknown_device_type_warns(self, caplog):
        with caplog.at_level("WARNING"):
            result = generate_process_requirements(["unknown_xyz"])
        assert any("No process template" in rec.message for rec in caplog.records)
        # 仅剩站点级通用工序
        assert len(result) == 4

    def test_sequence_numbers_are_continuous(self):
        result = generate_process_requirements(["power", "rack"])
        nums = [s["序号"] for s in result]
        assert nums == list(range(1, len(result) + 1))

    def test_does_not_mutate_global_template(self):
        generate_process_requirements(["antenna"])
        templates, _ = _load_templates()
        # 模板中不应被写入适用设备类型字段
        for step in templates["antenna"]["steps"]:
            assert "适用设备类型" not in step
