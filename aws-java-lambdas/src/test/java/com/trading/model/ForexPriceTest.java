package com.trading.model;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.Instant;

import static org.junit.jupiter.api.Assertions.*;

class ForexPriceTest {

    @Test
    void defaultConstructor_setsTimestamp() {
        Instant before = Instant.now();
        ForexPrice price = new ForexPrice();
        Instant after = Instant.now();

        assertNotNull(price.getTimestamp());
        assertFalse(price.getTimestamp().isBefore(before));
        assertFalse(price.getTimestamp().isAfter(after));
    }

    @Test
    void fourArgConstructor_setsFieldsAndComputesSpread() {
        BigDecimal bid = new BigDecimal("1.0850");
        BigDecimal ask = new BigDecimal("1.0855");

        ForexPrice price = new ForexPrice("EUR", "USD", bid, ask);

        assertEquals("EUR", price.getBaseCurrency());
        assertEquals("USD", price.getQuoteCurrency());
        assertEquals("EURUSD", price.getPair());
        assertEquals(bid, price.getBid());
        assertEquals(ask, price.getAsk());
        assertEquals(new BigDecimal("0.0005"), price.getSpread());
        assertNotNull(price.getTimestamp());
    }

    @Test
    void settersAndGetters_workCorrectly() {
        ForexPrice price = new ForexPrice();

        price.setBaseCurrency("GBP");
        price.setQuoteCurrency("JPY");
        price.setPair("GBPJPY");
        price.setBid(new BigDecimal("185.500"));
        price.setAsk(new BigDecimal("185.550"));
        price.setSpread(new BigDecimal("0.050"));
        price.setHigh24h(new BigDecimal("186.000"));
        price.setLow24h(new BigDecimal("184.000"));
        price.setPriceChange24h(new BigDecimal("0.750"));
        price.setPriceChangePercent24h(new BigDecimal("0.41"));
        price.setSource("Fixer.io");

        Instant now = Instant.now();
        price.setTimestamp(now);

        assertEquals("GBP", price.getBaseCurrency());
        assertEquals("JPY", price.getQuoteCurrency());
        assertEquals("GBPJPY", price.getPair());
        assertEquals(new BigDecimal("185.500"), price.getBid());
        assertEquals(new BigDecimal("185.550"), price.getAsk());
        assertEquals(new BigDecimal("0.050"), price.getSpread());
        assertEquals(new BigDecimal("186.000"), price.getHigh24h());
        assertEquals(new BigDecimal("184.000"), price.getLow24h());
        assertEquals(new BigDecimal("0.750"), price.getPriceChange24h());
        assertEquals(new BigDecimal("0.41"), price.getPriceChangePercent24h());
        assertEquals("Fixer.io", price.getSource());
        assertEquals(now, price.getTimestamp());
    }

    @Test
    void toString_containsKeyFields() {
        ForexPrice price = new ForexPrice("USD", "CHF", new BigDecimal("0.8800"), new BigDecimal("0.8810"));
        price.setSource("ExchangeRateAPI");

        String str = price.toString();

        assertTrue(str.contains("USD"));
        assertTrue(str.contains("CHF"));
        assertTrue(str.contains("USDCHF"));
        assertTrue(str.contains("ExchangeRateAPI"));
    }

    @Test
    void nullableFields_defaultToNull() {
        ForexPrice price = new ForexPrice();

        assertNull(price.getBaseCurrency());
        assertNull(price.getQuoteCurrency());
        assertNull(price.getPair());
        assertNull(price.getBid());
        assertNull(price.getAsk());
        assertNull(price.getSpread());
        assertNull(price.getHigh24h());
        assertNull(price.getLow24h());
        assertNull(price.getPriceChange24h());
        assertNull(price.getPriceChangePercent24h());
        assertNull(price.getSource());
    }
}
