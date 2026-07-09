package com.comm.m03.design.controller;

import com.comm.m03.design.entity.DesignData;
import com.comm.m03.design.entity.DesignScheme;
import com.comm.m03.design.entity.GenerateRequest;
import com.comm.m03.design.entity.Site;
import com.comm.m03.design.entity.SiteData;
import com.comm.m03.design.entity.ParametricTemplate;
import com.comm.m03.design.entity.DesignTask;
import com.comm.m03.design.service.DesignService;
import com.comm.common.Result;
import com.comm.m03.rate_limit.RateLimit;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/m03/design")
public class DesignController {

    @Autowired
    private DesignService designService;

    @PostMapping("/upload")
    @RateLimit(permitsPerSecond = 10.0)
    public Result<Long> uploadDesign(@Valid @RequestBody DesignData designData) {
        Long schemeId = designService.saveDesignScheme(designData);
        designService.saveSites(schemeId, designData.getSites());
        return Result.success("上传成功", schemeId);
    }

    @GetMapping("/{projectId}")
    public Result<DesignScheme> getDesign(@PathVariable Long projectId) {
        DesignScheme scheme = designService.getDesignScheme(projectId);
        if (scheme == null) {
            return Result.notFound("未找到设计方案");
        }
        return Result.success(scheme);
    }

    @PostMapping("/{schemeId}/sites")
    @RateLimit(permitsPerSecond = 10.0)
    public Result<String> uploadSite(@PathVariable Long schemeId, @Valid @RequestBody SiteData siteData) {
        designService.saveSite(schemeId, siteData);
        return Result.success("上传成功");
    }

    @GetMapping("/{schemeId}/sites")
    public Result<List<Site>> getSites(@PathVariable Long schemeId) {
        List<Site> sites = designService.getSites(schemeId);
        return Result.success(sites);
    }

    @GetMapping("/{projectId}/geojson")
    public Result<String> getGeoJson(@PathVariable Long projectId) {
        String geoJson = designService.getGeoJson(projectId);
        return Result.success(geoJson);
    }

    @DeleteMapping("/{schemeId}")
    public Result<String> deleteDesign(@PathVariable Long schemeId) {
        designService.deleteDesignScheme(schemeId);
        return Result.success("删除成功");
    }

    @PostMapping("/generate")
    @RateLimit(permitsPerSecond = 5.0)
    public Result<DesignData> generateDesign(@Valid @RequestBody GenerateRequest request) {
        DesignData designData = designService.generateDesign(request);
        return Result.success(designData);
    }

    @GetMapping("/templates")
    public Result<List<ParametricTemplate>> getTemplates() {
        List<ParametricTemplate> templates = designService.getTemplates();
        return Result.success(templates);
    }

    @GetMapping("/templates/{templateId}")
    public Result<ParametricTemplate> getTemplate(@PathVariable Long templateId) {
        ParametricTemplate template = designService.getTemplate(templateId);
        if (template == null) {
            return Result.notFound("模板不存在");
        }
        return Result.success(template);
    }

    @PostMapping("/templates")
    public Result<String> createTemplate(@Valid @RequestBody ParametricTemplate template) {
        designService.createTemplate(template);
        return Result.success("模板创建成功");
    }

    @PutMapping("/templates/{templateId}")
    public Result<String> updateTemplate(@PathVariable Long templateId, @Valid @RequestBody ParametricTemplate template) {
        template.setId(templateId);
        designService.updateTemplate(template);
        return Result.success("模板更新成功");
    }

    @DeleteMapping("/templates/{templateId}")
    public Result<String> deleteTemplate(@PathVariable Long templateId) {
        designService.deleteTemplate(templateId);
        return Result.success("模板删除成功");
    }

    @PostMapping("/tasks")
    public Result<String> createDesignTask(@Valid @RequestBody DesignTask task) {
        designService.createDesignTask(task);
        return Result.success("设计任务创建成功");
    }

    @GetMapping("/tasks")
    public Result<List<DesignTask>> getDesignTasks(@RequestParam(required = false) String status) {
        List<DesignTask> tasks = designService.getDesignTasks(status);
        return Result.success(tasks);
    }

    @GetMapping("/tasks/{taskId}")
    public Result<DesignTask> getDesignTask(@PathVariable Long taskId) {
        DesignTask task = designService.getDesignTask(taskId);
        if (task == null) {
            return Result.notFound("任务不存在");
        }
        return Result.success(task);
    }

    @PutMapping("/tasks/{taskId}/status")
    public Result<String> updateTaskStatus(@PathVariable Long taskId, @RequestParam String status) {
        designService.updateTaskStatus(taskId, status);
        return Result.success("任务状态更新成功");
    }

    @DeleteMapping("/tasks/{taskId}")
    public Result<String> deleteDesignTask(@PathVariable Long taskId) {
        designService.deleteDesignTask(taskId);
        return Result.success("任务删除成功");
    }

    @PostMapping("/tasks/{taskId}/generate")
    public Result<DesignData> executeDesignTask(@PathVariable Long taskId) {
        DesignData designData = designService.executeDesignTask(taskId);
        return Result.success("任务执行成功", designData);
    }
}
