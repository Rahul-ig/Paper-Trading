"""
Dashboard Updater Lambda Function
Updates dashboard data and prepares analytics for visualization
Handles real-time data aggregation and performance metrics
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List

import boto3
from decimal import Decimal

# AWS Clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

# Configuration
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
S3_BUCKET = os.environ.get('S3_BUCKET_MODELS', 'forex-ai-models')
CRYPTO_TABLE = os.environ.get('DYNAMODB_CRYPTO_TABLE', 'CryptoPriceData')
FOREX_TABLE = os.environ.get('DYNAMODB_FOREX_TABLE', 'ForexPriceData')
TRADING_TABLE = os.environ.get('DYNAMODB_TRADING_TABLE', 'TradingHistory')
AI_MODELS_TABLE = os.environ.get('DYNAMODB_AI_MODELS_TABLE', 'AIModelMetadata')

# Setup logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger(__name__)

class DashboardUpdater:
    """Dashboard data updater and analytics processor"""
    
    def __init__(self):
        self.crypto_table = dynamodb.Table(CRYPTO_TABLE)
        self.forex_table = dynamodb.Table(FOREX_TABLE)
        self.trading_table = dynamodb.Table(TRADING_TABLE)
        self.ai_models_table = dynamodb.Table(AI_MODELS_TABLE)
    
    def lambda_handler(self, event: Dict[str, Any], context) -> Dict[str, Any]:
        """Main Lambda handler for dashboard updates"""
        is_http_request = False
        try:
            logger.info(f"Dashboard Updater started with event: {event}")
            
            # Check if this is a Function URL / API Gateway request
            is_http_request = 'requestContext' in event and 'http' in event.get('requestContext', {})
            
            if is_http_request:
                # Function URL invocation - return full dashboard data as HTTP response
                return self._handle_http_request(event)
            
            request_type = event.get('requestType', 'update')
            
            if request_type == 'getData':
                # Direct invocation requesting full data
                dashboard_data = self.generate_dashboard_data()
                return {
                    'statusCode': 200,
                    'body': json.dumps(dashboard_data, default=str)
                }
            elif request_type == 'update':
                dashboard_data = self.generate_dashboard_data()
                
                # Save dashboard data to S3 for frontend access
                try:
                    self.save_dashboard_data_to_s3(dashboard_data)
                except Exception as s3_err:
                    logger.warning(f"Could not save to S3 (continuing): {s3_err}")
                
                return {
                    'statusCode': 200,
                    'status': 'success',
                    'dashboardUpdated': True,
                    'dataPoints': len(dashboard_data.get('priceHistory', [])),
                    'lastUpdate': datetime.utcnow().isoformat(),
                    'message': 'Dashboard data updated successfully'
                }
            else:
                return {
                    'statusCode': 400,
                    'status': 'error',
                    'message': f'Unknown request type: {request_type}'
                }
                
        except Exception as e:
            logger.error(f"Error in dashboard updater: {str(e)}")
            if is_http_request:
                return {
                    'statusCode': 500,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'GET, OPTIONS',
                        'Access-Control-Allow-Headers': '*'
                    },
                    'body': json.dumps({'error': str(e)})
                }
            return {
                'statusCode': 500,
                'status': 'error',
                'message': f'Dashboard update failed: {str(e)}'
            }
    
    def _handle_http_request(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle HTTP requests from Lambda Function URL"""
        http_method = event.get('requestContext', {}).get('http', {}).get('method', 'GET')
        
        # Handle CORS preflight
        if http_method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, OPTIONS',
                    'Access-Control-Allow-Headers': '*'
                },
                'body': ''
            }
        
        # Generate dashboard data
        dashboard_data = self.generate_dashboard_data()
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': '*',
                'Cache-Control': 'max-age=60'
            },
            'body': json.dumps(dashboard_data, default=str)
        }
    
    def generate_dashboard_data(self) -> Dict[str, Any]:
        """Generate comprehensive dashboard data"""
        logger.info("Generating dashboard data")
        
        dashboard_data = {
            'lastUpdate': datetime.utcnow().isoformat(),
            'portfolioSummary': self.get_portfolio_summary(),
            'tradingPerformance': self.get_trading_performance(),
            'priceHistory': self.get_price_history(),
            'marketSummary': self.get_market_summary(),
            'aiModelPerformance': self.get_ai_model_performance(),
            'recentTrades': self.get_recent_trades(),
            'riskMetrics': self.calculate_risk_metrics(),
            'alerts': self.generate_alerts()
        }
        
        logger.info(f"Dashboard data generated with {len(dashboard_data)} sections")
        return dashboard_data
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get current portfolio summary"""
        try:
            # Get recent trading history to calculate portfolio
            current_time = datetime.utcnow()
            start_time = current_time - timedelta(days=30)
            
            response = self.trading_table.scan(
                FilterExpression='#ts BETWEEN :start_time AND :end_time',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={
                    ':start_time': start_time.isoformat(),
                    ':end_time': current_time.isoformat()
                }
            )
            
            trades = response.get('Items', [])
            
            # Calculate current portfolio state
            wallet_balance = 50.0  # Initial balance
            open_positions = {}
            total_pnl = 0.0
            total_trades = len(trades)
            winning_trades = 0
            
            for trade in sorted(trades, key=lambda x: x['timestamp']):
                symbol = trade['symbol']
                action = trade['action']
                quantity = float(trade['quantity'])
                price = float(trade['price'])
                
                if action == 'BUY':
                    open_positions[symbol] = {
                        'quantity': quantity,
                        'entry_price': price,
                        'entry_time': trade['timestamp']
                    }
                    wallet_balance -= price * quantity
                    
                elif action == 'SELL' and symbol in open_positions:
                    # Calculate P&L for completed trade
                    entry_price = open_positions[symbol]['entry_price']
                    trade_pnl = (price - entry_price) * quantity
                    total_pnl += trade_pnl
                    
                    if trade_pnl > 0:
                        winning_trades += 1
                    
                    del open_positions[symbol]
                    wallet_balance += price * quantity
            
            # Fetch current market prices for live PnL calculation
            current_prices = self._get_current_prices()
            
            # Calculate portfolio value with LIVE prices
            portfolio_value = wallet_balance
            unrealized_pnl = 0.0
            positions_with_pnl = []
            
            for symbol, position in open_positions.items():
                entry_price = position['entry_price']
                quantity = position['quantity']
                current_price = current_prices.get(symbol, entry_price)
                
                position_value = quantity * current_price
                portfolio_value += position_value
                
                pos_pnl = (current_price - entry_price) * quantity
                pos_pnl_pct = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
                unrealized_pnl += pos_pnl
                
                # Determine market type from symbol
                is_forex = len(symbol) > 3 or any(c in symbol for c in ['USD', 'EUR', 'GBP', 'CHF', 'AUD', 'JPY', 'CAD', 'NZD'])
                
                positions_with_pnl.append({
                    'symbol': symbol,
                    'quantity': quantity,
                    'entryPrice': entry_price,
                    'currentPrice': current_price,
                    'entryTime': position['entry_time'],
                    'pnl': round(pos_pnl, 4),
                    'pnlPercent': round(pos_pnl_pct, 2),
                    'positionValue': round(position_value, 4),
                    'costBasis': round(entry_price * quantity, 4),
                    'type': 'forex' if is_forex else 'crypto'
                })
            
            # Calculate performance metrics
            closed_trades = total_trades - len(open_positions)
            win_rate = (winning_trades / max(closed_trades, 1)) * 100
            total_return = ((portfolio_value - 50.0) / 50.0) * 100
            
            return {
                'currentBalance': round(wallet_balance, 2),
                'portfolioValue': round(portfolio_value, 2),
                'totalPnL': round(total_pnl + unrealized_pnl, 2),
                'realizedPnL': round(total_pnl, 2),
                'unrealizedPnL': round(unrealized_pnl, 2),
                'totalReturn': round(total_return, 2),
                'openPositions': len(open_positions),
                'totalTrades': total_trades,
                'closedTrades': closed_trades,
                'winningTrades': winning_trades,
                'losingTrades': closed_trades - winning_trades,
                'winRate': round(win_rate, 1),
                'positions': positions_with_pnl
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio summary: {str(e)}")
            return {
                'currentBalance': 50.0,
                'portfolioValue': 50.0,
                'totalPnL': 0.0,
                'totalReturn': 0.0,
                'openPositions': 0,
                'totalTrades': 0,
                'winRate': 0.0,
                'positions': []
            }
    
    def _get_current_prices(self) -> Dict[str, float]:
        """Fetch current market prices for all tracked symbols"""
        prices = {}
        try:
            # Crypto prices
            for symbol in ['BTC', 'ETH', 'ADA', 'SOL', 'LINK', 'AVAX']:
                response = self.crypto_table.query(
                    KeyConditionExpression='symbol = :symbol',
                    ExpressionAttributeValues={':symbol': symbol},
                    ScanIndexForward=False,
                    Limit=1
                )
                if response.get('Items'):
                    prices[symbol] = float(response['Items'][0].get('price', 0))
            
            # Forex prices
            for pair in ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD']:
                response = self.forex_table.query(
                    KeyConditionExpression='pair = :pair',
                    ExpressionAttributeValues={':pair': pair},
                    ScanIndexForward=False,
                    Limit=1
                )
                if response.get('Items'):
                    item = response['Items'][0]
                    bid = float(item.get('bid', 0))
                    ask = float(item.get('ask', 0))
                    prices[pair] = (bid + ask) / 2 if bid and ask else float(item.get('price', 0))
        except Exception as e:
            logger.warning(f"Error fetching current prices: {e}")
        return prices
    
    def get_trading_performance(self) -> Dict[str, Any]:
        """Get trading performance metrics"""
        try:
            # Get trading data for last 30 days
            current_time = datetime.utcnow()
            start_time = current_time - timedelta(days=30)
            
            response = self.trading_table.scan(
                FilterExpression='#ts BETWEEN :start_time AND :end_time',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={
                    ':start_time': start_time.isoformat(),
                    ':end_time': current_time.isoformat()
                }
            )
            
            trades = response.get('Items', [])
            
            # Analyze performance by day
            daily_performance = {}
            crypto_trades = 0
            forex_trades = 0
            total_volume = 0.0
            total_wins = 0.0
            total_losses = 0.0
            win_count = 0
            loss_count = 0
            current_streak = 0
            best_streak = 0
            worst_streak = 0
            largest_win = 0.0
            largest_loss = 0.0
            
            for trade in sorted(trades, key=lambda x: x['timestamp']):
                trade_date = trade['timestamp'][:10]  # YYYY-MM-DD
                trade_value = float(trade.get('value', 0))
                total_volume += trade_value
                
                if trade.get('marketType') == 'crypto':
                    crypto_trades += 1
                elif trade.get('marketType') == 'forex':
                    forex_trades += 1
                
                # Group by date for performance tracking
                if trade_date not in daily_performance:
                    daily_performance[trade_date] = {
                        'date': trade_date,
                        'trades': 0,
                        'volume': 0.0,
                        'pnl': 0.0
                    }
                
                daily_performance[trade_date]['trades'] += 1
                daily_performance[trade_date]['volume'] += trade_value
                
                if trade.get('pnl'):
                    pnl = float(trade['pnl'])
                    daily_performance[trade_date]['pnl'] += pnl
                    if pnl > 0:
                        total_wins += pnl
                        win_count += 1
                        largest_win = max(largest_win, pnl)
                        current_streak = max(1, current_streak + 1) if current_streak >= 0 else 1
                        best_streak = max(best_streak, current_streak)
                    elif pnl < 0:
                        total_losses += abs(pnl)
                        loss_count += 1
                        largest_loss = min(largest_loss, pnl)
                        current_streak = min(-1, current_streak - 1) if current_streak <= 0 else -1
                        worst_streak = min(worst_streak, current_streak)
            
            # Convert to list and sort by date
            performance_data = sorted(daily_performance.values(), key=lambda x: x['date'])
            
            # Profit factor
            profit_factor = (total_wins / total_losses) if total_losses > 0 else (float('inf') if total_wins > 0 else 0)
            avg_win = total_wins / max(win_count, 1)
            avg_loss = total_losses / max(loss_count, 1)
            expectancy = (avg_win * win_count - avg_loss * loss_count) / max(win_count + loss_count, 1)
            
            return {
                'dailyPerformance': performance_data,
                'totalTrades': len(trades),
                'cryptoTrades': crypto_trades,
                'forexTrades': forex_trades,
                'totalVolume': round(total_volume, 2),
                'avgTradeSize': round(total_volume / max(len(trades), 1), 2),
                'profitFactor': round(profit_factor, 2) if profit_factor != float('inf') else 'N/A',
                'avgWin': round(avg_win, 4),
                'avgLoss': round(avg_loss, 4),
                'largestWin': round(largest_win, 4),
                'largestLoss': round(largest_loss, 4),
                'bestStreak': best_streak,
                'worstStreak': abs(worst_streak),
                'expectancy': round(expectancy, 4)
            }
            
        except Exception as e:
            logger.error(f"Error getting trading performance: {str(e)}")
            return {
                'dailyPerformance': [],
                'totalTrades': 0,
                'cryptoTrades': 0,
                'forexTrades': 0,
                'totalVolume': 0.0,
                'avgTradeSize': 0.0,
                'profitFactor': 0,
                'avgWin': 0,
                'avgLoss': 0,
                'largestWin': 0,
                'largestLoss': 0,
                'bestStreak': 0,
                'worstStreak': 0,
                'expectancy': 0
            }
    
    def get_price_history(self) -> List[Dict[str, Any]]:
        """Get recent price history for charts"""
        try:
            price_history = []
            
            # Get crypto price history
            crypto_symbols = ['BTC', 'ETH', 'ADA', 'SOL']
            for symbol in crypto_symbols:
                response = self.crypto_table.query(
                    KeyConditionExpression='symbol = :symbol',
                    ExpressionAttributeValues={':symbol': symbol},
                    ScanIndexForward=False,
                    Limit=100
                )
                
                for item in response.get('Items', []):
                    price_history.append({
                        'symbol': symbol,
                        'type': 'crypto',
                        'timestamp': item['timestamp'],
                        'price': float(item.get('price', 0)),
                        'volume': float(item.get('volume', 0))
                    })
            
            # Get forex price history
            forex_pairs = ['EURUSD', 'GBPUSD', 'USDJPY']
            for pair in forex_pairs:
                response = self.forex_table.query(
                    KeyConditionExpression='pair = :pair',
                    ExpressionAttributeValues={':pair': pair},
                    ScanIndexForward=False,
                    Limit=100
                )
                
                for item in response.get('Items', []):
                    bid = float(item.get('bid', 0))
                    ask = float(item.get('ask', 0))
                    mid_price = (bid + ask) / 2
                    
                    price_history.append({
                        'symbol': pair,
                        'type': 'forex',
                        'timestamp': item['timestamp'],
                        'price': mid_price,
                        'bid': bid,
                        'ask': ask,
                        'spread': float(item.get('spread', 0))
                    })
            
            # Sort by timestamp
            price_history.sort(key=lambda x: x['timestamp'])
            
            logger.info(f"Retrieved {len(price_history)} price data points")
            return price_history
            
        except Exception as e:
            logger.error(f"Error getting price history: {str(e)}")
            return []
    
    def get_market_summary(self) -> Dict[str, Any]:
        """Get current market summary"""
        try:
            current_prices = {}
            
            # Get latest crypto prices
            crypto_symbols = ['BTC', 'ETH', 'ADA', 'SOL', 'LINK', 'AVAX']
            for symbol in crypto_symbols:
                response = self.crypto_table.query(
                    KeyConditionExpression='symbol = :symbol',
                    ExpressionAttributeValues={':symbol': symbol},
                    ScanIndexForward=False,
                    Limit=1
                )
                
                if response['Items']:
                    item = response['Items'][0]
                    current_prices[symbol] = {
                        'price': float(item.get('price', 0)),
                        'change24h': float(item.get('priceChangePercent24h', 0)),
                        'volume': float(item.get('volume', 0)),
                        'type': 'crypto'
                    }
            
            # Get latest forex prices
            forex_pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF']
            for pair in forex_pairs:
                response = self.forex_table.query(
                    KeyConditionExpression='pair = :pair',
                    ExpressionAttributeValues={':pair': pair},
                    ScanIndexForward=False,
                    Limit=1
                )
                
                if response['Items']:
                    item = response['Items'][0]
                    bid = float(item.get('bid', 0))
                    ask = float(item.get('ask', 0))
                    mid_price = (bid + ask) / 2
                    
                    current_prices[pair] = {
                        'price': mid_price,
                        'change24h': float(item.get('priceChangePercent24h', 0)),
                        'spread': float(item.get('spread', 0)),
                        'type': 'forex'
                    }
            
            return current_prices
            
        except Exception as e:
            logger.error(f"Error getting market summary: {str(e)}")
            return {}
    
    def get_ai_model_performance(self) -> Dict[str, Any]:
        """Get AI model performance metrics"""
        try:
            # Get latest model information
            response = self.ai_models_table.scan()
            models = response.get('Items', [])
            
            if not models:
                return {
                    'latestModel': None,
                    'accuracy': 0.0,
                    'trainingHistory': []
                }
            
            # Sort by timestamp to get latest
            latest_model = max(models, key=lambda x: x['timestamp'])
            
            # Prepare training history
            training_history = [
                {
                    'modelId': model['modelId'],
                    'timestamp': model['timestamp'],
                    'accuracy': float(model.get('overallAccuracy', 0)),
                    'cryptoAccuracy': float(model.get('cryptoAccuracy', 0)),
                    'forexAccuracy': float(model.get('forexAccuracy', 0))
                }
                for model in sorted(models, key=lambda x: x['timestamp'])
            ]
            
            # Compute model performance stats
            accuracies = [float(m.get('overallAccuracy', 0)) for m in models]
            valid_accuracies = [a for a in accuracies if a > 0.5]  # Exclude initial baseline models
            avg_accuracy = sum(valid_accuracies) / len(valid_accuracies) if valid_accuracies else 0
            best_accuracy = max(accuracies) if accuracies else 0
            
            # Model age
            latest_ts = latest_model['timestamp']
            try:
                model_age_hours = (datetime.utcnow() - datetime.fromisoformat(latest_ts)).total_seconds() / 3600
            except:
                model_age_hours = 0
            
            # Accuracy trend (improving or declining)
            recent_accs = [float(m.get('overallAccuracy', 0)) for m in sorted(models, key=lambda x: x['timestamp'])[-3:]]
            trend = 'improving' if len(recent_accs) >= 2 and recent_accs[-1] > recent_accs[0] else 'stable' if len(recent_accs) < 2 else 'declining'
            
            return {
                'latestModel': {
                    'modelId': latest_model['modelId'],
                    'timestamp': latest_model['timestamp'],
                    'accuracy': float(latest_model.get('overallAccuracy', 0)),
                    'cryptoAccuracy': float(latest_model.get('cryptoAccuracy', 0)),
                    'forexAccuracy': float(latest_model.get('forexAccuracy', 0))
                },
                'accuracy': float(latest_model.get('overallAccuracy', 0)),
                'avgAccuracy': round(avg_accuracy, 4),
                'bestAccuracy': round(best_accuracy, 4),
                'totalModels': len(models),
                'modelAgeHours': round(model_age_hours, 1),
                'accuracyTrend': trend,
                'trainingInterval': '6h',
                'trainingHistory': training_history[-10:]  # Last 10 models
            }
            
        except Exception as e:
            logger.error(f"Error getting AI model performance: {str(e)}")
            return {
                'latestModel': None,
                'accuracy': 0.0,
                'trainingHistory': []
            }
    
    def get_recent_trades(self) -> List[Dict[str, Any]]:
        """Get recent trades for display"""
        try:
            current_time = datetime.utcnow()
            start_time = current_time - timedelta(days=7)
            
            response = self.trading_table.scan(
                FilterExpression='#ts BETWEEN :start_time AND :end_time',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={
                    ':start_time': start_time.isoformat(),
                    ':end_time': current_time.isoformat()
                }
            )
            
            trades = response.get('Items', [])
            
            # Format trades for display
            formatted_trades = [
                {
                    'tradeId': trade['tradeId'],
                    'symbol': trade['symbol'],
                    'action': trade['action'],
                    'quantity': float(trade['quantity']),
                    'price': float(trade['price']),
                    'value': float(trade.get('value', 0)),
                    'timestamp': trade['timestamp'],
                    'pnl': float(trade.get('pnl', 0)) if trade.get('pnl') else None,
                    'pnlPercent': float(trade.get('pnlPercent', 0)) if trade.get('pnlPercent') else None,
                    'marketType': trade.get('marketType', 'unknown')
                }
                for trade in trades
            ]
            
            # Sort by timestamp (newest first)
            formatted_trades.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return formatted_trades[:20]  # Return last 20 trades
            
        except Exception as e:
            logger.error(f"Error getting recent trades: {str(e)}")
            return []
    
    def calculate_risk_metrics(self) -> Dict[str, Any]:
        """Calculate portfolio risk metrics"""
        try:
            # Get trading data for risk analysis
            current_time = datetime.utcnow()
            start_time = current_time - timedelta(days=30)
            
            response = self.trading_table.scan(
                FilterExpression='#ts BETWEEN :start_time AND :end_time',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={
                    ':start_time': start_time.isoformat(),
                    ':end_time': current_time.isoformat()
                }
            )
            
            trades = response.get('Items', [])
            
            # Calculate returns for risk analysis
            returns = []
            for trade in trades:
                if trade.get('pnlPercent'):
                    returns.append(float(trade['pnlPercent']))
            
            if not returns:
                return {
                    'sharpeRatio': 0.0,
                    'maxDrawdown': 0.0,
                    'volatility': 0.0,
                    'varDaily': 0.0
                }
            
            # Calculate risk metrics
            import numpy as np
            
            returns_array = np.array(returns)
            
            # Sharpe ratio (assuming 0% risk-free rate)
            sharpe_ratio = np.mean(returns_array) / (np.std(returns_array) + 1e-10)
            
            # Volatility
            volatility = np.std(returns_array)
            
            # Max drawdown (simplified)
            cumulative_returns = np.cumsum(returns_array)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdown = cumulative_returns - running_max
            max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0.0
            
            # Value at Risk (95% confidence, 1 day)
            var_daily = np.percentile(returns_array, 5) if len(returns_array) > 0 else 0.0
            
            return {
                'sharpeRatio': round(sharpe_ratio, 2),
                'maxDrawdown': round(max_drawdown, 2),
                'volatility': round(volatility, 2),
                'varDaily': round(var_daily, 2)
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {str(e)}")
            return {
                'sharpeRatio': 0.0,
                'maxDrawdown': 0.0,
                'volatility': 0.0,
                'varDaily': 0.0
            }
    
    def generate_alerts(self) -> List[Dict[str, Any]]:
        """Generate system alerts and notifications"""
        alerts = []
        
        try:
            # Check for system issues
            portfolio_summary = self.get_portfolio_summary()
            
            # Alert if portfolio value is down significantly
            if portfolio_summary['totalReturn'] < -10:
                alerts.append({
                    'type': 'warning',
                    'title': 'Portfolio Down',
                    'message': f"Portfolio is down {portfolio_summary['totalReturn']:.1f}%",
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            # Alert if no recent trades
            recent_trades = self.get_recent_trades()
            if len(recent_trades) == 0:
                alerts.append({
                    'type': 'info',
                    'title': 'No Recent Activity',
                    'message': 'No trades executed in the last 7 days',
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            # Check AI model performance
            ai_performance = self.get_ai_model_performance()
            if ai_performance['accuracy'] < 0.55:
                alerts.append({
                    'type': 'warning',
                    'title': 'Low Model Accuracy',
                    'message': f"AI model accuracy is {ai_performance['accuracy']:.1%}",
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            logger.info(f"Generated {len(alerts)} alerts")
            return alerts
            
        except Exception as e:
            logger.error(f"Error generating alerts: {str(e)}")
            return []
    
    def save_dashboard_data_to_s3(self, dashboard_data: Dict[str, Any]):
        """Save dashboard data to S3 for frontend access"""
        try:
            # Save main dashboard data
            dashboard_json = json.dumps(dashboard_data, default=str)
            s3.put_object(
                Bucket=S3_BUCKET,
                Key='dashboard/latest_data.json',
                Body=dashboard_json,
                ContentType='application/json',
                CacheControl='max-age=300'  # 5 minutes cache
            )
            
            # Save historical snapshot
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            s3.put_object(
                Bucket=S3_BUCKET,
                Key=f'dashboard/history/data_{timestamp}.json',
                Body=dashboard_json,
                ContentType='application/json'
            )
            
            logger.info("Dashboard data saved to S3")
            
        except Exception as e:
            logger.error(f"Error saving dashboard data to S3: {str(e)}")
            raise


# Lambda handler function
updater = DashboardUpdater()

def lambda_handler(event, context):
    """AWS Lambda entry point"""
    return updater.lambda_handler(event, context)