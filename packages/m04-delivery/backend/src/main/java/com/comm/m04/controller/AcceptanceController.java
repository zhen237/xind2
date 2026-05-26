package com.comm.m04.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.comm.m04.common.Result;
import com.comm.m04.entity.AcceptanceProblem;
import com.comm.m04.entity.AcceptanceTask;
import com.comm.m04.service.AcceptanceProblemService;
import com.comm.m04.service.AcceptanceTaskService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/m04/acceptance")
public class AcceptanceController {

    @Autowired
    private AcceptanceTaskService acceptanceTaskService;

    @Autowired
    private AcceptanceProblemService acceptanceProblemService;

    @GetMapping("/task")
    public Result<IPage<AcceptanceTask>> listTasks(
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "10") Integer pageSize,
            @RequestParam(required = false) Long projectId,
            @RequestParam(required = false) Integer status) {
        IPage<AcceptanceTask> page = acceptanceTaskService.list(new Page<>(pageNum, pageSize), projectId, status);
        return Result.success(page);
    }

    @GetMapping("/task/{id}")
    public Result<AcceptanceTask> getTaskById(@PathVariable Long id) {
        AcceptanceTask task = acceptanceTaskService.getById(id);
        return task != null ? Result.success(task) : Result.notFound("验收任务不存在");
    }

    @PostMapping("/task")
    public Result<AcceptanceTask> createTask(@RequestBody AcceptanceTask task) {
        boolean success = acceptanceTaskService.save(task);
        return success ? Result.success(task) : Result.error("创建失败");
    }

    @PutMapping("/task/{id}")
    public Result<AcceptanceTask> updateTask(@PathVariable Long id, @RequestBody AcceptanceTask task) {
        task.setId(id);
        boolean success = acceptanceTaskService.update(task);
        return success ? Result.success(task) : Result.error("更新失败");
    }

    @PutMapping("/task/{id}/status")
    public Result<Void> updateTaskStatus(@PathVariable Long id, @RequestBody Map<String, Integer> body) {
        Integer status = body.get("status");
        boolean success = acceptanceTaskService.updateStatus(id, status);
        return success ? Result.success() : Result.error("更新失败");
    }

    @DeleteMapping("/task/{id}")
    public Result<Void> deleteTask(@PathVariable Long id) {
        boolean success = acceptanceTaskService.deleteById(id);
        return success ? Result.success() : Result.error("删除失败");
    }

    @GetMapping("/problem")
    public Result<IPage<AcceptanceProblem>> listProblems(
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "10") Integer pageSize,
            @RequestParam(required = false) Long taskId,
            @RequestParam(required = false) Integer status) {
        IPage<AcceptanceProblem> page = acceptanceProblemService.list(new Page<>(pageNum, pageSize), taskId, status);
        return Result.success(page);
    }

    @GetMapping("/problem/{id}")
    public Result<AcceptanceProblem> getProblemById(@PathVariable Long id) {
        AcceptanceProblem problem = acceptanceProblemService.getById(id);
        return problem != null ? Result.success(problem) : Result.notFound("验收问题不存在");
    }

    @PostMapping("/problem")
    public Result<AcceptanceProblem> createProblem(@RequestBody AcceptanceProblem problem) {
        boolean success = acceptanceProblemService.save(problem);
        return success ? Result.success(problem) : Result.error("创建失败");
    }

    @PutMapping("/problem/{id}")
    public Result<AcceptanceProblem> updateProblem(@PathVariable Long id, @RequestBody AcceptanceProblem problem) {
        problem.setId(id);
        boolean success = acceptanceProblemService.update(problem);
        return success ? Result.success(problem) : Result.error("更新失败");
    }

    @PutMapping("/problem/{id}/status")
    public Result<Void> updateProblemStatus(@PathVariable Long id, @RequestBody Map<String, Integer> body) {
        Integer status = body.get("status");
        boolean success = acceptanceProblemService.updateStatus(id, status);
        return success ? Result.success() : Result.error("更新失败");
    }

    @DeleteMapping("/problem/{id}")
    public Result<Void> deleteProblem(@PathVariable Long id) {
        boolean success = acceptanceProblemService.deleteById(id);
        return success ? Result.success() : Result.error("删除失败");
    }

    @GetMapping("/statistics")
    public Result<Map<String, Object>> statistics() {
        IPage<AcceptanceTask> taskPage = acceptanceTaskService.list(new Page<>(1, Integer.MAX_VALUE), null, null);
        List<AcceptanceTask> tasks = taskPage.getRecords();
        long totalTasks = tasks.size();
        long pendingTasks = tasks.stream().filter(t -> t.getStatus() == 0).count();
        long processingTasks = tasks.stream().filter(t -> t.getStatus() == 1).count();
        long passedTasks = tasks.stream().filter(t -> t.getStatus() == 2).count();
        long failedTasks = tasks.stream().filter(t -> t.getStatus() == 3).count();

        IPage<AcceptanceProblem> problemPage = acceptanceProblemService.list(new Page<>(1, Integer.MAX_VALUE), null, null);
        List<AcceptanceProblem> problems = problemPage.getRecords();
        long totalProblems = problems.size();
        long pendingProblems = problems.stream().filter(p -> p.getStatus() == 0).count();
        long rectifyingProblems = problems.stream().filter(p -> p.getStatus() == 1).count();
        long rectifiedProblems = problems.stream().filter(p -> p.getStatus() == 2).count();
        long reviewedProblems = problems.stream().filter(p -> p.getStatus() == 3).count();

        Map<String, Object> stats = new HashMap<>();
        stats.put("totalTasks", totalTasks);
        stats.put("pendingTasks", pendingTasks);
        stats.put("processingTasks", processingTasks);
        stats.put("passedTasks", passedTasks);
        stats.put("failedTasks", failedTasks);
        stats.put("totalProblems", totalProblems);
        stats.put("pendingProblems", pendingProblems);
        stats.put("rectifyingProblems", rectifyingProblems);
        stats.put("rectifiedProblems", rectifiedProblems);
        stats.put("reviewedProblems", reviewedProblems);
        return Result.success(stats);
    }
}