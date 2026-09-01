package com.comm.s2.s3push;

import com.comm.s2.common.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * S2 → S3 审查服务联动接口。
 */
@RestController
@RequestMapping("/api/s2/cad")
public class S3PushController {

    @Autowired
    private S3PushService s3PushService;

    /**
     * 将指定融合任务的融合结果 + 冲突清单推送给 S3 智能审查服务。
     *
     * @param taskId 融合任务 ID
     */
    @PostMapping("/s3-push")
    public Result<Map<String, Object>> pushToS3(@RequestParam Long taskId) {
        Map<String, Object> result = s3PushService.pushFusionResult(taskId);
        boolean success = Boolean.TRUE.equals(result.get("success"));
        return success ? Result.success("推送成功", result) : Result.error("推送失败", result);
    }
}
