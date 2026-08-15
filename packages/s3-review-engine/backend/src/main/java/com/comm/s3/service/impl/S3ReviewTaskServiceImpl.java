package com.comm.s3.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.comm.s3.entity.S3ReviewTask;
import com.comm.s3.mapper.S3ReviewTaskMapper;
import com.comm.s3.service.S3ReviewTaskService;
import org.springframework.stereotype.Service;

@Service
public class S3ReviewTaskServiceImpl extends ServiceImpl<S3ReviewTaskMapper, S3ReviewTask> implements S3ReviewTaskService {
}
