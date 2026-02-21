package com.trading.model;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class LambdaResponseTest {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    void defaultConstructor_setsDefaultHeaders() {
        LambdaResponse response = new LambdaResponse();

        Map<String, String> headers = response.getHeaders();
        assertNotNull(headers);
        assertEquals("application/json", headers.get("Content-Type"));
        assertEquals("*", headers.get("Access-Control-Allow-Origin"));
        assertEquals("GET, POST, OPTIONS", headers.get("Access-Control-Allow-Methods"));
        assertEquals("Content-Type", headers.get("Access-Control-Allow-Headers"));
        assertFalse(response.isBase64Encoded());
    }

    @Test
    void twoArgConstructor_setsCodeAndBody() {
        LambdaResponse response = new LambdaResponse(201, "{\"ok\":true}");

        assertEquals(201, response.getStatusCode());
        assertEquals("{\"ok\":true}", response.getBody());
        assertNotNull(response.getHeaders());
    }

    @Test
    void successString_returns200() {
        LambdaResponse response = LambdaResponse.success("hello");

        assertEquals(200, response.getStatusCode());
        assertEquals("hello", response.getBody());
    }

    @Test
    void successObject_serializesAsJson() throws Exception {
        Map<String, Object> data = new HashMap<>();
        data.put("message", "ok");
        data.put("count", 42);

        LambdaResponse response = LambdaResponse.success(data);

        assertEquals(200, response.getStatusCode());
        assertNotNull(response.getBody());

        // Verify body is valid JSON
        Map<?, ?> parsed = objectMapper.readValue(response.getBody(), Map.class);
        assertEquals("ok", parsed.get("message"));
        assertEquals(42, parsed.get("count"));
    }

    @Test
    void successObject_handlesNestedObjects() throws Exception {
        Map<String, Object> inner = Map.of("key", "value");
        Map<String, Object> outer = Map.of("nested", inner, "list", java.util.List.of(1, 2, 3));

        LambdaResponse response = LambdaResponse.success(outer);

        assertEquals(200, response.getStatusCode());
        Map<?, ?> parsed = objectMapper.readValue(response.getBody(), Map.class);
        assertNotNull(parsed.get("nested"));
        assertNotNull(parsed.get("list"));
    }

    @Test
    void error_returnsCorrectStatusAndMessage() {
        LambdaResponse response = LambdaResponse.error(404, "Not found");

        assertEquals(404, response.getStatusCode());
        assertTrue(response.getBody().contains("Not found"));
    }

    @Test
    void error_bodyIsValidJson() throws Exception {
        LambdaResponse response = LambdaResponse.error(500, "Internal error");

        Map<?, ?> parsed = objectMapper.readValue(response.getBody(), Map.class);
        assertEquals("Internal error", parsed.get("error"));
    }

    @Test
    void setters_updateValues() {
        LambdaResponse response = new LambdaResponse();

        response.setStatusCode(204);
        response.setBody("updated");
        response.setBase64Encoded(true);

        Map<String, String> customHeaders = new HashMap<>();
        customHeaders.put("X-Custom", "test");
        response.setHeaders(customHeaders);

        assertEquals(204, response.getStatusCode());
        assertEquals("updated", response.getBody());
        assertTrue(response.isBase64Encoded());
        assertEquals("test", response.getHeaders().get("X-Custom"));
    }
}
