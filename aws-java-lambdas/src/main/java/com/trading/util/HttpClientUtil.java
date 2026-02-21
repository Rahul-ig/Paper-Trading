package com.trading.util;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.http.HttpResponse;
import org.apache.http.HttpStatus;
import org.apache.http.client.HttpClient;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.impl.client.HttpClients;
import org.apache.http.util.EntityUtils;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.io.IOException;
import java.util.Map;

public class HttpClientUtil {
    
    private static final Logger logger = LogManager.getLogger(HttpClientUtil.class);
    private static final ObjectMapper objectMapper = new ObjectMapper();
    private static final HttpClient httpClient = HttpClients.createDefault();
    
    public static String getRequest(String url, Map<String, String> headers) throws IOException {
        logger.info("Making GET request to: {}", url);
        
        HttpGet request = new HttpGet(url);
        
        // Add headers
        if (headers != null) {
            headers.forEach(request::setHeader);
        }
        
        // Set default headers
        request.setHeader("Accept", "application/json");
        request.setHeader("User-Agent", "AWS-Lambda-Trading-Bot/1.0");
        
        try {
            HttpResponse response = httpClient.execute(request);
            int statusCode = response.getStatusLine().getStatusCode();
            
            if (statusCode == HttpStatus.SC_OK) {
                String responseBody = EntityUtils.toString(response.getEntity());
                logger.info("Successful response from {}: {} characters", url, responseBody.length());
                return responseBody;
            } else {
                String errorMessage = "HTTP Error %d: %s".formatted(
                        statusCode, response.getStatusLine().getReasonPhrase());
                logger.error("Error response from {}: {}", url, errorMessage);
                throw new IOException(errorMessage);
            }
        } catch (IOException e) {
            logger.error("IOException while calling {}: {}", url, e.getMessage());
            throw e;
        }
    }
    
    public static String getRequestWithRetry(String url, Map<String, String> headers, int maxRetries) {
        int attempt = 0;
        long delay = 1000; // Start with 1 second delay
        
        while (attempt < maxRetries) {
            try {
                return getRequest(url, headers);
            } catch (IOException e) {
                attempt++;
                if (attempt >= maxRetries) {
                    logger.error("Max retries ({}) reached for URL: {}. Last error: {}", 
                        maxRetries, url, e.getMessage());
                    return null;
                }
                
                logger.warn("Attempt {}/{} failed for URL: {}. Retrying in {}ms. Error: {}", 
                    attempt, maxRetries, url, delay, e.getMessage());
                
                try {
                    Thread.sleep(delay);
                    delay *= 2; // Exponential backoff
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    logger.error("Thread interrupted during retry delay");
                    return null;
                }
            }
        }
        return null;
    }
    
    public static <T> T parseJsonResponse(String jsonResponse, Class<T> responseType) {
        try {
            return objectMapper.readValue(jsonResponse, responseType);
        } catch (Exception e) {
            logger.error("Error parsing JSON response: {}", e.getMessage());
            return null;
        }
    }
}