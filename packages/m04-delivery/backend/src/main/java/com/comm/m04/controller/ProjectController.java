package com.comm.m04.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.comm.m04.common.Result;
import com.comm.m04.entity.Project;
import com.comm.m04.mapper.ProjectMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/m04/project")
public class ProjectController {

    @Autowired
    private ProjectMapper projectMapper;

    @GetMapping
    public Result<List<Project>> list() {
        return Result.success(projectMapper.selectList(null));
    }

    @GetMapping("/{id}")
    public Result<Project> getById(@PathVariable Long id) {
        Project p = projectMapper.selectById(id);
        return p != null ? Result.success(p) : Result.notFound("项目不存在");
    }

    @GetMapping("/phase/{phase}")
    public Result<List<Project>> getByPhase(@PathVariable String phase) {
        return Result.success(projectMapper.selectList(
                new LambdaQueryWrapper<Project>().eq(Project::getCurrentPhase, phase)));
    }

    @GetMapping("/statistics")
    public Result<java.util.Map<String, Object>> statistics() {
        List<Project> all = projectMapper.selectList(null);
        long total = all.size();
        long planning = all.stream().filter(p -> "PLANNING".equals(p.getCurrentPhase())).count();
        long design = all.stream().filter(p -> "DESIGN".equals(p.getCurrentPhase())).count();
        long construction = all.stream().filter(p -> "CONSTRUCTION".equals(p.getCurrentPhase())).count();
        long acceptance = all.stream().filter(p -> "ACCEPTANCE".equals(p.getCurrentPhase())).count();
        long completed = all.stream().filter(p -> p.getStatus() == 2).count();

        java.util.Map<String, Object> stats = new java.util.HashMap<>();
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
        projectMapper.insert(project);
        return Result.success(project);
    }

    @PutMapping("/{id}")
    public Result<Project> update(@PathVariable Long id, @RequestBody Project project) {
        project.setId(id);
        projectMapper.updateById(project);
        return Result.success(project);
    }

    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        projectMapper.deleteById(id);
        return Result.success();
    }
}
