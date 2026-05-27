package com.comm.m04.config;

import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Configuration;

import javax.sql.DataSource;
import java.sql.*;

@Configuration
public class DataSourceConfig {

    @Autowired
    private DataSource dataSource;

    @PostConstruct
    public void init() {
        try (Connection conn = dataSource.getConnection()) {
            conn.setAutoCommit(false);
            try {
                createTables(conn);
                insertSampleData(conn);
                conn.commit();
                System.out.println("Database initialization completed successfully");
            } catch (SQLException e) {
                conn.rollback();
                throw e;
            }
        } catch (SQLException e) {
            System.out.println("Error initializing database:");
            e.printStackTrace();
        }
    }

    private void createTables(Connection conn) throws SQLException {
        String taskTableSQL = "CREATE TABLE IF NOT EXISTS m04_acceptance_task (" +
            "id BIGINT AUTO_INCREMENT PRIMARY KEY, " +
            "project_id BIGINT, " +
            "task_name VARCHAR(200) NOT NULL, " +
            "task_type VARCHAR(50), " +
            "status INT DEFAULT 0, " +
            "acceptance_standard TEXT, " +
            "result_description TEXT, " +
            "problem_count INT DEFAULT 0, " +
            "acceptance_by BIGINT, " +
            "acceptance_time DATETIME, " +
            "create_time DATETIME DEFAULT CURRENT_TIMESTAMP, " +
            "update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, " +
            "INDEX idx_project_id (project_id), " +
            "INDEX idx_status (status) " +
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";

        String problemTableSQL = "CREATE TABLE IF NOT EXISTS m04_acceptance_problem (" +
            "id BIGINT AUTO_INCREMENT PRIMARY KEY, " +
            "task_id BIGINT NOT NULL, " +
            "problem_title VARCHAR(200) NOT NULL, " +
            "problem_level INT DEFAULT 1, " +
            "problem_description TEXT, " +
            "photo_path VARCHAR(500), " +
            "status INT DEFAULT 0, " +
            "rectify_deadline DATE, " +
            "rectify_result TEXT, " +
            "rectify_by BIGINT, " +
            "review_by BIGINT, " +
            "create_time DATETIME DEFAULT CURRENT_TIMESTAMP, " +
            "update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, " +
            "INDEX idx_task_id (task_id), " +
            "INDEX idx_status (status) " +
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";

        try (Statement stmt = conn.createStatement()) {
            stmt.executeUpdate("DROP TABLE IF EXISTS m04_acceptance_task");
            stmt.executeUpdate("DROP TABLE IF EXISTS m04_acceptance_problem");
            stmt.executeUpdate(taskTableSQL);
            stmt.executeUpdate(problemTableSQL);
        }
    }

    private void insertSampleData(Connection conn) throws SQLException {
        String insertTaskSQL = "INSERT INTO m04_acceptance_task (project_id, task_name, task_type, status, acceptance_standard, result_description, problem_count) VALUES (?, ?, ?, ?, ?, ?, ?)";
        
        try (PreparedStatement pstmt = conn.prepareStatement(insertTaskSQL)) {
            pstmt.setLong(1, 1);
            pstmt.setString(2, "Device Installation Acceptance");
            pstmt.setString(3, "Device");
            pstmt.setInt(4, 1);
            pstmt.setString(5, "Device installation position is accurate, fixed firmly, wiring correct");
            pstmt.setString(6, "");
            pstmt.setInt(7, 2);
            pstmt.executeUpdate();

            pstmt.setLong(1, 1);
            pstmt.setString(2, "Software Function Acceptance");
            pstmt.setString(3, "Software");
            pstmt.setInt(4, 0);
            pstmt.setString(5, "All function modules running normally, interface calls normal");
            pstmt.setString(6, "");
            pstmt.setInt(7, 0);
            pstmt.executeUpdate();

            pstmt.setLong(1, 2);
            pstmt.setString(2, "Network Cabling Acceptance");
            pstmt.setString(3, "Engineering");
            pstmt.setInt(4, 2);
            pstmt.setString(5, "Cabling specification, clear labels, test passed");
            pstmt.setString(6, "Acceptance passed, meets standards");
            pstmt.setInt(7, 0);
            pstmt.executeUpdate();

            pstmt.setLong(1, 3);
            pstmt.setString(2, "System Integration Acceptance");
            pstmt.setString(3, "Integration");
            pstmt.setInt(4, 1);
            pstmt.setString(5, "All subsystems working together normally");
            pstmt.setString(6, "");
            pstmt.setInt(7, 1);
            pstmt.executeUpdate();

            pstmt.setLong(1, 2);
            pstmt.setString(2, "Server Room Environment Acceptance");
            pstmt.setInt(4, 0);
            pstmt.setString(3, "Environment");
            pstmt.setString(5, "Temperature, humidity, power supply meet requirements");
            pstmt.setString(6, "");
            pstmt.setInt(7, 0);
            pstmt.executeUpdate();
        }

        String insertProblemSQL = "INSERT INTO m04_acceptance_problem (task_id, problem_title, problem_level, problem_description, status, rectify_deadline) VALUES (?, ?, ?, ?, ?, ?)";
        
        try (PreparedStatement pstmt = conn.prepareStatement(insertProblemSQL)) {
            pstmt.setLong(1, 1);
            pstmt.setString(2, "Improper grounding");
            pstmt.setInt(3, 2);
            pstmt.setString(4, "Grounding resistance exceeds standard, needs re-grounding");
            pstmt.setInt(5, 1);
            pstmt.setDate(6, Date.valueOf("2026-06-10"));
            pstmt.executeUpdate();

            pstmt.setLong(1, 1);
            pstmt.setString(2, "Missing cable labels");
            pstmt.setInt(3, 1);
            pstmt.setString(4, "Some cables missing identification labels");
            pstmt.setInt(5, 0);
            pstmt.setDate(6, Date.valueOf("2026-06-08"));
            pstmt.executeUpdate();

            pstmt.setLong(1, 4);
            pstmt.setString(2, "System response delay");
            pstmt.setInt(3, 3);
            pstmt.setString(4, "Core module response time exceeds 3 seconds, needs optimization");
            pstmt.setInt(5, 0);
            pstmt.setDate(6, Date.valueOf("2026-06-15"));
            pstmt.executeUpdate();
        }
    }
}