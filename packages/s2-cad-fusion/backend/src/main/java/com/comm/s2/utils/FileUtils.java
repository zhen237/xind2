package com.comm.s2.utils;

import org.springframework.web.multipart.MultipartFile;

import java.io.*;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.UUID;

public class FileUtils {

    /**
     * 生成带原始名 + 时间戳 + 短随机串的存储文件名，形如：
     *   通信设计方案_20260903_104215_a3f2.dxf
     * 替代早期纯 UUID 哈希（前端展示时无法辨认文件）。
     */
    public static String generateFileName(String originalName) {
        String baseName = sanitizeFileName(getFileNameWithoutExtension(originalName));
        String extension = getFileExtension(originalName);
        String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
        String shortId = UUID.randomUUID().toString().substring(0, 4).toLowerCase();

        if (baseName.isEmpty()) {
            baseName = "cad";
        }
        String name = baseName + "_" + timestamp + "_" + shortId;
        return extension.isEmpty() ? name : name + "." + extension;
    }

    /**
     * 清理文件名中 Windows 不允许的字符（\/:*?"<>| 与控制字符），
     * 连续空白压缩为下划线、去除结尾点/空格/下划线，并限制长度，
     * 避免生成过长的物理文件名。
     */
    public static String sanitizeFileName(String fileName) {
        if (fileName == null || fileName.isEmpty()) {
            return "";
        }
        String cleaned = fileName
                .replaceAll("[\\\\/:*?\"<>|\\x00-\\x1F]", "_")
                .replaceAll("\\s+", "_")
                .replaceAll("_+", "_")
                .replaceAll("[._ ]+$", "");
        int maxLength = 50;
        if (cleaned.length() > maxLength) {
            cleaned = cleaned.substring(0, maxLength);
        }
        return cleaned.replaceAll("[._ ]+$", "");
    }

    public static String getFileExtension(String fileName) {
        if (fileName == null || fileName.isEmpty()) {
            return "";
        }
        int lastDotIndex = fileName.lastIndexOf(".");
        if (lastDotIndex == -1) {
            return "";
        }
        return fileName.substring(lastDotIndex + 1).toLowerCase();
    }

    public static String getFileNameWithoutExtension(String fileName) {
        if (fileName == null || fileName.isEmpty()) {
            return "";
        }
        int lastDotIndex = fileName.lastIndexOf(".");
        if (lastDotIndex == -1) {
            return fileName;
        }
        return fileName.substring(0, lastDotIndex);
    }

    public static boolean isValidCadFile(String fileName) {
        String extension = getFileExtension(fileName);
        return extension.equals("dwg") || extension.equals("dxf") || 
               extension.equals("dgn") || extension.equals("dwf");
    }

    public static String saveUploadedFile(MultipartFile file, String directory) throws IOException {
        return saveUploadedFile(file, directory, generateFileName(file.getOriginalFilename()));
    }

    public static String saveUploadedFile(MultipartFile file, String directory, String newFileName) throws IOException {
        Path filePath = Paths.get(directory, newFileName);
        Files.createDirectories(filePath.getParent());
        Files.copy(file.getInputStream(), filePath, StandardCopyOption.REPLACE_EXISTING);
        return filePath.toString();
    }

    public static byte[] readFileAsBytes(String filePath) throws IOException {
        return Files.readAllBytes(Paths.get(filePath));
    }

    public static String readFileAsString(String filePath) throws IOException {
        return readFileAsString(filePath, StandardCharsets.UTF_8);
    }

    public static String readFileAsString(String filePath, Charset charset) throws IOException {
        return Files.readString(Paths.get(filePath), charset);
    }

    public static void writeStringToFile(String content, String filePath) throws IOException {
        writeStringToFile(content, filePath, StandardCharsets.UTF_8);
    }

    public static void writeStringToFile(String content, String filePath, Charset charset) throws IOException {
        Files.writeString(Paths.get(filePath), content, charset, 
                StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING);
    }

    public static void writeBytesToFile(byte[] data, String filePath) throws IOException {
        Files.write(Paths.get(filePath), data, StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING);
    }

    public static void deleteFile(String filePath) throws IOException {
        Files.deleteIfExists(Paths.get(filePath));
    }

    public static long getFileSize(String filePath) throws IOException {
        return Files.size(Paths.get(filePath));
    }

    public static boolean fileExists(String filePath) {
        return Files.exists(Paths.get(filePath));
    }

    public static String getFileSizeReadable(long bytes) {
        if (bytes < 1024) {
            return bytes + " B";
        } else if (bytes < 1024 * 1024) {
            return String.format("%.2f KB", bytes / 1024.0);
        } else if (bytes < 1024 * 1024 * 1024) {
            return String.format("%.2f MB", bytes / (1024.0 * 1024));
        } else {
            return String.format("%.2f GB", bytes / (1024.0 * 1024 * 1024));
        }
    }
}
