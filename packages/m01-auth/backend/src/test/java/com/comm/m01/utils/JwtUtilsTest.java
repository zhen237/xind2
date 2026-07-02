package com.comm.m01.utils;

import com.comm.utils.JwtUtils;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import static org.junit.jupiter.api.Assertions.*;

public class JwtUtilsTest {

    private JwtUtils jwtUtils;

    @BeforeEach
    public void setUp() {
        jwtUtils = new JwtUtils();
        ReflectionTestUtils.setField(jwtUtils, "secret", "test-secret-key-1234567890-abcdefghijklmnop");
        ReflectionTestUtils.setField(jwtUtils, "expiration", 3600000L);
    }

    @Test
    public void testGenerateToken() {
        String token = jwtUtils.generateToken(1L, "testuser");
        assertNotNull(token);
        assertFalse(token.isEmpty());
    }

    @Test
    public void testValidateToken() {
        String token = jwtUtils.generateToken(1L, "testuser");
        assertTrue(jwtUtils.validateToken(token));
    }

    @Test
    public void testValidateTokenWithInvalidToken() {
        assertFalse(jwtUtils.validateToken("invalid-token"));
    }

    @Test
    public void testGetUserIdFromToken() {
        String token = jwtUtils.generateToken(123L, "testuser");
        assertEquals(123L, jwtUtils.getUserIdFromToken(token));
    }

    @Test
    public void testGetUsernameFromToken() {
        String token = jwtUtils.generateToken(1L, "admin");
        assertEquals("admin", jwtUtils.getUsernameFromToken(token));
    }

    @Test
    public void testIsTokenExpired() {
        String token = jwtUtils.generateToken(1L, "testuser");
        assertFalse(jwtUtils.isTokenExpired(token));
    }
}
