"""
Paper Trader Lambda Function
Executes paper trades based on AI model predictions
Maintains trading portfolio and wallet balance
"""

import json
import logging
import os
import uuid
import io
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional

import boto3
import numpy as np
import pandas as pd
import joblib
from decimal import Decimal, ROUND_HALF_UP

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
INITIAL_BALANCE = float(os.environ.get('INITIAL_WALLET_BALANCE', '50.0'))

# Setup logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger(__name__)

class PaperTrader:
    """Paper trading system using AI predictions"""
    
    def __init__(self):
        self.crypto_table = dynamodb.Table(CRYPTO_TABLE)
        self.forex_table = dynamodb.Table(FOREX_TABLE)
        self.trading_table = dynamodb.Table(TRADING_TABLE)
        self.ai_models_table = dynamodb.Table(AI_MODELS_TABLE)
        
        self.portfolio = {}
        self.wallet_balance = INITIAL_BALANCE
        self.models = None
        self.scalers = None
        self.current_market_prices = {}
        
        # Trading parameters
        self.max_position_size = 0.2  # Max 20% of portfolio per trade
        self.stop_loss_pct = 0.05  # 5% stop loss
        self.take_profit_pct = 0.10  # 10% take profit
        self.min_confidence = 0.6  # Minimum prediction confidence
    
    def lambda_handler(self, event: Dict[str, Any], context) -> Dict[str, Any]:
        """Main Lambda handler for paper trading"""
        try:
            logger.info(f"Paper Trader started with event: {event}")
            
            request_type = event.get('requestType', 'trade_execution')
            use_latest_model = event.get('useLatestModel', True)
            
            if request_type == 'trade_execution':
                result = self.execute_trading_session()
                return {
                    'statusCode': 200,
                    'status': 'success',
                    'tradesExecuted': result['trades_executed'],
                    'portfolioValue': result['portfolio_value'],
                    'walletBalance': result['wallet_balance'],
                    'totalPnL': result['total_pnl'],
                    'message': 'Paper trading session completed'
                }
            elif request_type == 'portfolio_status':
                portfolio_status = self.get_portfolio_status()
                return {
                    'statusCode': 200,
                    'status': 'success',
                    'portfolio': portfolio_status
                }
            else:
                return {
                    'statusCode': 400,
                    'status': 'error',
                    'message': f'Unknown request type: {request_type}'
                }
                
        except Exception as e:
            logger.error(f"Error in paper trading: {str(e)}")
            return {
                'statusCode': 500,
                'status': 'error',
                'message': f'Trading failed: {str(e)}'
            }
    
    def execute_trading_session(self) -> Dict[str, Any]:
        """Execute a complete trading session"""
        logger.info("Starting trading session")
        
        # Load current portfolio state
        self.load_portfolio_state()
        
        # Load latest AI model
        model_loaded = self.load_latest_model()
        if not model_loaded:
            logger.warning("No AI model available, skipping trading")
            return {
                'trades_executed': 0,
                'portfolio_value': self.calculate_portfolio_value(),
                'wallet_balance': self.wallet_balance,
                'total_pnl': self.calculate_total_pnl()
            }
        
        # Get latest market data
        crypto_data = self.get_latest_crypto_data()
        forex_data = self.get_latest_forex_data()
        
        # Store current market prices for live portfolio valuation
        self.current_market_prices = {item['symbol']: item['price'] for item in crypto_data + forex_data}
        
        # Generate predictions
        crypto_predictions = self.predict_crypto_prices(crypto_data)
        forex_predictions = self.predict_forex_prices(forex_data)
        all_predictions = crypto_predictions + forex_predictions
        
        # Execute trades based on predictions
        trades_executed = 0
        
        # PHASE 1: Process EXIT signals for existing positions
        # The model should learn when to exit by generating SELL signals
        for prediction in all_predictions:
            symbol = prediction['symbol']
            if symbol in self.portfolio and prediction['signal'] == 'SELL':
                if prediction['confidence'] >= self.min_confidence:
                    trade_executed = self.execute_trade(prediction)
                    if trade_executed:
                        trades_executed += 1
                        logger.info(f"AI-driven exit: {symbol} (confidence: {prediction['confidence']:.2f})")
        
        # Check for stop loss / take profit triggers on remaining positions
        self.check_exit_conditions(crypto_data, forex_data)
        
        # PHASE 2: Process BUY signals for new positions
        for prediction in all_predictions:
            if self.should_trade(prediction):
                trade_executed = self.execute_trade(prediction)
                if trade_executed:
                    trades_executed += 1
        
        # Save portfolio state
        self.save_portfolio_state()
        
        result = {
            'trades_executed': trades_executed,
            'portfolio_value': self.calculate_portfolio_value(),
            'wallet_balance': self.wallet_balance,
            'total_pnl': self.calculate_total_pnl()
        }
        
        logger.info(f"Trading session completed: {result}")
        return result
    
    def load_latest_model(self) -> bool:
        """Load the latest AI model from S3"""
        try:
            # Get latest model metadata
            response = self.ai_models_table.scan()
            items = response.get('Items', [])
            
            if not items:
                logger.warning("No AI models found")
                return False
            
            # Sort by timestamp to get latest model
            latest_model = max(items, key=lambda x: x['timestamp'])
            
            # Download model from S3
            s3_path = latest_model['s3ModelPath']
            bucket, key = s3_path.replace('s3://', '').split('/', 1)
            
            response = s3.get_object(Bucket=bucket, Key=key)
            model_bytes = response['Body'].read()
            model_package = joblib.load(io.BytesIO(model_bytes))
            
            self.models = model_package['models']
            self.scalers = model_package['scalers']
            
            logger.info(f"Loaded AI model: {latest_model['modelId']}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading AI model: {str(e)}")
            return False
    
    def get_latest_crypto_data(self) -> List[Dict[str, Any]]:
        """Get latest crypto price data"""
        try:
            symbols = ['BTC', 'ETH', 'ADA', 'SOL', 'LINK', 'AVAX']
            crypto_data = []
            
            for symbol in symbols:
                # Get latest price for this symbol
                response = self.crypto_table.query(
                    KeyConditionExpression='symbol = :symbol',
                    ExpressionAttributeValues={':symbol': symbol},
                    ScanIndexForward=False,
                    Limit=1
                )
                
                if response['Items']:
                    item = response['Items'][0]
                    crypto_data.append({
                        'symbol': symbol,
                        'price': float(item.get('price', 0)),
                        'volume': float(item.get('volume', 0)),
                        'timestamp': item.get('timestamp', ''),
                        'market_type': 'crypto'
                    })
            
            logger.info(f"Fetched {len(crypto_data)} crypto prices")
            return crypto_data
            
        except Exception as e:
            logger.error(f"Error fetching crypto data: {str(e)}")
            return []
    
    def get_latest_forex_data(self) -> List[Dict[str, Any]]:
        """Get latest forex price data"""
        try:
            pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD']
            forex_data = []
            
            for pair in pairs:
                # Get latest price for this pair
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
                    
                    forex_data.append({
                        'symbol': pair,
                        'price': mid_price,
                        'bid': bid,
                        'ask': ask,
                        'spread': float(item.get('spread', 0)),
                        'timestamp': item.get('timestamp', ''),
                        'market_type': 'forex'
                    })
            
            logger.info(f"Fetched {len(forex_data)} forex prices")
            return forex_data
            
        except Exception as e:
            logger.error(f"Error fetching forex data: {str(e)}")
            return []
    
    def predict_crypto_prices(self, crypto_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate crypto price predictions"""
        predictions = []
        
        try:
            if not self.models or 'crypto_rf' not in self.models:
                return predictions
            
            for data in crypto_data:
                # Create features (simplified version)
                features = [
                    data['price'],  # current price
                    data['price'],  # price_lag1 (using current as approximation)
                    data['volume'],  # volume_lag1
                    0.0,  # price_change_pct (assume no change)
                    datetime.now().hour,  # hour
                    datetime.now().weekday(),  # day_of_week
                    0.0   # sentiment_score (neutral)
                ]
                
                # Scale features
                if 'crypto' in self.scalers:
                    features_scaled = self.scalers['crypto'].transform([features])
                else:
                    features_scaled = np.array([features])
                
                # Get predictions from both models
                rf_pred = self.models['crypto_rf'].predict(features_scaled)[0]
                gb_pred = self.models['crypto_gb'].predict(features_scaled)[0]
                
                # Ensemble prediction (average)
                ensemble_pred = (rf_pred + gb_pred) / 2
                
                # Calculate confidence and direction
                current_price = data['price']
                predicted_change = (ensemble_pred - current_price) / current_price
                confidence = min(abs(predicted_change) * 10, 1.0)  # Simplified confidence
                
                # For held positions, factor in unrealized PnL to decide exit
                signal = 'HOLD'
                symbol = data['symbol']
                if symbol in self.portfolio:
                    entry_price = self.portfolio[symbol]['entry_price']
                    unrealized_pnl_pct = (current_price - entry_price) / entry_price
                    # SELL if: model predicts price will drop, or position is losing and trending worse
                    if predicted_change < -0.01:  # Model predicts decline
                        signal = 'SELL'
                        confidence = max(confidence, 0.7)  # Boost confidence for exits
                    elif unrealized_pnl_pct >= self.take_profit_pct:  # Take profit
                        signal = 'SELL'
                        confidence = 0.9
                    elif unrealized_pnl_pct <= -self.stop_loss_pct:  # Stop loss
                        signal = 'SELL'
                        confidence = 0.95
                else:
                    # New position entry signals
                    if predicted_change > 0.02:
                        signal = 'BUY'
                    elif predicted_change < -0.02:
                        signal = 'SELL'  # Short signal (skip for now, no shorts)
                
                prediction = {
                    'symbol': symbol,
                    'market_type': 'crypto',
                    'current_price': current_price,
                    'predicted_price': ensemble_pred,
                    'predicted_change_pct': predicted_change * 100,
                    'confidence': confidence,
                    'signal': signal,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                predictions.append(prediction)
                
        except Exception as e:
            logger.error(f"Error predicting crypto prices: {str(e)}")
        
        return predictions
    
    def predict_forex_prices(self, forex_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate forex price predictions"""
        predictions = []
        
        try:
            if not self.models or 'forex_rf' not in self.models:
                return predictions
            
            for data in forex_data:
                # Create features (simplified version)
                features = [
                    data['bid'],  # bid_lag1
                    data['ask'],  # ask_lag1
                    data['spread'],  # spread_lag1
                    0.0,  # price_change_pct (assume no change)
                    datetime.now().hour,  # hour
                    datetime.now().weekday(),  # day_of_week
                    0.0   # sentiment_score (neutral)
                ]
                
                # Scale features
                if 'forex' in self.scalers:
                    features_scaled = self.scalers['forex'].transform([features])
                else:
                    features_scaled = np.array([features])
                
                # Get predictions from both models
                rf_pred = self.models['forex_rf'].predict(features_scaled)[0]
                gb_pred = self.models['forex_gb'].predict(features_scaled)[0]
                
                # Ensemble prediction (average)
                ensemble_pred = (rf_pred + gb_pred) / 2
                
                # Calculate confidence and direction
                current_price = data['price']
                predicted_change = (ensemble_pred - current_price) / current_price
                confidence = min(abs(predicted_change) * 20, 1.0)  # Forex has smaller moves
                
                # For held positions, factor in unrealized PnL to decide exit
                signal = 'HOLD'
                symbol = data['symbol']
                if symbol in self.portfolio:
                    entry_price = self.portfolio[symbol]['entry_price']
                    unrealized_pnl_pct = (current_price - entry_price) / entry_price
                    # SELL if: model predicts price will drop, or position is at profit/loss thresholds
                    if predicted_change < -0.0005:  # Model predicts decline (forex moves smaller)
                        signal = 'SELL'
                        confidence = max(confidence, 0.7)
                    elif unrealized_pnl_pct >= self.take_profit_pct:
                        signal = 'SELL'
                        confidence = 0.9
                    elif unrealized_pnl_pct <= -self.stop_loss_pct:
                        signal = 'SELL'
                        confidence = 0.95
                else:
                    # New position entry signals
                    if predicted_change > 0.001:
                        signal = 'BUY'
                    elif predicted_change < -0.001:
                        signal = 'SELL'
                
                prediction = {
                    'symbol': symbol,
                    'market_type': 'forex',
                    'current_price': current_price,
                    'predicted_price': ensemble_pred,
                    'predicted_change_pct': predicted_change * 100,
                    'confidence': confidence,
                    'signal': signal,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                predictions.append(prediction)
                
        except Exception as e:
            logger.error(f"Error predicting forex prices: {str(e)}")
        
        return predictions
    
    def should_trade(self, prediction: Dict[str, Any]) -> bool:
        """Determine if a trade should be executed based on prediction"""
        # Check minimum confidence
        if prediction['confidence'] < self.min_confidence:
            return False
        
        # Check if signal is actionable
        if prediction['signal'] == 'HOLD':
            return False
        
        # SELL signals for existing positions are handled in Phase 1
        # Here we only gate BUY signals for new entries
        if prediction['signal'] == 'SELL':
            return False  # Exits are handled separately
        
        # Check if we have sufficient balance for a BUY
        position_value = self.wallet_balance * self.max_position_size
        if position_value < 1.0:  # Minimum $1 trade
            return False
        
        # Check if already have position in this symbol (avoid doubling up)
        if prediction['symbol'] in self.portfolio:
            return False
        
        return True
    
    def execute_trade(self, prediction: Dict[str, Any]) -> bool:
        """Execute a paper trade based on prediction"""
        try:
            symbol = prediction['symbol']
            signal = prediction['signal']
            current_price = prediction['current_price']
            confidence = prediction['confidence']
            
            # Calculate position size based on confidence and available balance
            base_position_size = self.wallet_balance * self.max_position_size
            position_size = base_position_size * confidence
            
            if signal == 'BUY':
                # Calculate quantity to buy
                quantity = position_size / current_price
                
                # Execute buy order
                trade_id = str(uuid.uuid4())
                trade = {
                    'tradeId': trade_id,
                    'symbol': symbol,
                    'marketType': prediction['market_type'],
                    'action': 'BUY',
                    'quantity': str(quantity),
                    'price': str(current_price),
                    'value': str(position_size),
                    'confidence': str(confidence),
                    'timestamp': datetime.utcnow().isoformat(),
                    'status': 'EXECUTED',
                    'walletBalanceBefore': str(self.wallet_balance),
                    'predictedChange': str(prediction['predicted_change_pct'])
                }
                
                # Update portfolio
                self.portfolio[symbol] = {
                    'quantity': quantity,
                    'entry_price': current_price,
                    'entry_time': datetime.utcnow().isoformat(),
                    'trade_id': trade_id,
                    'market_type': prediction['market_type']
                }
                
                # Update wallet balance
                self.wallet_balance -= position_size
                trade['walletBalanceAfter'] = str(self.wallet_balance)
                
                # Save trade to DynamoDB
                self.trading_table.put_item(Item=trade)
                
                logger.info(f"Executed BUY trade: {symbol} @ {current_price}, quantity: {quantity}")
                return True
                
            elif signal == 'SELL' and symbol in self.portfolio:
                # Close existing position
                position = self.portfolio[symbol]
                quantity = position['quantity']
                entry_price = position['entry_price']
                
                # Calculate P&L
                pnl = (current_price - entry_price) * quantity
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
                
                trade_id = str(uuid.uuid4())
                trade = {
                    'tradeId': trade_id,
                    'symbol': symbol,
                    'marketType': prediction['market_type'],
                    'action': 'SELL',
                    'quantity': str(quantity),
                    'price': str(current_price),
                    'value': str(current_price * quantity),
                    'entryPrice': str(entry_price),
                    'pnl': str(pnl),
                    'pnlPercent': str(pnl_pct),
                    'timestamp': datetime.utcnow().isoformat(),
                    'status': 'EXECUTED',
                    'walletBalanceBefore': str(self.wallet_balance),
                    'originalTradeId': position['trade_id']
                }
                
                # Update wallet balance
                self.wallet_balance += current_price * quantity
                trade['walletBalanceAfter'] = str(self.wallet_balance)
                
                # Remove from portfolio
                del self.portfolio[symbol]
                
                # Save trade to DynamoDB
                self.trading_table.put_item(Item=trade)
                
                logger.info(f"Executed SELL trade: {symbol} @ {current_price}, P&L: ${pnl:.2f}")
                return True
                
        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}")
            return False
        
        return False
    
    def check_exit_conditions(self, crypto_data: List[Dict[str, Any]], forex_data: List[Dict[str, Any]]):
        """Check stop loss and take profit conditions"""
        all_data = {item['symbol']: item for item in crypto_data + forex_data}
        
        symbols_to_close = []
        
        for symbol, position in self.portfolio.items():
            if symbol not in all_data:
                continue
                
            current_price = all_data[symbol]['price']
            entry_price = position['entry_price']
            
            # Calculate current P&L percentage
            pnl_pct = ((current_price - entry_price) / entry_price)
            
            # Check stop loss
            if pnl_pct <= -self.stop_loss_pct:
                logger.info(f"Stop loss triggered for {symbol}: {pnl_pct:.2%}")
                symbols_to_close.append((symbol, current_price, 'STOP_LOSS'))
            
            # Check take profit
            elif pnl_pct >= self.take_profit_pct:
                logger.info(f"Take profit triggered for {symbol}: {pnl_pct:.2%}")
                symbols_to_close.append((symbol, current_price, 'TAKE_PROFIT'))
        
        # Close positions that hit exit conditions
        for symbol, price, reason in symbols_to_close:
            self.close_position(symbol, price, reason)
    
    def close_position(self, symbol: str, current_price: float, reason: str):
        """Close a position"""
        try:
            if symbol not in self.portfolio:
                return
                
            position = self.portfolio[symbol]
            quantity = position['quantity']
            entry_price = position['entry_price']
            
            # Calculate P&L
            pnl = (current_price - entry_price) * quantity
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
            
            trade_id = str(uuid.uuid4())
            trade = {
                'tradeId': trade_id,
                'symbol': symbol,
                'marketType': position['market_type'],
                'action': 'SELL',
                'quantity': str(quantity),
                'price': str(current_price),
                'value': str(current_price * quantity),
                'entryPrice': str(entry_price),
                'pnl': str(pnl),
                'pnlPercent': str(pnl_pct),
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'EXECUTED',
                'exitReason': reason,
                'walletBalanceBefore': str(self.wallet_balance),
                'originalTradeId': position['trade_id']
            }
            
            # Update wallet balance
            self.wallet_balance += current_price * quantity
            trade['walletBalanceAfter'] = str(self.wallet_balance)
            
            # Remove from portfolio
            del self.portfolio[symbol]
            
            # Save trade to DynamoDB
            self.trading_table.put_item(Item=trade)
            
            logger.info(f"Closed position {symbol} ({reason}): P&L ${pnl:.2f}")
            
        except Exception as e:
            logger.error(f"Error closing position {symbol}: {str(e)}")
    
    def load_portfolio_state(self):
        """Load current portfolio state from DynamoDB"""
        try:
            # Get recent trades to reconstruct portfolio
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
            
            # Reconstruct portfolio and wallet balance
            self.wallet_balance = INITIAL_BALANCE
            self.portfolio = {}
            
            for trade in sorted(trades, key=lambda x: x['timestamp']):
                symbol = trade['symbol']
                action = trade['action']
                quantity = float(trade['quantity'])
                price = float(trade['price'])
                
                if action == 'BUY':
                    self.portfolio[symbol] = {
                        'quantity': quantity,
                        'entry_price': price,
                        'entry_time': trade['timestamp'],
                        'trade_id': trade['tradeId'],
                        'market_type': trade.get('marketType', 'unknown')
                    }
                    self.wallet_balance -= price * quantity
                    
                elif action == 'SELL' and symbol in self.portfolio:
                    del self.portfolio[symbol]
                    self.wallet_balance += price * quantity
                    
            logger.info(f"Portfolio loaded: {len(self.portfolio)} positions, balance: ${self.wallet_balance:.2f}")
            
        except Exception as e:
            # If error loading, start with initial state
            logger.warning(f"Error loading portfolio state: {str(e)}, using initial state")
            self.wallet_balance = INITIAL_BALANCE
            self.portfolio = {}
    
    def save_portfolio_state(self):
        """Save current portfolio state"""
        # Portfolio state is automatically saved via trade records
        # This method can be used for additional state persistence if needed
        logger.info(f"Portfolio state: {len(self.portfolio)} positions, balance: ${self.wallet_balance:.2f}")
    
    def calculate_portfolio_value(self) -> float:
        """Calculate total portfolio value using current market prices"""
        total_value = self.wallet_balance
        
        for symbol, position in self.portfolio.items():
            # Use current market price if available, otherwise fall back to entry price
            current_price = getattr(self, 'current_market_prices', {}).get(
                symbol, position['entry_price']
            )
            position_value = position['quantity'] * current_price
            total_value += position_value
            
        return total_value
    
    def calculate_total_pnl(self) -> float:
        """Calculate total profit/loss"""
        return self.calculate_portfolio_value() - INITIAL_BALANCE
    
    def get_portfolio_status(self) -> Dict[str, Any]:
        """Get current portfolio status"""
        return {
            'walletBalance': self.wallet_balance,
            'portfolioValue': self.calculate_portfolio_value(),
            'totalPnL': self.calculate_total_pnl(),
            'positions': len(self.portfolio),
            'openPositions': [
                {
                    'symbol': symbol,
                    'quantity': pos['quantity'],
                    'entryPrice': pos['entry_price'],
                    'entryTime': pos['entry_time'],
                    'marketType': pos['market_type']
                }
                for symbol, pos in self.portfolio.items()
            ]
        }


# Lambda handler function
trader = PaperTrader()

def lambda_handler(event, context):
    """AWS Lambda entry point"""
    return trader.lambda_handler(event, context)