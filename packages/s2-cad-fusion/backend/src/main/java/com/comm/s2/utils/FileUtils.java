package com.comm.s2.utils;

import org.springframework.web.multipart.MultipartFile;

import java.io.*;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.UUID;

public class FileUtils {

    public static String generateFileName(String originalName) {
        String extension = getFileExtension(originalName);
        String uuid = UUID.randomUUID().toString().replace("-", "");
        return uuid + "." + extension;
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
        String newFileName = generateFileName(file.getOriginalFilename());
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
