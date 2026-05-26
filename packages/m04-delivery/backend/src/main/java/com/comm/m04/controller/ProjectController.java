package com.comm.m04.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.comm.m04.common.Result;
import com.comm.m04.entity.Project;
import com.comm.m04.service.ProjectService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/m04/project")
public class ProjectController {

    @Autowired
    private ProjectService projectService;

    @GetMapping
    public Result<IPage<Project>> list(
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "10") Integer pageSize,
            @RequestParam(required = false) String projectName,
            @RequestParam(required = false) String regionCode) {
        IPage<Project> page = projectService.list(new Page<>(pageNum, pageSize), projectName, regionCode);
        return Result.success(page);
    }

    @GetMapping("/{id}")
    public Result<Project> getById(@PathVariable Long id) {
        Project p = projectService.getById(id);
        return p != null ? Result.success(p) : Result.notFound("项目不存在");
    }

    @GetMapping("/phase/{phase}")
    public Result<List<Project>> getByPhase(@PathVariable String phase) {
        IPage<Project> page = projectService.list(new Page<>(1, Integer.MAX_VALUE), null, null);
        List<Project> result = page.getRecords().stream()
                .filter(p -> phase.equals(p.getCurrentPhase()))
                .toList();
        return Result.success(result);
    }

    @GetMapping("/statistics")
    public Result<Map<String, Object>> statistics() {
        IPage<Project> page = projectService.list(new Page<>(1, Integer.MAX_VALUE), null, null);
        List<Project> all = page.getRecords();
        long total = all.size();
        long planning = all.stream().filter(p -> "PLANNING".equals(p.getCurrentPhase())).count();
        long design = all.stream().filter(p -> "DESIGN".equals(p.getCurrentPhase())).count();
        long construction = all.stream().filter(p -> "CONSTRUCTION".equals(p.getCurrentPhase())).count();
        long acceptance = all.stream().filter(p -> "ACCEPTANCE".equals(p.getCurrentPhase())).count();
        long completed = all.stream().filter(p -> p.getStatus() == 2).count();

        Map<String, Object> stats = new HashMap<>();
        stats.put("total", total);
        stats.put("planning", planning);
        stats.put("design", design);
        stats.put("construction", construction);
        stats.put("acceptance", acceptance);
        stats.put("completed", completed);
        return Result.success(stats);
    }

    @PostMapping
    public Result<Project> create(@RequestBody Project project) {
        boolean success = projectService.save(project);
        return success ? Result.success(project) : Result.error("创建失败");
    }

    @PutMapping("/{id}")
    public Result<Project> update(@PathVariable Long id, @RequestBody Project project) {
        project.setId(id);
        boolean success = projectService.update(project);
        return success ? Result.success(project) : Result.error("更新失败");
    }

    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        boolean success = projectService.deleteById(id);
        return success ? Result.success() : Result.error("删除失败");
    }
}