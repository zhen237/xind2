package com.comm.m03.controller;

import com.comm.m03.entity.Project;
import com.comm.m03.service.ProjectService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/m03/project")
public class ProjectController {
    
    @Autowired
    private ProjectService projectService;
    
    @GetMapping
    public ResponseEntity<List<Project>> getAllProjects() {
        return ResponseEntity.ok(projectService.list());
    }
    
    @GetMapping("/{id}")
    public ResponseEntity<Project> getProjectById(@PathVariable Long id) {
        Project project = projectService.getById(id);
        if (project == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(project);
    }
    
    @PostMapping
    public ResponseEntity<Project> createProject(@RequestBody Project project) {
        projectService.save(project);
        return ResponseEntity.ok(project);
    }
    
    @PutMapping("/{id}")
    public ResponseEntity<Void> updateProject(@PathVariable Long id, @RequestBody Project project) {
        projectService.updateById(project);
        return ResponseEntity.ok().build();
    }
    
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteProject(@PathVariable Long id) {
        projectService.removeById(id);
        return ResponseEntity.noContent().build();
    }
}