/**
 * AI Trading Dashboard JavaScript
 * Handles real-time data updates, AWS integration, and chart management
 */

class TradingDashboard {
    constructor() {
        this.config = {
            apiEndpoint: 'https://3m473571ec.execute-api.eu-north-1.amazonaws.com/prod/dashboard',
            updateInterval: 30000, // 30 seconds (matches Lambda cache)
            retryAttempts: 3
        };
        
        this.charts = {};
        this.dashboardData = null;
        this.updateTimer = null;
        this.lastUpdateTime = null;
        
        this.init();
    }
    
    async init() {
        console.log('Initializing Trading Dashboard...');
        
        // Initialize AWS SDK
        this.initializeAWS();
        
        // Create charts
        this.initializeCharts();
        
        // Load initial data
        await this.loadDashboardData();
        
        // Start auto-refresh
        this.startAutoRefresh();
        
        // Setup event listeners
        this.setupEventListeners();
        
        console.log('Dashboard initialized successfully');
    }
    
    initializeAWS() {
        // No longer using AWS SDK directly from the browser
        // Data is fetched via API Gateway -> Lambda -> DynamoDB
        console.log('Using API Gateway endpoint:', this.config.apiEndpoint);
    }
    
    initializeCharts() {
        // Asset Allocation Pie Chart
        const allocationCtx = document.getElementById('allocation-chart').getContext('2d');
        this.charts.allocation = new Chart(allocationCtx, {
            type: 'doughnut',
            data: {
                labels: ['Cash', 'Crypto', 'Forex'],
                datasets: [{
                    data: [100, 0, 0],
                    backgroundColor: [
                        '#667eea',
                        '#4facfe',
                        '#43e97b'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }
    
    async loadDashboardData() {
        try {
            this.showLoading(true);
            this.updateConnectionStatus('connecting');
            
            // Fetch all dashboard data from API Gateway -> Lambda -> DynamoDB
            const response = await fetch(this.config.apiEndpoint, {
                method: 'GET',
                headers: { 'Accept': 'application/json' }
            });
            
            if (!response.ok) {
                throw new Error(`API returned ${response.status}: ${response.statusText}`);
            }
            
            const apiData = await response.json();
            console.log('Received data from AWS API:', Object.keys(apiData));
            
            // Map API response to dashboard format
            this.dashboardData = {
                lastUpdate: apiData.lastUpdate || new Date().toISOString(),
                cryptoData: this.extractCryptoData(apiData),
                forexData: this.extractForexData(apiData),
                tradingHistory: apiData.recentTrades || [],
                portfolioSummary: apiData.portfolioSummary || {},
                tradingPerformance: apiData.tradingPerformance || {},
                aiModelPerformance: apiData.aiModelPerformance || {},
                riskMetrics: apiData.riskMetrics || {},
                alerts: apiData.alerts || [],
                marketSummary: apiData.marketSummary || {}
            };
            
            this.updateDashboard();
            this.updateConnectionStatus('connected');
            
            this.lastUpdateTime = new Date();
            this.updateLastUpdateTime();
            
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            this.updateConnectionStatus('error');
            
            // Use mock data as fallback
            this.dashboardData = this.generateMockData();
            this.updateDashboard();
        } finally {
            this.showLoading(false);
        }
    }
    
    extractCryptoData(apiData) {
        // Extract crypto data from price history
        if (apiData.priceHistory) {
            return apiData.priceHistory
                .filter(item => item.type === 'crypto')
                .map(item => ({
                    symbol: item.symbol,
                    price: parseFloat(item.price || 0),
                    volume: parseFloat(item.volume || 0),
                    marketCap: parseFloat(item.marketCap || 0),
                    priceChangePercent24h: parseFloat(item.priceChangePercent24h || item.change24h || 0),
                    timestamp: item.timestamp,
                    type: 'crypto'
                }));
        }
        // Fallback: extract from market summary
        if (apiData.marketSummary) {
            return Object.entries(apiData.marketSummary)
                .filter(([_, v]) => v.type === 'crypto')
                .map(([symbol, data]) => ({
                    symbol,
                    price: parseFloat(data.price || data.latestPrice || 0),
                    volume: parseFloat(data.volume || 0),
                    priceChangePercent24h: parseFloat(data.change24h || data.priceChangePercent24h || 0),
                    timestamp: data.timestamp || apiData.lastUpdate,
                    type: 'crypto'
                }));
        }
        return [];
    }
    
    extractForexData(apiData) {
        // Extract forex data from price history
        if (apiData.priceHistory) {
            return apiData.priceHistory
                .filter(item => item.type === 'forex')
                .map(item => ({
                    pair: item.symbol || item.pair,
                    bid: parseFloat(item.bid || item.price || 0),
                    ask: parseFloat(item.ask || item.price || 0),
                    spread: parseFloat(item.spread || 0),
                    timestamp: item.timestamp,
                    type: 'forex'
                }));
        }
        // Fallback: extract from market summary
        if (apiData.marketSummary) {
            return Object.entries(apiData.marketSummary)
                .filter(([_, v]) => v.type === 'forex')
                .map(([pair, data]) => ({
                    pair,
                    bid: parseFloat(data.bid || data.price || data.latestPrice || 0),
                    ask: parseFloat(data.ask || data.price || data.latestPrice || 0),
                    spread: parseFloat(data.spread || 0),
                    timestamp: data.timestamp || apiData.lastUpdate,
                    type: 'forex'
                }));
        }
        return [];
    }
    
    // Data is now loaded via API Gateway endpoint in loadDashboardData()
    // No need for direct S3/DynamoDB access from the browser
    
    // Crypto/Forex/Trading data is now extracted from the API response
    // See extractCryptoData() and extractForexData() methods above
    
    calculatePortfolioSummary(tradingHistory) {
        const initialBalance = 50.0;
        let currentBalance = initialBalance;
        let totalTrades = tradingHistory.length;
        let winningTrades = 0;
        let openPositions = 0;
        
        const positions = [];
        
        tradingHistory.forEach(trade => {
            const hasPnl = trade.pnl !== undefined && trade.pnl !== null && trade.pnl !== '' && trade.pnl !== 'None';
            const isSellWithPnl = trade.action === 'SELL' && hasPnl;
            const isClosed = trade.status === 'closed' || trade.status === 'CLOSED';
            
            if (isSellWithPnl || (isClosed && hasPnl)) {
                const pnl = parseFloat(trade.pnl || 0);
                currentBalance += pnl;
                if (pnl > 0) winningTrades++;
            } else if (trade.action === 'BUY' && trade.status !== 'CLOSED' && trade.status !== 'closed') {
                openPositions++;
                positions.push(trade);
            }
        });
        
        const totalPnL = currentBalance - initialBalance;
        const totalReturn = (totalPnL / initialBalance) * 100;
        const winRate = totalTrades > 0 ? (winningTrades / totalTrades) * 100 : 0;
        
        return {
            initialBalance,
            currentBalance,
            portfolioValue: currentBalance,
            totalPnL,
            totalReturn,
            openPositions,
            totalTrades,
            winRate,
            positions
        };
    }
    
    generateMockData() {
        const now = new Date();
        const portfolioValue = 50 + (Math.random() - 0.5) * 10;
        
        return {
            lastUpdate: now.toISOString(),
            portfolioSummary: {
                currentBalance: 45.50,
                portfolioValue: portfolioValue,
                totalPnL: portfolioValue - 50,
                totalReturn: ((portfolioValue - 50) / 50) * 100,
                openPositions: Math.floor(Math.random() * 5),
                totalTrades: Math.floor(Math.random() * 20) + 5,
                winRate: Math.random() * 100,
                positions: [
                    {
                        symbol: 'BTC',
                        quantity: 0.001,
                        entryPrice: 45000,
                        entryTime: new Date(now - 1000 * 60 * 60 * 2).toISOString()
                    },
                    {
                        symbol: 'EURUSD',
                        quantity: 1000,
                        entryPrice: 1.1050,
                        entryTime: new Date(now - 1000 * 60 * 60 * 1).toISOString()
                    }
                ]
            },
            tradingPerformance: {
                dailyPerformance: this.generateMockPerformanceData(),
                totalTrades: 15,
                cryptoTrades: 8,
                forexTrades: 7,
                totalVolume: 856.42,
                avgTradeSize: 57.09
            },
            priceHistory: this.generateMockPriceData(),
            marketSummary: this.generateMockMarketData(),
            aiModelPerformance: {
                accuracy: 0.73,
                latestModel: {
                    modelId: 'mock-model-001',
                    timestamp: now.toISOString(),
                    accuracy: 0.73,
                    cryptoAccuracy: 0.71,
                    forexAccuracy: 0.75
                },
                trainingHistory: this.generateMockAIHistory()
            },
            recentTrades: this.generateMockTrades(),
            riskMetrics: {
                sharpeRatio: 1.23,
                maxDrawdown: -3.45,
                volatility: 12.34,
                varDaily: -2.1
            },
            alerts: [
                {
                    type: 'info',
                    title: 'Model Updated',
                    message: 'AI model retrained successfully',
                    timestamp: now.toISOString()
                },
                {
                    type: 'warning',
                    title: 'Market Volatility',
                    message: 'Increased volatility detected in crypto markets',
                    timestamp: new Date(now - 1000 * 60 * 30).toISOString()
                }
            ]
        };
    }
    
    generateMockPerformanceData() {
        const data = [];
        const now = new Date();
        
        for (let i = 7; i >= 0; i--) {
            const date = new Date(now - i * 24 * 60 * 60 * 1000);
            data.push({
                date: date.toISOString().split('T')[0],
                trades: Math.floor(Math.random() * 5) + 1,
                volume: Math.random() * 200 + 50,
                pnl: (Math.random() - 0.5) * 10
            });
        }
        
        return data;
    }
    
    generateMockPriceData() {
        const data = [];
        const symbols = ['BTC', 'ETH', 'EURUSD', 'GBPUSD'];
        const basePrices = { BTC: 45000, ETH: 3000, EURUSD: 1.105, GBPUSD: 1.27 };
        const now = new Date();
        
        symbols.forEach(symbol => {
            const basePrice = basePrices[symbol];
            
            for (let i = 24; i >= 0; i--) {
                const timestamp = new Date(now - i * 60 * 60 * 1000);
                const price = basePrice * (1 + (Math.random() - 0.5) * 0.02);
                
                data.push({
                    symbol: symbol,
                    type: symbol.length === 3 ? 'crypto' : 'forex',
                    timestamp: timestamp.toISOString(),
                    price: price,
                    volume: Math.random() * 1000000
                });
            }
        });
        
        return data;
    }
    
    generateMockMarketData() {
        return {
            BTC: {
                price: 45234.56,
                change24h: 2.34,
                volume: 28500000000,
                type: 'crypto'
            },
            ETH: {
                price: 3045.78,
                change24h: -1.23,
                volume: 15200000000,
                type: 'crypto'
            },
            EURUSD: {
                price: 1.1052,
                change24h: 0.08,
                spread: 0.0001,
                type: 'forex'
            },
            GBPUSD: {
                price: 1.2698,
                change24h: -0.12,
                spread: 0.0002,
                type: 'forex'
            }
        };
    }
    
    generateMockAIHistory() {
        const history = [];
        const now = new Date();
        
        for (let i = 5; i >= 0; i--) {
            const timestamp = new Date(now - i * 6 * 60 * 60 * 1000);
            history.push({
                modelId: `model-${i}`,
                timestamp: timestamp.toISOString(),
                accuracy: 0.65 + Math.random() * 0.15,
                cryptoAccuracy: 0.60 + Math.random() * 0.20,
                forexAccuracy: 0.70 + Math.random() * 0.15
            });
        }
        
        return history;
    }
    
    generateMockTrades() {
        const trades = [];
        const symbols = ['BTC', 'ETH', 'EURUSD', 'GBPUSD'];
        const actions = ['BUY', 'SELL'];
        const now = new Date();
        
        for (let i = 0; i < 10; i++) {
            const symbol = symbols[Math.floor(Math.random() * symbols.length)];
            const action = actions[Math.floor(Math.random() * actions.length)];
            const timestamp = new Date(now - i * 30 * 60 * 1000);
            
            trades.push({
                tradeId: `trade-${i}`,
                symbol: symbol,
                action: action,
                quantity: Math.random() * 2,
                price: Math.random() * 50000,
                value: Math.random() * 100,
                timestamp: timestamp.toISOString(),
                pnl: action === 'SELL' ? (Math.random() - 0.5) * 20 : null,
                pnlPercent: action === 'SELL' ? (Math.random() - 0.5) * 10 : null,
                marketType: symbol.length === 3 ? 'crypto' : 'forex'
            });
        }
        
        return trades;
    }
    
    updateDashboard() {
        if (!this.dashboardData) return;
        
        console.log('Updating dashboard with new data');
        
        // Update summary cards
        this.updateSummaryCards();
        
        // Update charts
        this.updateCharts();
        
        // Update portfolio breakdown
        this.updatePortfolioBreakdown();
        
        // Update trading insights
        this.updateTradingInsights();
        
        // Update market prices
        this.updateMarketPrices();
        
        // Update market overview cards
        this.updateMarketOverview();
        
        // Update recent trades
        this.updateRecentTrades();
        
        // Update open positions
        this.updateOpenPositions();
        
        // Update system alerts
        this.updateSystemAlerts();
    }
    
    updateSummaryCards() {
        const summary = this.dashboardData.portfolioSummary || {
            portfolioValue: 50,
            totalReturn: 0,
            totalPnL: 0,
            winRate: 0,
            openPositions: 0,
            totalTrades: 0
        };
        
        // Portfolio Value
        document.getElementById('portfolio-value').textContent = '$' + summary.portfolioValue.toFixed(2);
        
        const portfolioChangeElement = document.getElementById('portfolio-change');
        portfolioChangeElement.textContent = (summary.totalReturn >= 0 ? '+' : '') + summary.totalReturn.toFixed(2) + '%';
        portfolioChangeElement.className = summary.totalReturn >= 0 ? 'text-success' : 'text-danger';
        
        // Total P&L
        const pnlElement = document.getElementById('total-pnl');
        pnlElement.textContent = (summary.totalPnL >= 0 ? '+$' : '-$') + Math.abs(summary.totalPnL).toFixed(2);
        pnlElement.parentElement.parentElement.className = `card ${summary.totalPnL >= 0 ? 'bg-success' : 'bg-danger'} text-white`;
        
        document.getElementById('win-rate').textContent = 'Win Rate: ' + summary.winRate.toFixed(1) + '%';
        
        // Active Positions
        document.getElementById('active-positions').textContent = summary.openPositions;
        document.getElementById('total-trades').textContent = 'Total Trades: ' + summary.totalTrades;
        
        // AI Accuracy - use real data from API if available
        const aiPerf = this.dashboardData.aiModelPerformance;
        if (aiPerf && aiPerf.latestModel && aiPerf.latestModel.accuracy) {
            const accuracy = (parseFloat(aiPerf.latestModel.accuracy) * 100).toFixed(1);
            document.getElementById('ai-accuracy').textContent = accuracy + '%';
        } else if (aiPerf && aiPerf.accuracy) {
            const accuracy = (parseFloat(aiPerf.accuracy) * 100).toFixed(1);
            document.getElementById('ai-accuracy').textContent = accuracy + '%';
        } else {
            document.getElementById('ai-accuracy').textContent = 'N/A';
        }
        
        // Market Summary
        if (this.dashboardData.marketSummary) {
            const cryptoCount = this.dashboardData.marketSummary.cryptoCount || 0;
            const forexCount = this.dashboardData.marketSummary.forexCount || 0;
            
            // Update any additional market summary displays
            console.log(`Market data loaded: ${cryptoCount} crypto, ${forexCount} forex pairs`);
        }
    }
    
    updateCharts() {
        // Update asset allocation from positions data
        const summary = this.dashboardData.portfolioSummary || {};
        const positions = summary.positions || [];
        const totalValue = summary.portfolioValue || 50;
        const cashValue = summary.currentBalance || totalValue;
        
        let cryptoValue = 0;
        let forexValue = 0;
        positions.forEach(p => {
            const posVal = (p.quantity || 0) * (p.entryPrice || 0);
            const sym = (p.symbol || '').toUpperCase();
            if (sym.length > 3 || sym.includes('USD') || sym.includes('EUR') || sym.includes('GBP') || sym.includes('CHF') || sym.includes('AUD')) {
                forexValue += posVal;
            } else {
                cryptoValue += posVal;
            }
        });
        
        const labels = ['Cash'];
        const data = [cashValue];
        const colors = ['#667eea'];
        if (cryptoValue > 0) { labels.push('Crypto'); data.push(cryptoValue); colors.push('#4facfe'); }
        if (forexValue > 0) { labels.push('Forex'); data.push(forexValue); colors.push('#43e97b'); }
        
        this.charts.allocation.data.labels = labels;
        this.charts.allocation.data.datasets[0].data = data;
        this.charts.allocation.data.datasets[0].backgroundColor = colors;
        this.charts.allocation.update();
    }
    
    updatePortfolioBreakdown() {
        const summary = this.dashboardData.portfolioSummary || {};
        const positions = summary.positions || [];
        const totalValue = summary.portfolioValue || 50;
        const cashValue = summary.currentBalance || totalValue;
        const investedValue = Math.max(0, totalValue - cashValue);
        
        document.getElementById('breakdown-value').textContent = '$' + totalValue.toFixed(2);
        document.getElementById('breakdown-cash').textContent = '$' + cashValue.toFixed(2);
        document.getElementById('breakdown-invested').textContent = '$' + investedValue.toFixed(2);
        
        // Color the value based on profit/loss
        const valEl = document.getElementById('breakdown-value');
        valEl.className = totalValue >= 50 ? 'text-success' : 'text-danger';
        
        // Build position bars
        const container = document.getElementById('position-bars');
        if (!container) return;
        container.innerHTML = '';
        
        if (positions.length === 0) {
            container.innerHTML = '<p class="text-muted text-center mb-0">No open positions</p>';
            return;
        }
        
        // Calculate each position's value
        const posData = positions.map(p => {
            const val = (p.quantity || 0) * (p.entryPrice || 0);
            return { symbol: p.symbol, value: val, quantity: p.quantity, price: p.entryPrice };
        }).sort((a, b) => b.value - a.value);
        
        const maxVal = Math.max(...posData.map(p => p.value), 1);
        const barColors = ['#667eea','#4facfe','#43e97b','#fa709a','#ffc107','#17a2b8','#6f42c1','#fd7e14','#20c997'];
        
        posData.forEach((pos, i) => {
            const pct = (pos.value / maxVal) * 100;
            const color = barColors[i % barColors.length];
            const bar = document.createElement('div');
            bar.className = 'mb-2';
            bar.innerHTML = `
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <span class="fw-bold" style="font-size:0.85rem;">${pos.symbol}</span>
                    <span class="text-muted" style="font-size:0.8rem;">$${pos.value.toFixed(2)} <small>(${pos.quantity.toFixed(4)} @ $${pos.price.toFixed(pos.price < 10 ? 4 : 2)})</small></span>
                </div>
                <div class="progress" style="height: 6px;">
                    <div class="progress-bar" style="width:${pct}%; background:${color};" role="progressbar"></div>
                </div>
            `;
            container.appendChild(bar);
        });
    }
    
    updateTradingInsights() {
        const perf = this.dashboardData.tradingPerformance || {};
        const ai = this.dashboardData.aiModelPerformance || {};
        const risk = this.dashboardData.riskMetrics || {};
        const summary = this.dashboardData.portfolioSummary || {};
        
        // AI accuracy
        let accuracy = 0;
        let cryptoAcc = 0;
        let forexAcc = 0;
        if (ai.latestModel) {
            accuracy = parseFloat(ai.latestModel.accuracy || 0);
            cryptoAcc = parseFloat(ai.latestModel.cryptoAccuracy || 0);
            forexAcc = parseFloat(ai.latestModel.forexAccuracy || 0);
        } else if (ai.accuracy) {
            accuracy = parseFloat(ai.accuracy);
        }
        const accPct = (accuracy * 100).toFixed(1);
        const el = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val; };
        const elH = (id, html) => { const e = document.getElementById(id); if (e) e.innerHTML = html; };
        
        // Model info
        el('insight-accuracy', accuracy > 0 ? accPct + '%' : 'Training...');
        const accBar = document.getElementById('accuracy-bar');
        if (accBar) accBar.style.width = accPct + '%';
        el('insight-crypto-accuracy', cryptoAcc > 0 ? (cryptoAcc * 100).toFixed(1) + '%' : '--');
        el('insight-forex-accuracy', forexAcc > 0 ? (forexAcc * 100).toFixed(1) + '%' : '--');
        el('insight-total-models', ai.totalModels || 0);
        
        // Model age
        const modelAge = ai.modelAgeHours;
        if (modelAge !== undefined && modelAge !== null) {
            el('insight-model-age', modelAge < 1 ? '<1h ago' : modelAge.toFixed(0) + 'h ago');
        } else {
            el('insight-model-age', '--');
        }
        
        // Accuracy trend
        const trend = ai.accuracyTrend || '--';
        const trendEl = document.getElementById('insight-trend');
        if (trendEl) {
            const trendIcon = trend === 'improving' ? '📈' : trend === 'declining' ? '📉' : '➡️';
            const trendClass = trend === 'improving' ? 'text-success' : trend === 'declining' ? 'text-danger' : 'text-muted';
            trendEl.innerHTML = `<span class="${trendClass}">${trendIcon} ${trend.charAt(0).toUpperCase() + trend.slice(1)}</span>`;
        }
        
        // Trade stats
        el('insight-crypto-trades', perf.cryptoTrades || 0);
        el('insight-forex-trades', perf.forexTrades || 0);
        el('insight-avg-trade', '$' + (perf.avgTradeSize || 0).toFixed(2));
        el('insight-volume', '$' + (perf.totalVolume || 0).toFixed(2));
        el('insight-win-rate', (summary.winRate || 0).toFixed(1) + '%');
        
        // Profit factor & expectancy
        const pf = perf.profitFactor;
        el('insight-profit-factor', pf === 'N/A' ? 'N/A' : (typeof pf === 'number' ? pf.toFixed(2) : '--'));
        const exp = perf.expectancy || 0;
        const expEl = document.getElementById('insight-expectancy');
        if (expEl) {
            expEl.textContent = (exp >= 0 ? '+$' : '-$') + Math.abs(exp).toFixed(4);
            expEl.className = exp >= 0 ? 'text-success' : 'text-danger';
        }
        
        // Sharpe ratio
        el('insight-sharpe', (risk.sharpeRatio || 0).toFixed(2));
        
        // Risk metrics
        const drawdown = risk.maxDrawdown || 0;
        el('insight-drawdown', drawdown.toFixed(2) + '%');
        const varDaily = risk.varDaily || 0;
        el('insight-var', '$' + Math.abs(varDaily).toFixed(2));
        
        // Avg win/loss
        const avgWin = perf.avgWin || 0;
        const avgLoss = perf.avgLoss || 0;
        elH('insight-avg-wl', `<span class="text-success">$${avgWin.toFixed(4)}</span> / <span class="text-danger">$${avgLoss.toFixed(4)}</span>`);
        
        // Largest win/loss
        const lWin = perf.largestWin || 0;
        const lLoss = perf.largestLoss || 0;
        elH('insight-largest-wl', `<span class="text-success">$${lWin.toFixed(4)}</span> / <span class="text-danger">$${Math.abs(lLoss).toFixed(4)}</span>`);
        
        // Streaks
        elH('insight-streak', `<span class="text-success">${perf.bestStreak || 0}</span> / <span class="text-danger">${perf.worstStreak || 0}</span>`);
        
        // Cash utilization
        const totalVal = summary.portfolioValue || 50;
        const cash = summary.currentBalance || totalVal;
        const utilization = ((1 - cash / totalVal) * 100).toFixed(1);
        el('insight-utilization', utilization + '%');
        
        // Unrealized PnL
        const unrealizedPnl = summary.unrealizedPnL || 0;
        const upEl = document.getElementById('insight-unrealized-pnl');
        if (upEl) {
            upEl.textContent = (unrealizedPnl >= 0 ? '+$' : '-$') + Math.abs(unrealizedPnl).toFixed(2);
            upEl.className = unrealizedPnl >= 0 ? 'text-success' : 'text-danger';
        }
    }
    
    updateMarketPrices() {
        const container = document.getElementById('market-prices');
        container.innerHTML = '';
        
        // Combine crypto and forex data
        const allMarketData = [];
        
        // Add crypto data
        if (this.dashboardData.cryptoData) {
            const cryptoBySymbol = {};
            this.dashboardData.cryptoData.forEach(item => {
                if (!cryptoBySymbol[item.symbol] || new Date(item.timestamp) > new Date(cryptoBySymbol[item.symbol].timestamp)) {
                    cryptoBySymbol[item.symbol] = item;
                }
            });
            
            Object.values(cryptoBySymbol).forEach(crypto => {
                allMarketData.push({
                    symbol: crypto.symbol,
                    price: crypto.price,
                    change24h: crypto.priceChangePercent24h || 0,
                    volume: crypto.volume,
                    marketCap: crypto.marketCap,
                    type: 'crypto',
                    timestamp: crypto.timestamp
                });
            });
        }
        
        // Add forex data
        if (this.dashboardData.forexData) {
            const forexByPair = {};
            this.dashboardData.forexData.forEach(item => {
                if (!forexByPair[item.pair] || new Date(item.timestamp) > new Date(forexByPair[item.pair].timestamp)) {
                    forexByPair[item.pair] = item;
                }
            });
            
            Object.values(forexByPair).forEach(forex => {
                allMarketData.push({
                    symbol: forex.pair,
                    price: (forex.bid + forex.ask) / 2,
                    spread: forex.spread,
                    bid: forex.bid,
                    ask: forex.ask,
                    type: 'forex',
                    timestamp: forex.timestamp
                });
            });
        }
        
        // Sort by symbol
        allMarketData.sort((a, b) => a.symbol.localeCompare(b.symbol));
        
        // Display market data
        allMarketData.slice(0, 20).forEach(data => {
            const item = document.createElement('div');
            item.className = 'market-price-item d-flex justify-content-between align-items-center p-2 border-bottom';
            
            let extraInfo = '';
            if (data.type === 'crypto') {
                const changeClass = data.change24h >= 0 ? 'text-success' : 'text-danger';
                const changeSymbol = data.change24h >= 0 ? '+' : '';
                extraInfo = `<small class="${changeClass}">${changeSymbol}${data.change24h.toFixed(2)}%</small>`;
            } else {
                extraInfo = `<small class="text-muted">Spread: ${data.spread ? data.spread.toFixed(4) : 'N/A'}</small>`;
            }
            
            const priceFormatted = data.type === 'forex' ? data.price.toFixed(4) : data.price.toFixed(2);
            const timeFormatted = new Date(data.timestamp).toLocaleTimeString();
            
            item.innerHTML = `
                <div>
                    <div class="fw-bold">${data.symbol}</div>
                    <div class="text-muted small">${data.type.toUpperCase()}</div>
                </div>
                <div class="text-end">
                    <div class="fw-bold">$${priceFormatted}</div>
                    ${extraInfo}
                    <div class="text-muted small">${timeFormatted}</div>
                </div>
            `;
            
            container.appendChild(item);
        });
        
        if (allMarketData.length === 0) {
            container.innerHTML = '<div class="text-center text-muted p-3">No market data available</div>';
        }
    }
    
    updateMarketOverview() {
        // Update crypto count
        const cryptoCount = this.dashboardData.cryptoData ? this.dashboardData.cryptoData.length : 0;
        const forexCount = this.dashboardData.forexData ? this.dashboardData.forexData.length : 0;
        
        document.getElementById('crypto-count').textContent = cryptoCount;
        document.getElementById('forex-count').textContent = forexCount;
        document.getElementById('total-data-points').textContent = cryptoCount + forexCount;
        
        // Find top gainer and loser from crypto data
        let topGainer = null;
        let topLoser = null;
        
        if (this.dashboardData.cryptoData && this.dashboardData.cryptoData.length > 0) {
            this.dashboardData.cryptoData.forEach(crypto => {
                const change = crypto.priceChangePercent24h || 0;
                
                if (!topGainer || change > topGainer.change) {
                    topGainer = { symbol: crypto.symbol, change: change };
                }
                
                if (!topLoser || change < topLoser.change) {
                    topLoser = { symbol: crypto.symbol, change: change };
                }
            });
        }
        
        // Update top gainer/loser
        if (topGainer) {
            document.getElementById('top-gainer').textContent = topGainer.symbol;
            const gainerElement = document.getElementById('top-gainer-change');
            gainerElement.textContent = `+${topGainer.change.toFixed(2)}%`;
            gainerElement.className = 'text-success';
        }
        
        if (topLoser) {
            document.getElementById('top-loser').textContent = topLoser.symbol;
            const loserElement = document.getElementById('top-loser-change');
            loserElement.textContent = `${topLoser.change.toFixed(2)}%`;
            loserElement.className = 'text-danger';
        }
        
        // Update data age
        const latestTimestamp = this.getLatestDataTimestamp();
        if (latestTimestamp) {
            const age = Math.floor((new Date() - new Date(latestTimestamp)) / 1000 / 60);
            document.getElementById('data-age').textContent = age < 1 ? 'Just now' : `${age} min ago`;
        }
    }
    
    getLatestDataTimestamp() {
        let latest = null;
        
        // Check crypto data
        if (this.dashboardData.cryptoData && this.dashboardData.cryptoData.length > 0) {
            const cryptoLatest = this.dashboardData.cryptoData[0].timestamp;
            if (!latest || new Date(cryptoLatest) > new Date(latest)) {
                latest = cryptoLatest;
            }
        }
        
        // Check forex data
        if (this.dashboardData.forexData && this.dashboardData.forexData.length > 0) {
            const forexLatest = this.dashboardData.forexData[0].timestamp;
            if (!latest || new Date(forexLatest) > new Date(latest)) {
                latest = forexLatest;
            }
        }
        
        return latest;
    }
    
    updateRecentTrades() {
        const container = document.getElementById('recent-trades');
        container.innerHTML = '';
        
        const tradingHistory = this.dashboardData.tradingHistory || [];
        
        if (tradingHistory.length === 0) {
            container.innerHTML = '<div class="text-center text-muted p-3">No recent trades</div>';
            return;
        }
        
        tradingHistory.slice(0, 10).forEach(trade => {
            const item = document.createElement('div');
            item.className = 'trade-item d-flex justify-content-between align-items-center p-2 border-bottom';
            
            const actionClass = trade.action ? trade.action.toLowerCase() : 'unknown';
            const pnl = parseFloat(trade.pnl || 0);
            let pnlDisplay = '';
            
            // Show P&L for SELL trades that have pnl data, or when status indicates closed/executed
            const hasPnl = trade.pnl !== undefined && trade.pnl !== null && trade.pnl !== '' && trade.pnl !== 'None';
            const isSellWithPnl = trade.action === 'SELL' && hasPnl;
            const isClosed = trade.status === 'closed' || trade.status === 'CLOSED';
            
            if (isSellWithPnl || (isClosed && hasPnl)) {
                pnlDisplay = `<div class="${pnl >= 0 ? 'text-success' : 'text-danger'}">
                    ${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}
                </div>`;
            } else if (trade.action === 'BUY') {
                const value = parseFloat(trade.value || 0);
                pnlDisplay = `<div class="text-info">$${value.toFixed(2)}</div>`;
            } else {
                pnlDisplay = `<div class="text-muted">${trade.status || 'Active'}</div>`;
            }
            
            const timeFormatted = trade.timestamp ? new Date(trade.timestamp).toLocaleTimeString() : 'Unknown';
            
            item.innerHTML = `
                <div>
                    <div class="fw-bold">${trade.symbol || 'Unknown'}</div>
                    <div class="text-muted small">${timeFormatted}</div>
                </div>
                <div class="text-end">
                    <div class="badge bg-primary">${trade.action || 'Unknown'}</div>
                    ${pnlDisplay}
                </div>
            `;
            
            container.appendChild(item);
        });
    }
    
    updateOpenPositions() {
        const positions = this.dashboardData.portfolioSummary?.positions || [];
        const tableBody = document.getElementById('positions-table');
        tableBody.innerHTML = '';
        
        if (positions.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="9" class="text-center text-muted py-4">No open positions</td>';
            tableBody.appendChild(row);
            return;
        }
        
        positions.forEach(position => {
            const row = document.createElement('tr');
            
            // Use live currentPrice from backend (which fetches latest market data)
            const currentPrice = parseFloat(position.currentPrice || position.entryPrice || 0);
            const entryPrice = parseFloat(position.entryPrice || 0);
            const quantity = parseFloat(position.quantity || 0);
            
            // Use pre-calculated PnL from backend if available, else compute
            const pnl = position.pnl !== undefined ? parseFloat(position.pnl) : (currentPrice - entryPrice) * quantity;
            const pnlPct = position.pnlPercent !== undefined ? parseFloat(position.pnlPercent) : (entryPrice > 0 ? ((currentPrice - entryPrice) / entryPrice) * 100 : 0);
            
            const pnlClass = pnl >= 0 ? 'text-success' : 'text-danger';
            const pnlSymbol = pnl >= 0 ? '+' : '';
            
            const entryTime = position.entryTime ? new Date(position.entryTime).toLocaleString() : 'Unknown';
            const posType = position.type || 'Unknown';
            const typeBadge = posType === 'crypto' ? 'bg-warning' : posType === 'forex' ? 'bg-info' : 'bg-secondary';
            
            // Format prices based on type
            const priceDecimals = posType === 'forex' ? 6 : (entryPrice < 10 ? 4 : 2);
            
            row.innerHTML = `
                <td class="fw-bold">${position.symbol || 'Unknown'}</td>
                <td><span class="badge ${typeBadge}">${posType.toUpperCase()}</span></td>
                <td>${quantity.toFixed(4)}</td>
                <td>$${entryPrice.toFixed(priceDecimals)}</td>
                <td>$${currentPrice.toFixed(priceDecimals)}</td>
                <td class="${pnlClass} fw-bold">${pnlSymbol}$${Math.abs(pnl).toFixed(4)}</td>
                <td class="${pnlClass} fw-bold">${pnlSymbol}${pnlPct.toFixed(2)}%</td>
                <td class="text-muted small">${entryTime}</td>
                <td>
                    <button class="btn btn-sm btn-outline-danger" onclick="dashboard.closePosition('${position.symbol}')">
                        <i class="fas fa-times"></i> Close
                    </button>
                </td>
            `;
            
            tableBody.appendChild(row);
        });
    }
    
    updateSystemAlerts() {
        const container = document.getElementById('system-alerts');
        container.innerHTML = '';
        
        // Use alerts from API if available, otherwise generate locally
        const alerts = [];
        
        // Add alerts from API response
        if (this.dashboardData.alerts && this.dashboardData.alerts.length > 0) {
            this.dashboardData.alerts.forEach(alert => {
                alerts.push({
                    type: alert.type || 'info',
                    title: alert.title || 'Alert',
                    message: alert.message || '',
                    timestamp: alert.timestamp || new Date().toISOString()
                });
            });
        }
        
        // Add live data status alerts
        if (this.dashboardData.cryptoData && this.dashboardData.cryptoData.length > 0) {
            alerts.push({
                type: 'success',
                title: 'Crypto Data Live',
                message: `${this.dashboardData.cryptoData.length} crypto data points loaded`,
                timestamp: new Date().toISOString()
            });
        }
        
        if (this.dashboardData.forexData && this.dashboardData.forexData.length > 0) {
            alerts.push({
                type: 'success',
                title: 'Forex Data Live', 
                message: `${this.dashboardData.forexData.length} forex data points loaded`,
                timestamp: new Date().toISOString()
            });
        }
        
        // Connection status alert
        alerts.push({
            type: 'success',
            title: 'AWS Connected',
            message: `Data fetched from API at ${new Date().toLocaleTimeString()}`,
            timestamp: new Date().toISOString()
        });
        
        // Add portfolio status
        const portfolio = this.dashboardData.portfolioSummary;
        if (portfolio && portfolio.totalReturn > 5) {
            alerts.push({
                type: 'success',
                title: 'Portfolio Performance',
                message: `Portfolio up ${portfolio.totalReturn.toFixed(1)}% today`,
                timestamp: new Date().toISOString()
            });
        } else if (portfolio && portfolio.totalReturn < -5) {
            alerts.push({
                type: 'warning',
                title: 'Portfolio Alert',
                message: `Portfolio down ${Math.abs(portfolio.totalReturn).toFixed(1)}% today`,
                timestamp: new Date().toISOString()
            });
        }
        
        if (alerts.length === 0) {
            container.innerHTML = '<div class="text-center text-muted p-3">No alerts</div>';
            return;
        }
        
        alerts.slice(0, 5).forEach(alert => {
            const item = document.createElement('div');
            item.className = `alert alert-${alert.type === 'success' ? 'success' : alert.type === 'warning' ? 'warning' : 'info'} alert-dismissible fade show mb-2`;
            
            item.innerHTML = `
                <div class="d-flex align-items-start">
                    <div class="me-2">
                        <i class="fas fa-${alert.type === 'success' ? 'check-circle' : alert.type === 'warning' ? 'exclamation-triangle' : 'info-circle'}"></i>
                    </div>
                    <div class="flex-grow-1">
                        <div class="fw-bold">${alert.title}</div>
                        <div>${alert.message}</div>
                        <small class="text-muted">${new Date(alert.timestamp).toLocaleTimeString()}</small>
                    </div>
                </div>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            
            container.appendChild(item);
        });
    }
    
    updateConnectionStatus(status) {
        const statusElement = document.getElementById('connection-status');
        const statusMap = {
            'connected': { text: 'Connected', class: 'text-success' },
            'connecting': { text: 'Connecting...', class: 'text-warning' },
            'warning': { text: 'Limited Data', class: 'text-warning' },
            'error': { text: 'Connection Error', class: 'text-danger' }
        };
        
        const statusInfo = statusMap[status] || statusMap['error'];
        statusElement.textContent = statusInfo.text;
        statusElement.className = `navbar-text ${statusInfo.class}`;
    }
    
    updateLastUpdateTime() {
        const element = document.getElementById('last-update');
        if (this.lastUpdateTime) {
            element.textContent = this.lastUpdateTime.toLocaleTimeString();
        }
    }
    
    showLoading(show) {
        const overlay = document.getElementById('loading-overlay');
        if (show) {
            overlay.classList.remove('d-none');
        } else {
            overlay.classList.add('d-none');
        }
    }
    
    startAutoRefresh() {
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
        }
        
        this.updateTimer = setInterval(() => {
            this.loadDashboardData();
        }, this.config.updateInterval);
    }
    
    setupEventListeners() {
        // Refresh button (if you add one)
        document.addEventListener('keydown', (e) => {
            if (e.key === 'F5' || (e.ctrlKey && e.key === 'r')) {
                e.preventDefault();
                this.loadDashboardData();
            }
        });
        
        // Handle window focus/blur for performance
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                // Page is not visible, reduce update frequency
                if (this.updateTimer) {
                    clearInterval(this.updateTimer);
                }
            } else {
                // Page is visible again, resume normal updates
                this.startAutoRefresh();
                this.loadDashboardData();
            }
        });
    }
    
    // Method to close position (called from UI)
    closePosition(symbol) {
        if (confirm(`Are you sure you want to close the ${symbol} position?`)) {
            // In a real implementation, this would call your AWS API
            console.log(`Closing position for ${symbol}`);
            
            // For demo purposes, just reload data
            setTimeout(() => {
                this.loadDashboardData();
            }, 1000);
        }
    }
}

// Initialize dashboard when page loads
let dashboard;

document.addEventListener('DOMContentLoaded', () => {
    dashboard = new TradingDashboard();
});

// Export for global access
window.dashboard = dashboard;