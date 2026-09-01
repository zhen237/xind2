package com.comm.m02.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;

import java.io.File;

@Configuration
public class FileStorageConfig {

    @Value("${file.upload-dir:uploads}")
    private String uploadDir;

    @Value("${file.max-size:524288000}")
    private Long maxFileSize;

    public String getUploadDir() {
        File dir = new File(uploadDir);
        if (!dir.exists()) {
            dir.mkdirs();
        }
        return uploadDir;
    }

    public Long getMaxFileSize() {
        return maxFileSize;
    }

    public String getCadDir() {
        String cadDir = uploadDir + File.separator + "cad";
        File dir = new File(cadDir);
        if (!dir.exists()) {
            dir.mkdirs();
        }
        return cadDir;
    }

    public String getOutputDir() {
        String outputDir = uploadDir + File.separator + "output";
        File dir = new File(outputDir);
        if (!dir.exists()) {
            dir.mkdirs();
        }
        return outputDir;
    }
}
