package com.trading.model;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.Instant;

import static org.junit.jupiter.api.Assertions.*;

class CryptoPriceTest {

    @Test
    void defaultConstructor_setsTimestamp() {
        Instant before = Instant.now();
        CryptoPrice price = new CryptoPrice();
        Instant after = Instant.now();

        assertNotNull(price.getTimestamp());
        assertFalse(price.getTimestamp().isBefore(before));
        assertFalse(price.getTimestamp().isAfter(after));
    }

    @Test
    void threeArgConstructor_setsFields() {
        CryptoPrice price = new CryptoPrice("BTC", new BigDecimal("65000.50"), new BigDecimal("1234567890"));

        assertEquals("BTC", price.getSymbol());
        assertEquals(new BigDecimal("65000.50"), price.getPrice());
        assertEquals(new BigDecimal("1234567890"), price.getVolume());
        assertNotNull(price.getTimestamp());
    }

    @Test
    void settersAndGetters_workCorrectly() {
        CryptoPrice price = new CryptoPrice();

        price.setSymbol("ETH");
        price.setPrice(new BigDecimal("3500.25"));
        price.setVolume(new BigDecimal("500000000"));
        price.setMarketCap(new BigDecimal("420000000000"));
        price.setPriceChange24h(new BigDecimal("-50.75"));
        price.setPriceChangePercent24h(new BigDecimal("-1.43"));
        price.setHigh24h(new BigDecimal("3600.00"));
        price.setLow24h(new BigDecimal("3400.00"));
        price.setSource("CoinGecko");

        Instant now = Instant.now();
        price.setTimestamp(now);

        assertEquals("ETH", price.getSymbol());
        assertEquals(new BigDecimal("3500.25"), price.getPrice());
        assertEquals(new BigDecimal("500000000"), price.getVolume());
        assertEquals(new BigDecimal("420000000000"), price.getMarketCap());
        assertEquals(new BigDecimal("-50.75"), price.getPriceChange24h());
        assertEquals(new BigDecimal("-1.43"), price.getPriceChangePercent24h());
        assertEquals(new BigDecimal("3600.00"), price.getHigh24h());
        assertEquals(new BigDecimal("3400.00"), price.getLow24h());
        assertEquals("CoinGecko", price.getSource());
        assertEquals(now, price.getTimestamp());
    }

    @Test
    void toString_containsAllFields() {
        CryptoPrice price = new CryptoPrice("SOL", new BigDecimal("150"), new BigDecimal("9999"));
        price.setSource("Binance");

        String str = price.toString();

        assertTrue(str.contains("SOL"));
        assertTrue(str.contains("150"));
        assertTrue(str.contains("9999"));
        assertTrue(str.contains("Binance"));
    }

    @Test
    void nullableFields_defaultToNull() {
        CryptoPrice price = new CryptoPrice();

        assertNull(price.getSymbol());
        assertNull(price.getPrice());
        assertNull(price.getVolume());
        assertNull(price.getMarketCap());
        assertNull(price.getPriceChange24h());
        assertNull(price.getPriceChangePercent24h());
        assertNull(price.getHigh24h());
        assertNull(price.getLow24h());
        assertNull(price.getSource());
    }
}
