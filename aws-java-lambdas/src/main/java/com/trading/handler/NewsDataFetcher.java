package com.trading.handler;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.trading.model.LambdaResponse;
import com.trading.util.HttpClientUtil;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.dynamodb.DynamoDbClient;
import software.amazon.awssdk.services.dynamodb.model.AttributeValue;
import software.amazon.awssdk.services.dynamodb.model.PutItemRequest;

import java.time.Instant;
import java.util.*;

public class NewsDataFetcher implements RequestHandler<Map<String, Object>, LambdaResponse> {
    
    private static final Logger logger = LogManager.getLogger(NewsDataFetcher.class);
    private static final ObjectMapper objectMapper = new ObjectMapper()
            .registerModule(new JavaTimeModule());
    
    private final List<String> newsCategories;
    private final DynamoDbClient dynamoDbClient;
    private final String newsTableName;
    
    public NewsDataFetcher() {
        this.newsCategories = Arrays.asList(
            "cryptocurrency", "forex", "trading", "finance", "market", "economy"
        );
        this.dynamoDbClient = DynamoDbClient.builder()
                .region(Region.of(System.getenv().getOrDefault("AWS_REGION", "us-east-1")))
                .build();
        this.newsTableName = System.getenv().getOrDefault("DYNAMODB_NEWS_TABLE", "NewsData");
    }
    
    @Override
    public LambdaResponse handleRequest(Map<String, Object> input, Context context) {
        logger.info("NewsDataFetcher Lambda invoked with input: {}", input);
        
        try {
            List<Map<String, Object>> allNews = new ArrayList<>();
            
            // Fetch from multiple news sources
            allNews.addAll(fetchFromNewsAPI());
            allNews.addAll(fetchFromAlphaVantageNews());
            
            // Save news data to DynamoDB (you'd need a news table)
            int savedCount = saveNewsData(allNews);
            
            Map<String, Object> response = new HashMap<>();
            response.put("message", "News data fetched successfully");
            response.put("totalFetched", allNews.size());
            response.put("savedToDynamoDB", savedCount);
            response.put("timestamp", Instant.now().toString());
            response.put("categories", newsCategories);
            
            logger.info("Successfully fetched {} news articles, saved {} to DynamoDB", 
                allNews.size(), savedCount);
            
            return LambdaResponse.success(response);
            
        } catch (Exception e) {
            logger.error("Error in NewsDataFetcher: {}", e.getMessage(), e);
            return LambdaResponse.error(500, "Error fetching news data: " + e.getMessage());
        }
    }
    
    private List<Map<String, Object>> fetchFromNewsAPI() {
        List<Map<String, Object>> newsList = new ArrayList<>();
        
        try {
            String apiKey = System.getenv("NEWS_API_KEY");
            
            if (apiKey == null || apiKey.isEmpty()) {
                logger.warn("NEWS_API_KEY not found, skipping News API");
                return newsList;
            }
            
            for (String category : newsCategories) {
                String url = "https://newsapi.org/v2/everything?q=%s&language=en&sortBy=publishedAt&pageSize=10&apiKey=%s".formatted(
                        category, apiKey
                );
                
                Map<String, String> headers = new HashMap<>();
                headers.put("X-Api-Key", apiKey);
                
                String response = HttpClientUtil.getRequestWithRetry(url, headers, 3);
                if (response != null && !response.isEmpty()) {
                    newsList.addAll(parseNewsAPIResponse(response, category));
                }
                
                // Add delay to respect API rate limits
                Thread.sleep(1000);
            }
            
        } catch (Exception e) {
            logger.error("Error fetching from News API: {}", e.getMessage());
        }
        
        return newsList;
    }
    
    private List<Map<String, Object>> fetchFromAlphaVantageNews() {
        List<Map<String, Object>> newsList = new ArrayList<>();
        
        try {
            String apiKey = System.getenv("ALPHA_VANTAGE_API_KEY");
            
            if (apiKey == null || apiKey.isEmpty()) {
                logger.warn("ALPHA_VANTAGE_API_KEY not found, skipping Alpha Vantage News");
                return newsList;
            }
            
            // Alpha Vantage News & Sentiment API
            String url = "https://www.alphavantage.co/query?function=NEWS_SENTIMENT&topics=finance&apikey=%s&sort=LATEST&limit=50".formatted(
                    apiKey
            );
            
            String response = HttpClientUtil.getRequestWithRetry(url, null, 3);
            if (response != null && !response.isEmpty()) {
                newsList.addAll(parseAlphaVantageResponse(response));
            }
            
        } catch (Exception e) {
            logger.error("Error fetching from Alpha Vantage: {}", e.getMessage());
        }
        
        return newsList;
    }
    
    private List<Map<String, Object>> parseNewsAPIResponse(String jsonResponse, String category) {
        List<Map<String, Object>> newsList = new ArrayList<>();
        
        try {
            JsonNode rootNode = objectMapper.readTree(jsonResponse);
            
            if (!rootNode.get("status").asText().equals("ok")) {
                logger.error("NewsAPI error: {}", rootNode.toString());
                return newsList;
            }
            
            JsonNode articles = rootNode.get("articles");
            
            for (JsonNode article : articles) {
                Map<String, Object> newsItem = new HashMap<>();
                
                newsItem.put("id", UUID.randomUUID().toString());
                newsItem.put("source", "NewsAPI");
                newsItem.put("category", category);
                newsItem.put("title", article.has("title") ? article.get("title").asText() : "");
                newsItem.put("description", article.has("description") ? article.get("description").asText() : "");
                newsItem.put("content", article.has("content") ? article.get("content").asText() : "");
                newsItem.put("url", article.has("url") ? article.get("url").asText() : "");
                newsItem.put("publishedAt", article.has("publishedAt") ? article.get("publishedAt").asText() : "");
                newsItem.put("author", article.has("author") ? article.get("author").asText() : "");
                newsItem.put("urlToImage", article.has("urlToImage") ? article.get("urlToImage").asText() : "");
                newsItem.put("timestamp", Instant.now().toString());
                
                if (article.has("source") && article.get("source").has("name")) {
                    newsItem.put("sourceName", article.get("source").get("name").asText());
                }
                
                newsList.add(newsItem);
            }
            
        } catch (Exception e) {
            logger.error("Error parsing NewsAPI response: {}", e.getMessage());
        }
        
        return newsList;
    }
    
    private List<Map<String, Object>> parseAlphaVantageResponse(String jsonResponse) {
        List<Map<String, Object>> newsList = new ArrayList<>();
        
        try {
            JsonNode rootNode = objectMapper.readTree(jsonResponse);
            
            if (rootNode.has("feed")) {
                JsonNode feed = rootNode.get("feed");
                
                for (JsonNode item : feed) {
                    Map<String, Object> newsItem = new HashMap<>();
                    
                    newsItem.put("id", UUID.randomUUID().toString());
                    newsItem.put("source", "AlphaVantage");
                    newsItem.put("category", "finance");
                    newsItem.put("title", item.has("title") ? item.get("title").asText() : "");
                    newsItem.put("summary", item.has("summary") ? item.get("summary").asText() : "");
                    newsItem.put("url", item.has("url") ? item.get("url").asText() : "");
                    newsItem.put("publishedAt", item.has("time_published") ? item.get("time_published").asText() : "");
                    newsItem.put("overallSentiment", item.has("overall_sentiment_score") ? item.get("overall_sentiment_score").asDouble() : 0.0);
                    newsItem.put("overallSentimentLabel", item.has("overall_sentiment_label") ? item.get("overall_sentiment_label").asText() : "");
                    newsItem.put("timestamp", Instant.now().toString());
                    
                    if (item.has("authors")) {
                        JsonNode authors = item.get("authors");
                        if (authors.isArray() && authors.size() > 0) {
                            newsItem.put("author", authors.get(0).asText());
                        }
                    }
                    
                    // Extract ticker sentiment if available
                    if (item.has("ticker_sentiment")) {
                        JsonNode tickerSentiment = item.get("ticker_sentiment");
                        newsItem.put("tickerSentiment", tickerSentiment.toString());
                    }
                    
                    newsList.add(newsItem);
                }
            }
            
        } catch (Exception e) {
            logger.error("Error parsing Alpha Vantage response: {}", e.getMessage());
        }
        
        return newsList;
    }
    
    private int saveNewsData(List<Map<String, Object>> newsList) {
        int savedCount = 0;
        
        for (Map<String, Object> newsItem : newsList) {
            try {
                Map<String, AttributeValue> item = new HashMap<>();
                item.put("newsId", AttributeValue.builder()
                        .s(String.valueOf(newsItem.getOrDefault("id", UUID.randomUUID().toString()))).build());
                item.put("timestamp", AttributeValue.builder()
                        .s(String.valueOf(newsItem.getOrDefault("timestamp", Instant.now().toString()))).build());
                item.put("category", AttributeValue.builder()
                        .s(String.valueOf(newsItem.getOrDefault("category", "general"))).build());
                item.put("title", AttributeValue.builder()
                        .s(String.valueOf(newsItem.getOrDefault("title", ""))).build());
                item.put("source", AttributeValue.builder()
                        .s(String.valueOf(newsItem.getOrDefault("source", "unknown"))).build());

                // Optional fields
                if (newsItem.containsKey("description")) {
                    item.put("description", AttributeValue.builder()
                            .s(String.valueOf(newsItem.get("description"))).build());
                }
                if (newsItem.containsKey("url")) {
                    item.put("url", AttributeValue.builder()
                            .s(String.valueOf(newsItem.get("url"))).build());
                }
                if (newsItem.containsKey("publishedAt")) {
                    item.put("publishedAt", AttributeValue.builder()
                            .s(String.valueOf(newsItem.get("publishedAt"))).build());
                }
                if (newsItem.containsKey("overallSentiment")) {
                    item.put("sentimentScore", AttributeValue.builder()
                            .n(String.valueOf(newsItem.get("overallSentiment"))).build());
                }
                if (newsItem.containsKey("overallSentimentLabel")) {
                    item.put("sentimentLabel", AttributeValue.builder()
                            .s(String.valueOf(newsItem.get("overallSentimentLabel"))).build());
                }

                // TTL: 30 days from now
                long ttl = Instant.now().plusSeconds(30L * 24 * 60 * 60).getEpochSecond();
                item.put("ttl", AttributeValue.builder().n(String.valueOf(ttl)).build());

                // Store full JSON
                String jsonData = objectMapper.writeValueAsString(newsItem);
                item.put("data", AttributeValue.builder().s(jsonData).build());

                PutItemRequest request = PutItemRequest.builder()
                        .tableName(newsTableName)
                        .item(item)
                        .build();

                dynamoDbClient.putItem(request);
                savedCount++;
            } catch (Exception e) {
                logger.error("Error saving news item '{}': {}", newsItem.get("title"), e.getMessage());
            }
        }
        
        logger.info("Saved {}/{} news items to DynamoDB table {}", savedCount, newsList.size(), newsTableName);
        
        return savedCount;
    }
}