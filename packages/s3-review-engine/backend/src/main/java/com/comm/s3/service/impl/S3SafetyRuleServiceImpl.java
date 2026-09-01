package com.comm.s3.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.comm.s3.entity.S3SafetyRule;
import com.comm.s3.mapper.S3SafetyRuleMapper;
import com.comm.s3.service.S3SafetyRuleService;
import org.springframework.stereotype.Service;

@Service
public class S3SafetyRuleServiceImpl extends ServiceImpl<S3SafetyRuleMapper, S3SafetyRule> implements S3SafetyRuleService {
}
