package com.trading.model;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.math.BigDecimal;
import java.time.Instant;

public class ForexPrice {
    
    @JsonProperty("baseCurrency")
    private String baseCurrency;
    
    @JsonProperty("quoteCurrency")
    private String quoteCurrency;
    
    @JsonProperty("pair")
    private String pair; // e.g., "EURUSD"
    
    @JsonProperty("bid")
    private BigDecimal bid;
    
    @JsonProperty("ask")
    private BigDecimal ask;
    
    @JsonProperty("spread")
    private BigDecimal spread;
    
    @JsonProperty("high24h")
    private BigDecimal high24h;
    
    @JsonProperty("low24h")
    private BigDecimal low24h;
    
    @JsonProperty("priceChange24h")
    private BigDecimal priceChange24h;
    
    @JsonProperty("priceChangePercent24h")
    private BigDecimal priceChangePercent24h;
    
    @JsonProperty("timestamp")
    private Instant timestamp;
    
    @JsonProperty("source")
    private String source;
    
    public ForexPrice() {
        this.timestamp = Instant.now();
    }
    
    public ForexPrice(String baseCurrency, String quoteCurrency, BigDecimal bid, BigDecimal ask) {
        this.baseCurrency = baseCurrency;
        this.quoteCurrency = quoteCurrency;
        this.pair = baseCurrency + quoteCurrency;
        this.bid = bid;
        this.ask = ask;
        this.spread = ask.subtract(bid);
        this.timestamp = Instant.now();
    }

    // Getters and Setters
    public String getBaseCurrency() {
        return baseCurrency;
    }

    public void setBaseCurrency(String baseCurrency) {
        this.baseCurrency = baseCurrency;
    }

    public String getQuoteCurrency() {
        return quoteCurrency;
    }

    public void setQuoteCurrency(String quoteCurrency) {
        this.quoteCurrency = quoteCurrency;
    }

    public String getPair() {
        return pair;
    }

    public void setPair(String pair) {
        this.pair = pair;
    }

    public BigDecimal getBid() {
        return bid;
    }

    public void setBid(BigDecimal bid) {
        this.bid = bid;
    }

    public BigDecimal getAsk() {
        return ask;
    }

    public void setAsk(BigDecimal ask) {
        this.ask = ask;
    }

    public BigDecimal getSpread() {
        return spread;
    }

    public void setSpread(BigDecimal spread) {
        this.spread = spread;
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
        return "ForexPrice{" +
                "baseCurrency='" + baseCurrency + '\'' +
                ", quoteCurrency='" + quoteCurrency + '\'' +
                ", pair='" + pair + '\'' +
                ", bid=" + bid +
                ", ask=" + ask +
                ", spread=" + spread +
                ", high24h=" + high24h +
                ", low24h=" + low24h +
                ", priceChange24h=" + priceChange24h +
                ", priceChangePercent24h=" + priceChangePercent24h +
                ", timestamp=" + timestamp +
                ", source='" + source + '\'' +
                '}';
    }
}