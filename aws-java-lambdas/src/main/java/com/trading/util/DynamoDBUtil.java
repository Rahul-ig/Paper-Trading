package com.trading.util;

import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.dynamodb.DynamoDbClient;
import software.amazon.awssdk.services.dynamodb.model.AttributeValue;
import software.amazon.awssdk.services.dynamodb.model.PutItemRequest;
import software.amazon.awssdk.services.dynamodb.model.PutItemResponse;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.trading.model.CryptoPrice;
import com.trading.model.ForexPrice;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.util.HashMap;
import java.util.Map;

public class DynamoDBUtil {
    
    private static final Logger logger = LogManager.getLogger(DynamoDBUtil.class);
    private static final ObjectMapper objectMapper = new ObjectMapper()
            .registerModule(new JavaTimeModule());
    
    private final DynamoDbClient dynamoDbClient;
    private final String cryptoTableName;
    private final String forexTableName;
    
    public DynamoDBUtil() {
        this.dynamoDbClient = DynamoDbClient.builder()
                .region(Region.of(System.getenv().getOrDefault("AWS_REGION", "us-east-1")))
                .build();
        
        this.cryptoTableName = System.getenv().getOrDefault("DYNAMODB_CRYPTO_TABLE", "CryptoPriceData");
        this.forexTableName = System.getenv().getOrDefault("DYNAMODB_FOREX_TABLE", "ForexPriceData");
    }
    
    public boolean saveCryptoPrice(CryptoPrice cryptoPrice) {
        try {
            Map<String, AttributeValue> item = new HashMap<>();
            item.put("symbol", AttributeValue.builder().s(cryptoPrice.getSymbol()).build());
            item.put("timestamp", AttributeValue.builder().s(cryptoPrice.getTimestamp().toString()).build());
            item.put("price", AttributeValue.builder().n(cryptoPrice.getPrice().toString()).build());
            
            if (cryptoPrice.getVolume() != null) {
                item.put("volume", AttributeValue.builder().n(cryptoPrice.getVolume().toString()).build());
            }
            if (cryptoPrice.getMarketCap() != null) {
                item.put("marketCap", AttributeValue.builder().n(cryptoPrice.getMarketCap().toString()).build());
            }
            if (cryptoPrice.getPriceChange24h() != null) {
                item.put("priceChange24h", AttributeValue.builder().n(cryptoPrice.getPriceChange24h().toString()).build());
            }
            if (cryptoPrice.getPriceChangePercent24h() != null) {
                item.put("priceChangePercent24h", AttributeValue.builder().n(cryptoPrice.getPriceChangePercent24h().toString()).build());
            }
            if (cryptoPrice.getHigh24h() != null) {
                item.put("high24h", AttributeValue.builder().n(cryptoPrice.getHigh24h().toString()).build());
            }
            if (cryptoPrice.getLow24h() != null) {
                item.put("low24h", AttributeValue.builder().n(cryptoPrice.getLow24h().toString()).build());
            }
            if (cryptoPrice.getSource() != null) {
                item.put("source", AttributeValue.builder().s(cryptoPrice.getSource()).build());
            }
            
            // Add full JSON data
            String jsonData = objectMapper.writeValueAsString(cryptoPrice);
            item.put("data", AttributeValue.builder().s(jsonData).build());
            
            PutItemRequest request = PutItemRequest.builder()
                    .tableName(cryptoTableName)
                    .item(item)
                    .build();
            
            PutItemResponse response = dynamoDbClient.putItem(request);
            logger.info("Successfully saved crypto price for {}: {}", cryptoPrice.getSymbol(), response.sdkHttpResponse().statusCode());
            return true;
            
        } catch (Exception e) {
            logger.error("Error saving crypto price for {}: {}", cryptoPrice.getSymbol(), e.getMessage());
            return false;
        }
    }
    
    public boolean saveForexPrice(ForexPrice forexPrice) {
        try {
            Map<String, AttributeValue> item = new HashMap<>();
            item.put("pair", AttributeValue.builder().s(forexPrice.getPair()).build());
            item.put("timestamp", AttributeValue.builder().s(forexPrice.getTimestamp().toString()).build());
            item.put("bid", AttributeValue.builder().n(forexPrice.getBid().toString()).build());
            item.put("ask", AttributeValue.builder().n(forexPrice.getAsk().toString()).build());
            
            if (forexPrice.getSpread() != null) {
                item.put("spread", AttributeValue.builder().n(forexPrice.getSpread().toString()).build());
            }
            if (forexPrice.getHigh24h() != null) {
                item.put("high24h", AttributeValue.builder().n(forexPrice.getHigh24h().toString()).build());
            }
            if (forexPrice.getLow24h() != null) {
                item.put("low24h", AttributeValue.builder().n(forexPrice.getLow24h().toString()).build());
            }
            if (forexPrice.getPriceChange24h() != null) {
                item.put("priceChange24h", AttributeValue.builder().n(forexPrice.getPriceChange24h().toString()).build());
            }
            if (forexPrice.getPriceChangePercent24h() != null) {
                item.put("priceChangePercent24h", AttributeValue.builder().n(forexPrice.getPriceChangePercent24h().toString()).build());
            }
            if (forexPrice.getSource() != null) {
                item.put("source", AttributeValue.builder().s(forexPrice.getSource()).build());
            }
            
            // Add full JSON data
            String jsonData = objectMapper.writeValueAsString(forexPrice);
            item.put("data", AttributeValue.builder().s(jsonData).build());
            
            PutItemRequest request = PutItemRequest.builder()
                    .tableName(forexTableName)
                    .item(item)
                    .build();
            
            PutItemResponse response = dynamoDbClient.putItem(request);
            logger.info("Successfully saved forex price for {}: {}", forexPrice.getPair(), response.sdkHttpResponse().statusCode());
            return true;
            
        } catch (Exception e) {
            logger.error("Error saving forex price for {}: {}", forexPrice.getPair(), e.getMessage());
            return false;
        }
    }
    
    public void close() {
        if (dynamoDbClient != null) {
            dynamoDbClient.close();
        }
    }
}