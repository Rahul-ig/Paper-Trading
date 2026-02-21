package com.trading.handler;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.trading.model.ForexPrice;
import com.trading.model.LambdaResponse;
import com.trading.util.DynamoDBUtil;
import com.trading.util.HttpClientUtil;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.*;

public class ForexDataFetcher implements RequestHandler<Map<String, Object>, LambdaResponse> {
    
    private static final Logger logger = LogManager.getLogger(ForexDataFetcher.class);
    private static final ObjectMapper objectMapper = new ObjectMapper()
            .registerModule(new JavaTimeModule());
    
    private final DynamoDBUtil dynamoDBUtil;
    private final List<String> forexPairs;
    
    public ForexDataFetcher() {
        this.dynamoDBUtil = new DynamoDBUtil();
        this.forexPairs = Arrays.asList(
            "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", 
            "NZDUSD", "EURGBP", "EURJPY", "GBPJPY", "CHFJPY", "EURCHF",
            "AUDCHF", "CADCHF", "NZDCHF", "AUDCAD", "AUDNZD", "AUDGBP"
        );
    }
    
    @Override
    public LambdaResponse handleRequest(Map<String, Object> input, Context context) {
        logger.info("ForexDataFetcher Lambda invoked with input: {}", input);
        
        try {
            List<ForexPrice> fetchedPrices = new ArrayList<>();
            
            // Fetch from multiple forex data sources
            fetchedPrices.addAll(fetchFromForexAPI());
            fetchedPrices.addAll(fetchFromExchangeRatesAPI());
            
            // Save all fetched data to DynamoDB
            int savedCount = 0;
            for (ForexPrice price : fetchedPrices) {
                if (dynamoDBUtil.saveForexPrice(price)) {
                    savedCount++;
                }
            }
            
            Map<String, Object> response = new HashMap<>();
            response.put("message", "Forex data fetched successfully");
            response.put("totalFetched", fetchedPrices.size());
            response.put("savedToDynamoDB", savedCount);
            response.put("timestamp", Instant.now().toString());
            response.put("pairs", forexPairs);
            
            logger.info("Successfully fetched {} forex prices, saved {} to DynamoDB", 
                fetchedPrices.size(), savedCount);
            
            return LambdaResponse.success(response);
            
        } catch (Exception e) {
            logger.error("Error in ForexDataFetcher: {}", e.getMessage(), e);
            return LambdaResponse.error(500, "Error fetching forex data: " + e.getMessage());
        }
    }
    
    private List<ForexPrice> fetchFromForexAPI() {
        List<ForexPrice> prices = new ArrayList<>();
        
        try {
            // Using Forex API (free tier available)
            // You can get API key from https://fixer.io/ or similar service
            String apiKey = System.getenv("FOREX_API_KEY");
            
            if (apiKey == null || apiKey.isEmpty()) {
                logger.warn("FOREX_API_KEY not found, skipping Forex API");
                return prices;
            }
            
            String baseCurrency = "USD";
            String symbols = String.join(",", getTargetCurrencies());
            
            String url = "https://data.fixer.io/api/latest?access_key=%s&base=%s&symbols=%s".formatted(
                    apiKey, baseCurrency, symbols
            );
            
            String response = HttpClientUtil.getRequestWithRetry(url, null, 3);
            if (response != null && !response.isEmpty()) {
                prices.addAll(parseFixerResponse(response, baseCurrency));
            }
            
        } catch (Exception e) {
            logger.error("Error fetching from Forex API: {}", e.getMessage());
        }
        
        return prices;
    }
    
    private List<ForexPrice> fetchFromExchangeRatesAPI() {
        List<ForexPrice> prices = new ArrayList<>();
        
        try {
            // Using exchangerate-api.com (free tier available)
            String baseCurrency = "USD";
            String url = "https://api.exchangerate-api.com/v4/latest/%s".formatted(baseCurrency);
            
            String response = HttpClientUtil.getRequestWithRetry(url, null, 3);
            if (response != null && !response.isEmpty()) {
                prices.addAll(parseExchangeRateAPIResponse(response, baseCurrency));
            }
            
        } catch (Exception e) {
            logger.error("Error fetching from ExchangeRates API: {}", e.getMessage());
        }
        
        return prices;
    }
    
    private List<ForexPrice> parseFixerResponse(String jsonResponse, String baseCurrency) {
        List<ForexPrice> prices = new ArrayList<>();
        
        try {
            JsonNode rootNode = objectMapper.readTree(jsonResponse);
            
            if (!rootNode.get("success").asBoolean()) {
                logger.error("Fixer API error: {}", rootNode.get("error").get("info").asText());
                return prices;
            }
            
            JsonNode rates = rootNode.get("rates");
            
            for (Iterator<Map.Entry<String, JsonNode>> it = rates.fields(); it.hasNext();) {
                Map.Entry<String, JsonNode> entry = it.next();
                String targetCurrency = entry.getKey();
                double rate = entry.getValue().asDouble();
                
                ForexPrice forexPrice = new ForexPrice();
                forexPrice.setBaseCurrency(baseCurrency);
                forexPrice.setQuoteCurrency(targetCurrency);
                forexPrice.setPair(baseCurrency + targetCurrency);
                forexPrice.setSource("Fixer.io");
                
                // For simplicity, we'll use the same rate for bid and ask
                // In real implementation, you'd get actual bid/ask spread
                BigDecimal rateDecimal = new BigDecimal(String.valueOf(rate));
                BigDecimal spread = rateDecimal.multiply(new BigDecimal("0.0002")); // 0.02% spread
                
                forexPrice.setBid(rateDecimal.subtract(spread));
                forexPrice.setAsk(rateDecimal.add(spread));
                forexPrice.setSpread(spread.multiply(new BigDecimal("2")));
                
                prices.add(forexPrice);
            }
            
        } catch (Exception e) {
            logger.error("Error parsing Fixer response: {}", e.getMessage());
        }
        
        return prices;
    }
    
    private List<ForexPrice> parseExchangeRateAPIResponse(String jsonResponse, String baseCurrency) {
        List<ForexPrice> prices = new ArrayList<>();
        
        try {
            JsonNode rootNode = objectMapper.readTree(jsonResponse);
            JsonNode rates = rootNode.get("rates");
            
            for (Iterator<Map.Entry<String, JsonNode>> it = rates.fields(); it.hasNext();) {
                Map.Entry<String, JsonNode> entry = it.next();
                String targetCurrency = entry.getKey();
                double rate = entry.getValue().asDouble();
                
                // Only process currencies we're interested in
                if (!getTargetCurrencies().contains(targetCurrency)) {
                    continue;
                }
                
                ForexPrice forexPrice = new ForexPrice();
                forexPrice.setBaseCurrency(baseCurrency);
                forexPrice.setQuoteCurrency(targetCurrency);
                forexPrice.setPair(baseCurrency + targetCurrency);
                forexPrice.setSource("ExchangeRateAPI");
                
                // Simulate bid/ask spread
                BigDecimal rateDecimal = new BigDecimal(String.valueOf(rate));
                BigDecimal spread = rateDecimal.multiply(new BigDecimal("0.0003")); // 0.03% spread
                
                forexPrice.setBid(rateDecimal.subtract(spread));
                forexPrice.setAsk(rateDecimal.add(spread));
                forexPrice.setSpread(spread.multiply(new BigDecimal("2")));
                
                prices.add(forexPrice);
                
                // Also add reverse pair (e.g., EURUSD -> USDEUR)
                if (!targetCurrency.equals("USD")) {
                    ForexPrice reversePrice = new ForexPrice();
                    reversePrice.setBaseCurrency(targetCurrency);
                    reversePrice.setQuoteCurrency(baseCurrency);
                    reversePrice.setPair(targetCurrency + baseCurrency);
                    reversePrice.setSource("ExchangeRateAPI");
                    
                    BigDecimal reverseRate = BigDecimal.ONE.divide(rateDecimal, 6, RoundingMode.HALF_UP);
                    BigDecimal reverseSpread = reverseRate.multiply(new BigDecimal("0.0003"));
                    
                    reversePrice.setBid(reverseRate.subtract(reverseSpread));
                    reversePrice.setAsk(reverseRate.add(reverseSpread));
                    reversePrice.setSpread(reverseSpread.multiply(new BigDecimal("2")));
                    
                    prices.add(reversePrice);
                }
            }
            
        } catch (Exception e) {
            logger.error("Error parsing ExchangeRateAPI response: {}", e.getMessage());
        }
        
        return prices;
    }
    
    private List<String> getTargetCurrencies() {
        Set<String> currencies = new HashSet<>();
        
        for (String pair : forexPairs) {
            if (pair.length() == 6) {
                currencies.add(pair.substring(0, 3));
                currencies.add(pair.substring(3, 6));
            }
        }
        
        return new ArrayList<>(currencies);
    }
    
    // Method to fetch historical data for past months
    public LambdaResponse fetchHistoricalData(int monthsBack, Context context) {
        logger.info("Fetching historical forex data for {} months back", monthsBack);
        
        try {
            List<ForexPrice> historicalPrices = new ArrayList<>();
            
            // This would typically involve making API calls to get historical data
            // For now, we'll implement a basic structure
            
            // Save historical data
            int savedCount = 0;
            for (ForexPrice price : historicalPrices) {
                if (dynamoDBUtil.saveForexPrice(price)) {
                    savedCount++;
                }
            }
            
            Map<String, Object> response = new HashMap<>();
            response.put("message", "Historical forex data fetched");
            response.put("monthsBack", monthsBack);
            response.put("totalFetched", historicalPrices.size());
            response.put("savedToDynamoDB", savedCount);
            response.put("timestamp", Instant.now().toString());
            
            return LambdaResponse.success(response);
            
        } catch (Exception e) {
            logger.error("Error fetching historical forex data: {}", e.getMessage(), e);
            return LambdaResponse.error(500, "Error fetching historical data: " + e.getMessage());
        }
    }
}