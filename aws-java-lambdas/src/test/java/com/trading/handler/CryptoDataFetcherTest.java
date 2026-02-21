package com.trading.handler;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class CryptoDataFetcherTest {

    @Test
    void symbolToCoingeckoIdMap_containsAllExpectedSymbols() throws Exception {
        Field field = CryptoDataFetcher.class.getDeclaredField("SYMBOL_TO_COINGECKO_ID");
        field.setAccessible(true);
        @SuppressWarnings("unchecked")
        Map<String, String> symbolMap = (Map<String, String>) field.get(null);

        assertEquals(15, symbolMap.size(), "Expected 15 crypto symbols");

        // Verify key mappings
        assertEquals("bitcoin", symbolMap.get("BTC"));
        assertEquals("ethereum", symbolMap.get("ETH"));
        assertEquals("cardano", symbolMap.get("ADA"));
        assertEquals("solana", symbolMap.get("SOL"));
        assertEquals("polkadot", symbolMap.get("DOT"));
        assertEquals("chainlink", symbolMap.get("LINK"));
        assertEquals("avalanche-2", symbolMap.get("AVAX"));
        assertEquals("matic-network", symbolMap.get("MATIC"));
        assertEquals("uniswap", symbolMap.get("UNI"));
        assertEquals("litecoin", symbolMap.get("LTC"));
        assertEquals("bitcoin-cash", symbolMap.get("BCH"));
        assertEquals("ripple", symbolMap.get("XRP"));
        assertEquals("binancecoin", symbolMap.get("BNB"));
        assertEquals("dogecoin", symbolMap.get("DOGE"));
        assertEquals("shiba-inu", symbolMap.get("SHIB"));
    }

    @Test
    void reverseMap_matchesForwardMap() throws Exception {
        Field forwardField = CryptoDataFetcher.class.getDeclaredField("SYMBOL_TO_COINGECKO_ID");
        forwardField.setAccessible(true);
        @SuppressWarnings("unchecked")
        Map<String, String> forwardMap = (Map<String, String>) forwardField.get(null);

        Field reverseField = CryptoDataFetcher.class.getDeclaredField("COINGECKO_ID_TO_SYMBOL");
        reverseField.setAccessible(true);
        @SuppressWarnings("unchecked")
        Map<String, String> reverseMap = (Map<String, String>) reverseField.get(null);

        assertEquals(forwardMap.size(), reverseMap.size(), "Forward and reverse maps should be same size");

        // Every forward entry should have a matching reverse entry
        for (Map.Entry<String, String> entry : forwardMap.entrySet()) {
            String symbol = entry.getKey();
            String coingeckoId = entry.getValue();
            assertEquals(symbol, reverseMap.get(coingeckoId),
                    "Reverse lookup for " + coingeckoId + " should return " + symbol);
        }
    }

    @Test
    void symbolToCoingeckoIdMap_isImmutable() throws Exception {
        Field field = CryptoDataFetcher.class.getDeclaredField("SYMBOL_TO_COINGECKO_ID");
        field.setAccessible(true);
        @SuppressWarnings("unchecked")
        Map<String, String> symbolMap = (Map<String, String>) field.get(null);

        assertThrows(UnsupportedOperationException.class, () -> symbolMap.put("TEST", "test-coin"));
    }

    @Test
    void reverseMap_isImmutable() throws Exception {
        Field field = CryptoDataFetcher.class.getDeclaredField("COINGECKO_ID_TO_SYMBOL");
        field.setAccessible(true);
        @SuppressWarnings("unchecked")
        Map<String, String> reverseMap = (Map<String, String>) field.get(null);

        assertThrows(UnsupportedOperationException.class, () -> reverseMap.put("test", "TEST"));
    }
}
