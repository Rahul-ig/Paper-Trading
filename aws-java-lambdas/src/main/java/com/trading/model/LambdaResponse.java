package com.trading.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;

import java.util.HashMap;
import java.util.Map;

public class LambdaResponse {

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper()
            .registerModule(new JavaTimeModule())
            .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
    
    @JsonProperty("statusCode")
    private int statusCode;
    
    @JsonProperty("body")
    private String body;
    
    @JsonProperty("headers")
    private Map<String, String> headers;
    
    @JsonProperty("isBase64Encoded")
    private boolean isBase64Encoded;

    public LambdaResponse() {
        this.headers = new HashMap<>();
        this.headers.put("Content-Type", "application/json");
        this.headers.put("Access-Control-Allow-Origin", "*");
        this.headers.put("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
        this.headers.put("Access-Control-Allow-Headers", "Content-Type");
        this.isBase64Encoded = false;
    }

    public LambdaResponse(int statusCode, String body) {
        this();
        this.statusCode = statusCode;
        this.body = body;
    }

    public static LambdaResponse success(String body) {
        return new LambdaResponse(200, body);
    }

    public static LambdaResponse success(Object data) {
        try {
            String jsonBody = OBJECT_MAPPER.writeValueAsString(data);
            return new LambdaResponse(200, jsonBody);
        } catch (Exception e) {
            return error(500, "Error serializing response: " + e.getMessage());
        }
    }

    public static LambdaResponse error(int statusCode, String message) {
        String errorBody = "{\"error\": \"%s\"}".formatted(message);
        return new LambdaResponse(statusCode, errorBody);
    }

    // Getters and Setters
    public int getStatusCode() {
        return statusCode;
    }

    public void setStatusCode(int statusCode) {
        this.statusCode = statusCode;
    }

    public String getBody() {
        return body;
    }

    public void setBody(String body) {
        this.body = body;
    }

    public Map<String, String> getHeaders() {
        return headers;
    }

    public void setHeaders(Map<String, String> headers) {
        this.headers = headers;
    }

    public boolean isBase64Encoded() {
        return isBase64Encoded;
    }

    public void setBase64Encoded(boolean base64Encoded) {
        isBase64Encoded = base64Encoded;
    }
}