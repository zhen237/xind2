package com.comm.m03.controller;

import com.comm.common.Result;
import com.comm.m03.entity.Project;
import com.comm.m03.service.ProjectService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/m03/project")
public class ProjectController {

    @Autowired
    private ProjectService projectService;

    @GetMapping
    public Result<List<Project>> list() {
        return Result.success(projectService.list());
    }

    @GetMapping("/{id}")
    public Result<Project> getById(@PathVariable Long id) {
        Project project = projectService.getById(id);
        if (project == null) {
            return Result.notFound("项目不存在");
        }
        return Result.success(project);
    }

    @PostMapping
    public Result<Project> create(@RequestBody Project project) {
        projectService.save(project);
        return Result.success(project);
    }

    @PutMapping("/{id}")
    public Result<Boolean> update(@PathVariable Long id, @RequestBody Project project) {
        projectService.updateById(project);
        return Result.success(true);
    }

    @DeleteMapping("/{id}")
    public Result<Boolean> delete(@PathVariable Long id) {
        projectService.removeById(id);
        return Result.success(true);
    }
}
