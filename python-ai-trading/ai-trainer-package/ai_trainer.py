"""
AI Trainer Lambda Function for Crypto and Forex Trading
Trains machine learning models every 6 hours using latest market data
"""

import json
import logging
import os
import uuid
import io
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
from decimal import Decimal

import boto3
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_absolute_error, r2_score
import joblib


def convert_decimals(obj):
    """Convert DynamoDB Decimal types to float for pandas compatibility"""
    if isinstance(obj, list):
        return [convert_decimals(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    return obj

# AWS Clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

# Configuration
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
S3_BUCKET = os.environ.get('S3_BUCKET_MODELS', 'forex-ai-models')
CRYPTO_TABLE = os.environ.get('DYNAMODB_CRYPTO_TABLE', 'CryptoPriceData')
FOREX_TABLE = os.environ.get('DYNAMODB_FOREX_TABLE', 'ForexPriceData')
NEWS_TABLE = os.environ.get('DYNAMODB_NEWS_TABLE', 'NewsData')
AI_MODELS_TABLE = os.environ.get('DYNAMODB_AI_MODELS_TABLE', 'AIModelMetadata')

# Setup logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger(__name__)

class TradingAITrainer:
    """AI Trainer for cryptocurrency and forex trading predictions"""
    
    def __init__(self):
        self.crypto_table = dynamodb.Table(CRYPTO_TABLE)
        self.forex_table = dynamodb.Table(FOREX_TABLE)
        self.news_table = dynamodb.Table(NEWS_TABLE)
        self.ai_models_table = dynamodb.Table(AI_MODELS_TABLE)
        
        self.models = {
            'crypto_rf': RandomForestRegressor(n_estimators=100, random_state=42),
            'crypto_gb': GradientBoostingRegressor(n_estimators=100, random_state=42),
            'forex_rf': RandomForestRegressor(n_estimators=100, random_state=42),
            'forex_gb': GradientBoostingRegressor(n_estimators=100, random_state=42)
        }
        
        self.scalers = {}
    
    def lambda_handler(self, event: Dict[str, Any], context) -> Dict[str, Any]:
        """Main Lambda handler for AI training"""
        try:
            logger.info(f"AI Training started with event: {event}")
            
            request_type = event.get('requestType', 'training')
            model_type = event.get('modelType', 'ensemble')
            
            if request_type == 'training':
                result = self.train_models()
                return {
                    'statusCode': 200,
                    'modelId': result['modelId'],
                    'status': 'success',
                    'accuracy': result['accuracy'],
                    's3ModelPath': result['s3Path'],
                    'message': 'AI models trained successfully'
                }
            else:
                return {
                    'statusCode': 400,
                    'status': 'error',
                    'message': f'Unknown request type: {request_type}'
                }
                
        except Exception as e:
            logger.error(f"Error in AI training: {str(e)}")
            return {
                'statusCode': 500,
                'status': 'error',
                'message': f'Training failed: {str(e)}'
            }
    
    def train_models(self) -> Dict[str, Any]:
        """Train all AI models and save to S3"""
        model_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        
        logger.info(f"Starting training for model ID: {model_id}")
        
        # Fetch and prepare data
        crypto_data = self.fetch_crypto_data()
        forex_data = self.fetch_forex_data()
        news_sentiment = self.fetch_news_sentiment()
        
        # Train models
        crypto_accuracy = self.train_crypto_models(crypto_data, news_sentiment)
        forex_accuracy = self.train_forex_models(forex_data, news_sentiment)
        
        # Save models to S3
        s3_path = self.save_models_to_s3(model_id)
        
        # Save metadata to DynamoDB
        self.save_model_metadata(model_id, timestamp, crypto_accuracy, forex_accuracy, s3_path)
        
        overall_accuracy = (crypto_accuracy + forex_accuracy) / 2
        
        logger.info(f"Training completed. Overall accuracy: {overall_accuracy:.4f}")
        
        return {
            'modelId': model_id,
            'accuracy': round(overall_accuracy, 4),
            's3Path': s3_path,
            'cryptoAccuracy': round(crypto_accuracy, 4),
            'forexAccuracy': round(forex_accuracy, 4)
        }
    
    def fetch_crypto_data(self) -> pd.DataFrame:
        """Fetch crypto price data from DynamoDB"""
        try:
            # Get data from last 30 days
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=30)
            
            # Scan table for recent data (in production, use more efficient querying)
            response = self.crypto_table.scan(
                FilterExpression='#ts BETWEEN :start_time AND :end_time',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={
                    ':start_time': start_time.isoformat(),
                    ':end_time': end_time.isoformat()
                },
                Limit=10000
            )
            
            items = response['Items']
            
            if not items:
                logger.warning("No crypto data found, using mock data for training")
                return self.generate_mock_crypto_data()
            
            # Convert DynamoDB Decimal types to float
            items = convert_decimals(items)
            df = pd.DataFrame(items)
            df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601', utc=True)
            df = df.sort_values('timestamp')
            
            # Convert numeric columns (DynamoDB returns Decimal types)
            numeric_columns = ['price', 'volume', 'marketCap', 'priceChange24h', 'priceChangePercent24h']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            logger.info(f"Fetched {len(df)} crypto data points")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching crypto data: {str(e)}")
            return self.generate_mock_crypto_data()
    
    def fetch_forex_data(self) -> pd.DataFrame:
        """Fetch forex price data from DynamoDB"""
        try:
            # Get data from last 30 days
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=30)
            
            response = self.forex_table.scan(
                FilterExpression='#ts BETWEEN :start_time AND :end_time',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={
                    ':start_time': start_time.isoformat(),
                    ':end_time': end_time.isoformat()
                },
                Limit=10000
            )
            
            items = response['Items']
            
            if not items:
                logger.warning("No forex data found, using mock data for training")
                return self.generate_mock_forex_data()
            
            # Convert DynamoDB Decimal types to float
            items = convert_decimals(items)
            df = pd.DataFrame(items)
            df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601', utc=True)
            df = df.sort_values('timestamp')
            
            # Convert numeric columns (DynamoDB returns Decimal types)
            numeric_columns = ['bid', 'ask', 'spread', 'high24h', 'low24h', 'priceChange24h']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            logger.info(f"Fetched {len(df)} forex data points")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching forex data: {str(e)}")
            return self.generate_mock_forex_data()
    
    def fetch_news_sentiment(self) -> pd.DataFrame:
        """Fetch news sentiment data from DynamoDB"""
        try:
            # Get data from last 7 days
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=7)
            
            response = self.news_table.scan(
                FilterExpression='#ts BETWEEN :start_time AND :end_time',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={
                    ':start_time': start_time.isoformat(),
                    ':end_time': end_time.isoformat()
                },
                Limit=5000
            )
            
            items = response['Items']
            
            if not items:
                logger.warning("No news data found, using neutral sentiment")
                return pd.DataFrame({'sentiment_score': [0.0], 'timestamp': [datetime.utcnow()]})
            
            df = pd.DataFrame(items)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Extract sentiment scores
            if 'overallSentiment' in df.columns:
                df['sentiment_score'] = pd.to_numeric(df['overallSentiment'], errors='coerce')
            else:
                df['sentiment_score'] = 0.0
            
            # Aggregate daily sentiment
            df['date'] = df['timestamp'].dt.date
            daily_sentiment = df.groupby('date')['sentiment_score'].mean().reset_index()
            daily_sentiment['timestamp'] = pd.to_datetime(daily_sentiment['date'])
            
            logger.info(f"Processed {len(daily_sentiment)} days of news sentiment")
            return daily_sentiment
            
        except Exception as e:
            logger.error(f"Error fetching news sentiment: {str(e)}")
            return pd.DataFrame({'sentiment_score': [0.0], 'timestamp': [datetime.utcnow()]})
    
    def train_crypto_models(self, crypto_data: pd.DataFrame, news_sentiment: pd.DataFrame) -> float:
        """Train crypto prediction models"""
        try:
            # Feature engineering for crypto data
            features_df = self.engineer_crypto_features(crypto_data, news_sentiment)
            
            if len(features_df) < 10:
                logger.warning("Insufficient crypto data for training")
                return 0.5
            
            # Prepare features and targets
            feature_columns = ['price_lag1', 'price_lag2', 'volume_lag1', 'price_change_pct', 
                              'hour', 'day_of_week', 'sentiment_score']
            
            X = features_df[feature_columns].fillna(0)
            y = features_df['price_next'].fillna(features_df['price_next'].mean())
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Scale features
            self.scalers['crypto'] = StandardScaler()
            X_train_scaled = self.scalers['crypto'].fit_transform(X_train)
            X_test_scaled = self.scalers['crypto'].transform(X_test)
            
            # Train models
            self.models['crypto_rf'].fit(X_train_scaled, y_train)
            self.models['crypto_gb'].fit(X_train_scaled, y_train)
            
            # Evaluate
            rf_score = self.models['crypto_rf'].score(X_test_scaled, y_test)
            gb_score = self.models['crypto_gb'].score(X_test_scaled, y_test)
            
            avg_accuracy = (rf_score + gb_score) / 2
            logger.info(f"Crypto models trained. RF Score: {rf_score:.4f}, GB Score: {gb_score:.4f}")
            
            return max(avg_accuracy, 0.0)
            
        except Exception as e:
            logger.error(f"Error training crypto models: {str(e)}")
            return 0.5
    
    def train_forex_models(self, forex_data: pd.DataFrame, news_sentiment: pd.DataFrame) -> float:
        """Train forex prediction models"""
        try:
            # Feature engineering for forex data
            features_df = self.engineer_forex_features(forex_data, news_sentiment)
            
            if len(features_df) < 10:
                logger.warning("Insufficient forex data for training")
                return 0.5
            
            # Prepare features and targets
            feature_columns = ['bid_lag1', 'ask_lag1', 'spread_lag1', 'price_change_pct',
                              'hour', 'day_of_week', 'sentiment_score']
            
            X = features_df[feature_columns].fillna(0)
            y = features_df['mid_price_next'].fillna(features_df['mid_price_next'].mean())
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Scale features
            self.scalers['forex'] = StandardScaler()
            X_train_scaled = self.scalers['forex'].fit_transform(X_train)
            X_test_scaled = self.scalers['forex'].transform(X_test)
            
            # Train models
            self.models['forex_rf'].fit(X_train_scaled, y_train)
            self.models['forex_gb'].fit(X_train_scaled, y_train)
            
            # Evaluate
            rf_score = self.models['forex_rf'].score(X_test_scaled, y_test)
            gb_score = self.models['forex_gb'].score(X_test_scaled, y_test)
            
            avg_accuracy = (rf_score + gb_score) / 2
            logger.info(f"Forex models trained. RF Score: {rf_score:.4f}, GB Score: {gb_score:.4f}")
            
            return max(avg_accuracy, 0.0)
            
        except Exception as e:
            logger.error(f"Error training forex models: {str(e)}")
            return 0.5
    
    def engineer_crypto_features(self, crypto_data: pd.DataFrame, news_sentiment: pd.DataFrame) -> pd.DataFrame:
        """Create features for crypto prediction"""
        try:
            # Group by symbol and create features
            features_list = []
            
            for symbol in crypto_data['symbol'].unique():
                symbol_data = crypto_data[crypto_data['symbol'] == symbol].copy()
                symbol_data = symbol_data.sort_values('timestamp').reset_index(drop=True)
                
                if len(symbol_data) < 5:
                    continue
                
                # Price-based features
                symbol_data['price_lag1'] = symbol_data['price'].shift(1)
                symbol_data['price_lag2'] = symbol_data['price'].shift(2)
                symbol_data['volume_lag1'] = symbol_data['volume'].shift(1)
                symbol_data['price_change_pct'] = symbol_data['price'].pct_change()
                
                # Time features
                symbol_data['hour'] = symbol_data['timestamp'].dt.hour
                symbol_data['day_of_week'] = symbol_data['timestamp'].dt.dayofweek
                
                # Target variable (next price)
                symbol_data['price_next'] = symbol_data['price'].shift(-1)
                
                # Merge with sentiment data
                symbol_data['date'] = symbol_data['timestamp'].dt.normalize()
                if not news_sentiment.empty and 'date' in news_sentiment.columns:
                    symbol_data = symbol_data.merge(
                        news_sentiment[['date', 'sentiment_score']], 
                        on='date', 
                        how='left'
                    )
                    symbol_data['sentiment_score'] = symbol_data['sentiment_score'].fillna(0.0)
                else:
                    symbol_data['sentiment_score'] = 0.0
                
                features_list.append(symbol_data)
            
            if features_list:
                return pd.concat(features_list, ignore_index=True)
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error engineering crypto features: {str(e)}")
            return pd.DataFrame()
    
    def engineer_forex_features(self, forex_data: pd.DataFrame, news_sentiment: pd.DataFrame) -> pd.DataFrame:
        """Create features for forex prediction"""
        try:
            # Group by pair and create features
            features_list = []
            
            for pair in forex_data['pair'].unique():
                pair_data = forex_data[forex_data['pair'] == pair].copy()
                pair_data = pair_data.sort_values('timestamp').reset_index(drop=True)
                
                if len(pair_data) < 5:
                    continue
                
                # Calculate mid price
                pair_data['mid_price'] = (pair_data['bid'] + pair_data['ask']) / 2
                
                # Price-based features
                pair_data['bid_lag1'] = pair_data['bid'].shift(1)
                pair_data['ask_lag1'] = pair_data['ask'].shift(1)
                pair_data['spread_lag1'] = pair_data['spread'].shift(1)
                pair_data['price_change_pct'] = pair_data['mid_price'].pct_change()
                
                # Time features
                pair_data['hour'] = pair_data['timestamp'].dt.hour
                pair_data['day_of_week'] = pair_data['timestamp'].dt.dayofweek
                
                # Target variable (next mid price)
                pair_data['mid_price_next'] = pair_data['mid_price'].shift(-1)
                
                # Merge with sentiment data
                pair_data['date'] = pair_data['timestamp'].dt.normalize()
                if not news_sentiment.empty and 'date' in news_sentiment.columns:
                    pair_data = pair_data.merge(
                        news_sentiment[['date', 'sentiment_score']], 
                        on='date', 
                        how='left'
                    )
                    pair_data['sentiment_score'] = pair_data['sentiment_score'].fillna(0.0)
                else:
                    pair_data['sentiment_score'] = 0.0
                
                features_list.append(pair_data)
            
            if features_list:
                return pd.concat(features_list, ignore_index=True)
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error engineering forex features: {str(e)}")
            return pd.DataFrame()
    
    def save_models_to_s3(self, model_id: str) -> str:
        """Save trained models and scalers to S3"""
        try:
            # Create model package
            model_package = {
                'models': self.models,
                'scalers': self.scalers,
                'model_id': model_id,
                'timestamp': datetime.utcnow().isoformat(),
                'metadata': {
                    'crypto_symbols': ['BTC', 'ETH', 'ADA', 'SOL'],
                    'forex_pairs': ['EURUSD', 'GBPUSD', 'USDJPY'],
                    'features': ['price_lag1', 'price_lag2', 'volume_lag1', 'sentiment_score']
                }
            }
            
            # Serialize models to bytes via BytesIO
            buffer = io.BytesIO()
            joblib.dump(model_package, buffer)
            model_bytes = buffer.getvalue()
            
            # Upload to S3
            s3_key = f'ai-models/{model_id}/model_package.joblib'
            s3.put_object(
                Bucket=S3_BUCKET,
                Key=s3_key,
                Body=model_bytes,
                ContentType='application/octet-stream'
            )
            
            s3_path = f's3://{S3_BUCKET}/{s3_key}'
            logger.info(f"Models saved to S3: {s3_path}")
            
            return s3_path
            
        except Exception as e:
            logger.error(f"Error saving models to S3: {str(e)}")
            raise
    
    def save_model_metadata(self, model_id: str, timestamp: datetime, 
                          crypto_accuracy: float, forex_accuracy: float, s3_path: str):
        """Save model metadata to DynamoDB"""
        try:
            item = {
                'modelId': model_id,
                'timestamp': timestamp.isoformat(),
                'trainingStatus': 'completed',
                'cryptoAccuracy': Decimal(str(round(crypto_accuracy, 4))),
                'forexAccuracy': Decimal(str(round(forex_accuracy, 4))),
                'overallAccuracy': Decimal(str(round((crypto_accuracy + forex_accuracy) / 2, 4))),
                's3ModelPath': s3_path,
                'createdAt': timestamp.isoformat(),
                'modelType': 'ensemble',
                'features': json.dumps(['price_lag1', 'price_lag2', 'volume_lag1', 'sentiment_score'])
            }
            
            self.ai_models_table.put_item(Item=item)
            logger.info(f"Model metadata saved for model ID: {model_id}")
            
        except Exception as e:
            logger.error(f"Error saving model metadata: {str(e)}")
            raise
    
    def generate_mock_crypto_data(self) -> pd.DataFrame:
        """Generate mock crypto data for testing"""
        symbols = ['BTC', 'ETH', 'ADA', 'SOL']
        data = []
        
        for symbol in symbols:
            base_price = {'BTC': 45000, 'ETH': 3000, 'ADA': 0.5, 'SOL': 100}[symbol]
            
            for i in range(100):
                timestamp = datetime.utcnow() - timedelta(hours=i)
                price = base_price * (1 + np.random.normal(0, 0.02))
                
                data.append({
                    'symbol': symbol,
                    'timestamp': timestamp.isoformat(),
                    'price': str(price),
                    'volume': str(np.random.uniform(1000000, 10000000)),
                    'marketCap': str(price * np.random.uniform(10000000, 100000000))
                })
        
        return pd.DataFrame(data)
    
    def generate_mock_forex_data(self) -> pd.DataFrame:
        """Generate mock forex data for testing"""
        pairs = ['EURUSD', 'GBPUSD', 'USDJPY']
        data = []
        
        for pair in pairs:
            base_rate = {'EURUSD': 1.1, 'GBPUSD': 1.3, 'USDJPY': 140}[pair]
            
            for i in range(100):
                timestamp = datetime.utcnow() - timedelta(hours=i)
                rate = base_rate * (1 + np.random.normal(0, 0.01))
                spread = rate * 0.0002
                
                data.append({
                    'pair': pair,
                    'timestamp': timestamp.isoformat(),
                    'bid': str(rate - spread),
                    'ask': str(rate + spread),
                    'spread': str(spread * 2)
                })
        
        return pd.DataFrame(data)


# Lambda handler function
trainer = TradingAITrainer()

def lambda_handler(event, context):
    """AWS Lambda entry point"""
    return trainer.lambda_handler(event, context)