package com.trading.model;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.math.BigDecimal;
import java.time.Instant;

public class CryptoPrice {
    
    @JsonProperty("symbol")
    private String symbol;
    
    @JsonProperty("price")
    private BigDecimal price;
    
    @JsonProperty("volume")
    private BigDecimal volume;
    
    @JsonProperty("marketCap")
    private BigDecimal marketCap;
    
    @JsonProperty("priceChange24h")
    private BigDecimal priceChange24h;
    
    @JsonProperty("priceChangePercent24h")
    private BigDecimal priceChangePercent24h;
    
    @JsonProperty("high24h")
    private BigDecimal high24h;
    
    @JsonProperty("low24h")
    private BigDecimal low24h;
    
    @JsonProperty("timestamp")
    private Instant timestamp;
    
    @JsonProperty("source")
    private String source;
    
    public CryptoPrice() {
        this.timestamp = Instant.now();
    }
    
    public CryptoPrice(String symbol, BigDecimal price, BigDecimal volume) {
        this.symbol = symbol;
        this.price = price;
        this.volume = volume;
        this.timestamp = Instant.now();
    }

    // Getters and Setters
    public String getSymbol() {
        return symbol;
    }

    public void setSymbol(String symbol) {
        this.symbol = symbol;
    }

    public BigDecimal getPrice() {
        return price;
    }

    public void setPrice(BigDecimal price) {
        this.price = price;
    }

    public BigDecimal getVolume() {
        return volume;
    }

    public void setVolume(BigDecimal volume) {
        this.volume = volume;
    }

    public BigDecimal getMarketCap() {
        return marketCap;
    }

    public void setMarketCap(BigDecimal marketCap) {
        this.marketCap = marketCap;
    }

    public BigDecimal getPriceChange24h() {
        return priceChange24h;
    }

    public void setPriceChange24h(BigDecimal priceChange24h) {
        this.priceChange24h = priceChange24h;
    }

    public BigDecimal getPriceChangePercent24h() {
        return priceChangePercent24h;
    }

    public void setPriceChangePercent24h(BigDecimal priceChangePercent24h) {
        this.priceChangePercent24h = priceChangePercent24h;
    }

    public BigDecimal getHigh24h() {
        return high24h;
    }

    public void setHigh24h(BigDecimal high24h) {
        this.high24h = high24h;
    }

    public BigDecimal getLow24h() {
        return low24h;
    }

    public void setLow24h(BigDecimal low24h) {
        this.low24h = low24h;
    }

    public Instant getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(Instant timestamp) {
        this.timestamp = timestamp;
    }

    public String getSource() {
        return source;
    }

    public void setSource(String source) {
        this.source = source;
    }

    @Override
    public String toString() {
        return "CryptoPrice{" +
                "symbol='" + symbol + '\'' +
                ", price=" + price +
                ", volume=" + volume +
                ", marketCap=" + marketCap +
                ", priceChange24h=" + priceChange24h +
                ", priceChangePercent24h=" + priceChangePercent24h +
                ", high24h=" + high24h +
                ", low24h=" + low24h +
                ", timestamp=" + timestamp +
                ", source='" + source + '\'' +
                '}';
    }
}