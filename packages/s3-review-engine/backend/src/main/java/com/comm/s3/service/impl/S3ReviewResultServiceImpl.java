package com.comm.s3.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.comm.s3.entity.S3ReviewResult;
import com.comm.s3.mapper.S3ReviewResultMapper;
import com.comm.s3.service.S3ReviewResultService;
import org.springframework.stereotype.Service;

@Service
public class S3ReviewResultServiceImpl extends ServiceImpl<S3ReviewResultMapper, S3ReviewResult> implements S3ReviewResultService {
}
