package com.trading.handler;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.trading.model.CryptoPrice;
import com.trading.model.LambdaResponse;
import com.trading.util.DynamoDBUtil;
import com.trading.util.HttpClientUtil;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.*;

public class CryptoDataFetcher implements RequestHandler<Map<String, Object>, LambdaResponse> {
    
    private static final Logger logger = LogManager.getLogger(CryptoDataFetcher.class);
    private static final ObjectMapper objectMapper = new ObjectMapper()
            .registerModule(new JavaTimeModule());
    
    /** Single source of truth: symbol (uppercase) <-> CoinGecko ID mapping */
    private static final Map<String, String> SYMBOL_TO_COINGECKO_ID = Map.ofEntries(
            Map.entry("BTC", "bitcoin"),
            Map.entry("ETH", "ethereum"),
            Map.entry("ADA", "cardano"),
            Map.entry("DOT", "polkadot"),
            Map.entry("SOL", "solana"),
            Map.entry("LINK", "chainlink"),
            Map.entry("AVAX", "avalanche-2"),
            Map.entry("MATIC", "matic-network"),
            Map.entry("UNI", "uniswap"),
            Map.entry("LTC", "litecoin"),
            Map.entry("BCH", "bitcoin-cash"),
            Map.entry("XRP", "ripple"),
            Map.entry("BNB", "binancecoin"),
            Map.entry("DOGE", "dogecoin"),
            Map.entry("SHIB", "shiba-inu")
    );

    /** Reverse lookup: CoinGecko ID -> symbol, derived from SYMBOL_TO_COINGECKO_ID */
    private static final Map<String, String> COINGECKO_ID_TO_SYMBOL;
    static {
        Map<String, String> reverse = new HashMap<>();
        SYMBOL_TO_COINGECKO_ID.forEach((symbol, id) -> reverse.put(id, symbol));
        COINGECKO_ID_TO_SYMBOL = Collections.unmodifiableMap(reverse);
    }
    
    private final DynamoDBUtil dynamoDBUtil;
    private final List<String> cryptoSymbols;
    
    public CryptoDataFetcher() {
        this.dynamoDBUtil = new DynamoDBUtil();
        this.cryptoSymbols = Arrays.asList(
            "BTC", "ETH", "ADA", "DOT", "SOL", "LINK", "AVAX", "MATIC", 
            "UNI", "LTC", "BCH", "XRP", "BNB", "DOGE", "SHIB"
        );
    }
    
    @Override
    public LambdaResponse handleRequest(Map<String, Object> input, Context context) {
        logger.info("CryptoDataFetcher Lambda invoked with input: {}", input);
        
        try {
            List<CryptoPrice> fetchedPrices = new ArrayList<>();
            
            // Option 1: CoinGecko API (Free tier available)
            fetchedPrices.addAll(fetchFromCoinGecko());
            
            // Option 2: Binance API (for real-time data)
            fetchedPrices.addAll(fetchFromBinance());
            
            // Save all fetched data to DynamoDB
            int savedCount = 0;
            for (CryptoPrice price : fetchedPrices) {
                if (dynamoDBUtil.saveCryptoPrice(price)) {
                    savedCount++;
                }
            }
            
            Map<String, Object> response = new HashMap<>();
            response.put("message", "Crypto data fetched successfully");
            response.put("totalFetched", fetchedPrices.size());
            response.put("savedToDynamoDB", savedCount);
            response.put("timestamp", Instant.now().toString());
            response.put("symbols", cryptoSymbols);
            
            logger.info("Successfully fetched {} crypto prices, saved {} to DynamoDB", 
                fetchedPrices.size(), savedCount);
            
            return LambdaResponse.success(response);
            
        } catch (Exception e) {
            logger.error("Error in CryptoDataFetcher: {}", e.getMessage(), e);
            return LambdaResponse.error(500, "Error fetching crypto data: " + e.getMessage());
        }
    }
    
    private List<CryptoPrice> fetchFromCoinGecko() {
        List<CryptoPrice> prices = new ArrayList<>();
        
        try {
            // CoinGecko API endpoint for multiple cryptocurrencies
            String symbolsList = String.join(",", cryptoSymbols.stream()
                .map(s -> s.toLowerCase())
                .toArray(String[]::new));
            
            String url = (
                    "https://api.coingecko.com/api/v3/simple/price?" +
                            "ids=%s&vs_currencies=usd&include_market_cap=true&include_24hr_vol=true&" +
                            "include_24hr_change=true&include_last_updated_at=true").formatted(
                    convertSymbolsToIds(symbolsList)
            );
            
            Map<String, String> headers = new HashMap<>();
            // Add API key if you have one
            String apiKey = System.getenv("COINGECKO_API_KEY");
            if (apiKey != null && !apiKey.isEmpty()) {
                headers.put("x-cg-demo-api-key", apiKey);
            }
            
            String response = HttpClientUtil.getRequestWithRetry(url, headers, 3);
            if (response != null && !response.isEmpty()) {
                prices.addAll(parseCoinGeckoResponse(response));
            }
            
        } catch (Exception e) {
            logger.error("Error fetching from CoinGecko: {}", e.getMessage());
        }
        
        return prices;
    }
    
    private List<CryptoPrice> fetchFromBinance() {
        List<CryptoPrice> prices = new ArrayList<>();
        
        try {
            // Binance API endpoint for 24hr ticker statistics
            String url = "https://api.binance.com/api/v3/ticker/24hr";
            
            String response = HttpClientUtil.getRequestWithRetry(url, null, 3);
            if (response != null && !response.isEmpty()) {
                prices.addAll(parseBinanceResponse(response));
            }
            
        } catch (Exception e) {
            logger.error("Error fetching from Binance: {}", e.getMessage());
        }
        
        return prices;
    }
    
    private List<CryptoPrice> parseCoinGeckoResponse(String jsonResponse) {
        List<CryptoPrice> prices = new ArrayList<>();
        
        try {
            JsonNode rootNode = objectMapper.readTree(jsonResponse);
            
            for (Iterator<Map.Entry<String, JsonNode>> it = rootNode.fields(); it.hasNext();) {
                Map.Entry<String, JsonNode> entry = it.next();
                String coinId = entry.getKey();
                JsonNode data = entry.getValue();
                
                String symbol = getSymbolFromCoinId(coinId).toUpperCase();
                
                CryptoPrice cryptoPrice = new CryptoPrice();
                cryptoPrice.setSymbol(symbol);
                cryptoPrice.setSource("CoinGecko");
                
                if (data.has("usd")) {
                    cryptoPrice.setPrice(new BigDecimal(data.get("usd").asText()));
                }
                if (data.has("usd_market_cap")) {
                    cryptoPrice.setMarketCap(new BigDecimal(data.get("usd_market_cap").asText()));
                }
                if (data.has("usd_24h_vol")) {
                    cryptoPrice.setVolume(new BigDecimal(data.get("usd_24h_vol").asText()));
                }
                if (data.has("usd_24h_change")) {
                    cryptoPrice.setPriceChangePercent24h(new BigDecimal(data.get("usd_24h_change").asText()));
                }
                
                prices.add(cryptoPrice);
            }
            
        } catch (Exception e) {
            logger.error("Error parsing CoinGecko response: {}", e.getMessage());
        }
        
        return prices;
    }
    
    private List<CryptoPrice> parseBinanceResponse(String jsonResponse) {
        List<CryptoPrice> prices = new ArrayList<>();
        
        try {
            JsonNode rootNode = objectMapper.readTree(jsonResponse);
            
            for (JsonNode ticker : rootNode) {
                String symbol = ticker.get("symbol").asText();
                
                // Filter only USDT pairs for major cryptocurrencies
                if (!symbol.endsWith("USDT") || !isMajorCrypto(symbol.replace("USDT", ""))) {
                    continue;
                }
                
                String baseSymbol = symbol.replace("USDT", "");
                
                CryptoPrice cryptoPrice = new CryptoPrice();
                cryptoPrice.setSymbol(baseSymbol);
                cryptoPrice.setSource("Binance");
                
                if (ticker.has("lastPrice")) {
                    cryptoPrice.setPrice(new BigDecimal(ticker.get("lastPrice").asText()));
                }
                if (ticker.has("volume")) {
                    cryptoPrice.setVolume(new BigDecimal(ticker.get("volume").asText()));
                }
                if (ticker.has("highPrice")) {
                    cryptoPrice.setHigh24h(new BigDecimal(ticker.get("highPrice").asText()));
                }
                if (ticker.has("lowPrice")) {
                    cryptoPrice.setLow24h(new BigDecimal(ticker.get("lowPrice").asText()));
                }
                if (ticker.has("priceChange")) {
                    cryptoPrice.setPriceChange24h(new BigDecimal(ticker.get("priceChange").asText()));
                }
                if (ticker.has("priceChangePercent")) {
                    cryptoPrice.setPriceChangePercent24h(new BigDecimal(ticker.get("priceChangePercent").asText()));
                }
                
                prices.add(cryptoPrice);
            }
            
        } catch (Exception e) {
            logger.error("Error parsing Binance response: {}", e.getMessage());
        }
        
        return prices;
    }
    
    private String convertSymbolsToIds(String symbols) {
        String[] symbolArray = symbols.split(",");
        List<String> ids = new ArrayList<>();
        
        for (String symbol : symbolArray) {
            String id = SYMBOL_TO_COINGECKO_ID.get(symbol.trim().toUpperCase());
            if (id != null) {
                ids.add(id);
            }
        }
        
        return String.join(",", ids);
    }
    
    private String getSymbolFromCoinId(String coinId) {
        return COINGECKO_ID_TO_SYMBOL.getOrDefault(coinId, coinId.toUpperCase());
    }
    
    private boolean isMajorCrypto(String symbol) {
        return cryptoSymbols.contains(symbol);
    }
}