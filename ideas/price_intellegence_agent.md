Excellent choice! Qdrant is a superior vector database for this use case due to its excellent performance, rich filtering capabilities, and production-ready features. Let me redesign the similarity engine with Qdrant.

## Qdrant-Based Similarity Engine Implementation

### 1. Qdrant Schema & Collection Setup

```python
# qdrant_schema.py
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams
from typing import List, Dict, Optional
import uuid
import numpy as np

class QdrantTradeCollection:
    def __init__(self, client: QdrantClient, collection_name: str = "structured_trades"):
        self.client = client
        self.collection_name = collection_name
        
    def create_collection(self, vector_size: int = 256):
        """Create Qdrant collection for structured trades"""
        
        # Delete existing collection if it exists
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass
        
        # Create new collection with optimized configuration
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE  # Cosine similarity for trade embeddings
            ),
            # Optimize for hybrid search with filters
            optimizers_config=models.OptimizersConfigDiff(
                default_segment_number=2,
                max_segment_size=50000,
                memmap_threshold=20000
            ),
            # Configure replication for production
            replication_factor=1,  # Increase for production
        )
        
        # Create payload indexes for fast filtering
        self._create_payload_indexes()
        
    def _create_payload_indexes(self):
        """Create indexes on frequently filtered fields"""
        index_fields = [
            "product_type",
            "underlying_asset", 
            "client_tier",
            "barrier_type",
            "coupon_type",
            "tenor_bucket",
            "notional_bucket",
            "trade_date"
        ]
        
        for field in index_fields:
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name=field,
                field_schema=models.PayloadSchemaType.KEYWORD
            )
        
        # Range index for numerical fields
        range_fields = ["tenor", "notional", "margin", "volatility"]
        for field in range_fields:
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name=field,
                field_schema=models.PayloadSchemaType.INTEGER  # or FLOAT
            )

class TradePayloadBuilder:
    """Build Qdrant payload from trade data"""
    
    @staticmethod
    def build_payload(trade: Dict) -> Dict:
        """Convert trade data to Qdrant payload"""
        
        # Categorical features for filtering
        payload = {
            "trade_id": str(trade['trade_id']),
            "product_type": trade['product_type'],
            "underlying_asset": trade['underlying_asset'],
            "client_id": trade['client_id'],
            "client_tier": trade.get('client_tier', 'STANDARD'),
            "barrier_type": trade.get('barrier_type', 'NONE'),
            "coupon_type": trade.get('coupon_type', 'NONE'),
            "currency": trade.get('currency', 'USD'),
            "dealer_id": trade.get('dealer_id', ''),
            
            # Numerical features for range queries
            "tenor": int(trade['tenor']),
            "notional": float(trade['notional']),
            "margin": float(trade.get('margin', 0)),
            "volatility": float(trade.get('volatility', 0)),
            "strike": float(trade.get('strike', 1.0)),
            "barrier_level": float(trade.get('barrier_level', 1.0)),
            
            # Bucketed features for categorical filtering
            "tenor_bucket": TradePayloadBuilder._get_tenor_bucket(trade['tenor']),
            "notional_bucket": TradePayloadBuilder._get_notional_bucket(trade['notional']),
            "margin_bucket": TradePayloadBuilder._get_margin_bucket(trade.get('margin', 0)),
            
            # Time-based features
            "trade_date": trade['trade_date'].isoformat() if hasattr(trade['trade_date'], 'isoformat') else trade['trade_date'],
            "trade_year": trade['trade_date'].year if hasattr(trade['trade_date'], 'year') else int(trade['trade_date'][:4]),
            "trade_month": trade['trade_date'].month if hasattr(trade['trade_date'], 'month') else int(trade['trade_date'][5:7]),
            
            # Market regime features
            "volatility_regime": TradePayloadBuilder._get_volatility_regime(trade.get('volatility', 0)),
            "rate_environment": TradePayloadBuilder._get_rate_environment(trade.get('risk_free_rate', 0)),
        }
        
        return payload
    
    @staticmethod
    def _get_tenor_bucket(tenor: int) -> str:
        if tenor <= 30: return "SHORT_TERM"
        elif tenor <= 180: return "MEDIUM_TERM"
        elif tenor <= 365: return "LONG_TERM"
        else: return "VERY_LONG_TERM"
    
    @staticmethod
    def _get_notional_bucket(notional: float) -> str:
        if notional <= 1000000: return "SMALL"
        elif notional <= 10000000: return "MEDIUM"
        elif notional <= 50000000: return "LARGE"
        else: return "XLARGE"
    
    @staticmethod
    def _get_margin_bucket(margin: float) -> str:
        if margin <= 0.005: return "TIGHT"
        elif margin <= 0.015: return "AVERAGE"
        else: return "WIDE"
    
    @staticmethod
    def _get_volatility_regime(volatility: float) -> str:
        if volatility <= 0.15: return "LOW_VOL"
        elif volatility <= 0.25: return "MEDIUM_VOL"
        else: return "HIGH_VOL"
    
    @staticmethod
    def _get_rate_environment(rate: float) -> str:
        if rate <= 0.01: return "LOW_RATES"
        elif rate <= 0.05: return "MEDIUM_RATES"
        else: return "HIGH_RATES"
```

### 2. Enhanced Feature Encoder for Qdrant

```python
# qdrant_feature_encoder.py
import numpy as np
from typing import Dict, List
from sklearn.preprocessing import StandardScaler
import hashlib

class QdrantFeatureEncoder:
    def __init__(self, embedding_dim: int = 256):
        self.embedding_dim = embedding_dim
        self.scaler = StandardScaler()
        self._initialize_embeddings()
        
    def _initialize_embeddings(self):
        """Initialize embedding tables for categorical features"""
        self.product_embeddings = {
            'AUTOCALLABLE': self._random_embedding(16),
            'BARRIER_OPTION': self._random_embedding(16),
            'ACCUMULATOR': self._random_embedding(16),
            'DIGITAL_OPTION': self._random_embedding(16),
            'REVERSE_CONVERTIBLE': self._random_embedding(16),
            'RANGE_ACCURAL': self._random_embedding(16),
        }
        
        self.underlying_embeddings = {
            'EQUITY': self._random_embedding(12),
            'INDEX': self._random_embedding(12),
            'FX': self._random_embedding(12),
            'COMMODITY': self._random_embedding(12),
        }
        
        self.client_tier_embeddings = {
            'PLATINUM': self._random_embedding(8),
            'GOLD': self._random_embedding(8),
            'STANDARD': self._random_embedding(8),
        }
    
    def _random_embedding(self, size: int) -> np.ndarray:
        """Generate deterministic random embeddings"""
        return np.random.randn(size).astype(np.float32)
    
    def encode_trade(self, trade: Dict) -> np.ndarray:
        """Encode trade into a high-dimensional vector for Qdrant"""
        features = []
        
        # 1. Product Structure Features (64 dim)
        features.extend(self._encode_product_structure(trade))
        
        # 2. Underlying & Market Features (64 dim)
        features.extend(self._encode_market_characteristics(trade))
        
        # 3. Risk & Pricing Features (64 dim)
        features.extend(self._encode_risk_characteristics(trade))
        
        # 4. Client & Context Features (64 dim)
        features.extend(self._encode_context_features(trade))
        
        # Convert to numpy array and ensure correct dimension
        embedding = np.array(features, dtype=np.float32)
        
        # Pad or truncate to exact dimension
        if len(embedding) < self.embedding_dim:
            padding = np.zeros(self.embedding_dim - len(embedding), dtype=np.float32)
            embedding = np.concatenate([embedding, padding])
        elif len(embedding) > self.embedding_dim:
            embedding = embedding[:self.embedding_dim]
        
        return embedding
    
    def _encode_product_structure(self, trade: Dict) -> List[float]:
        """Encode product structure with rich embeddings"""
        features = []
        
        # Product type embedding
        product_type = trade['product_type']
        features.extend(self.product_embeddings.get(product_type, self._random_embedding(16)))
        
        # Barrier configuration
        barrier_type = trade.get('barrier_type', 'NONE')
        barrier_encoding = {
            'NONE': [0, 0, 0, 0],
            'KNOCK_IN': [1, 0, 0, 0],
            'KNOCK_OUT': [0, 1, 0, 0],
            'AUTOCALL': [0, 0, 1, 0],
            'DOUBLE_BARRIER': [0, 0, 0, 1]
        }
        features.extend(barrier_encoding.get(barrier_type, [0, 0, 0, 0]))
        
        # Coupon structure
        coupon_type = trade.get('coupon_type', 'NONE')
        coupon_encoding = {
            'NONE': [0, 0, 0],
            'FIXED': [1, 0, 0],
            'FLOATING': [0, 1, 0],
            'DIGITAL': [0, 0, 1]
        }
        features.extend(coupon_encoding.get(coupon_type, [0, 0, 0]))
        
        # Key levels (normalized)
        features.append(float(trade.get('strike', 1.0)))  # Moneyness
        features.append(float(trade.get('barrier_level', 1.0)))
        features.append(float(trade.get('coupon_rate', 0.0)) / 0.1)  # Normalize
        
        # Tenor features
        tenor = trade['tenor']
        features.append(tenor / 365.0)  # Years
        features.append(np.log1p(tenor) / 10.0)  # Log-scaled
        
        return features
    
    def _encode_market_characteristics(self, trade: Dict) -> List[float]:
        """Encode market conditions and underlying characteristics"""
        features = []
        
        # Underlying asset class
        underlying_class = self._classify_underlying(trade['underlying_asset'])
        features.extend(self.underlying_embeddings.get(underlying_class, self._random_embedding(12)))
        
        # Market regime at trade time
        volatility = trade.get('volatility', 0.15)
        features.extend(self._encode_volatility_regime(volatility))
        
        risk_free_rate = trade.get('risk_free_rate', 0.02)
        features.extend(self._encode_rate_environment(risk_free_rate))
        
        # Spot price normalized
        spot_price = trade.get('spot_price', 100.0)
        features.append(np.log(spot_price) / 10.0)
        
        # Market sentiment indicators
        features.append(1.0 if volatility > 0.20 else 0.0)  # High vol flag
        features.append(1.0 if risk_free_rate > 0.05 else 0.0)  # High rates flag
        
        # Currency features
        currency = trade.get('currency', 'USD')
        features.extend(self._encode_currency(currency))
        
        return features
    
    def _encode_risk_characteristics(self, trade: Dict) -> List[float]:
        """Encode risk and pricing characteristics"""
        features = []
        
        # Notional-based features
        notional = trade['notional']
        features.append(np.log10(max(notional, 1000000)) / 9.0)  # Log-scaled
        features.append(notional / 100000000.0)  # Linear scaled to $100M
        
        # Margin and pricing
        margin = trade.get('margin', 0.0)
        features.append(margin / 0.05)  # Normalize to 5% max
        features.append(np.log1p(margin * 1000))  # Log of basis points
        
        # Greeks approximations (if available)
        features.append(self._estimate_delta_sensitivity(trade))
        features.append(self._estimate_vega_sensitivity(trade))
        features.append(self._estimate_gamma_sensitivity(trade))
        
        # Complexity score
        features.append(self._calculate_complexity_score(trade))
        
        return features
    
    def _encode_context_features(self, trade: Dict) -> List[float]:
        """Encode client and temporal context"""
        features = []
        
        # Client context
        client_tier = trade.get('client_tier', 'STANDARD')
        features.extend(self.client_tier_embeddings.get(client_tier, self._random_embedding(8)))
        
        # Volume context
        ytd_volume = trade.get('ytd_volume', 0)
        features.append(np.log1p(ytd_volume) / 20.0)  # Log-scaled
        
        # Temporal features
        trade_date = trade['trade_date']
        if hasattr(trade_date, 'timestamp'):
            timestamp = trade_date.timestamp()
        else:
            # Parse string date
            from datetime import datetime
            timestamp = datetime.fromisoformat(trade_date.replace('Z', '+00:00')).timestamp()
        
        # Recency encoding
        days_ago = (datetime.now().timestamp() - timestamp) / (24 * 3600)
        features.append(np.exp(-days_ago / 90.0))  # 90-day decay
        
        # Seasonal features
        if hasattr(trade_date, 'month'):
            month = trade_date.month
        else:
            month = int(trade_date[5:7])
        
        # Month encoding (sine/cosine for cyclical)
        features.append(np.sin(2 * np.pi * month / 12))
        features.append(np.cos(2 * np.pi * month / 12))
        
        # Quarter encoding
        quarter = (month - 1) // 3
        quarter_encoding = [0, 0, 0, 0]
        quarter_encoding[quarter] = 1
        features.extend(quarter_encoding)
        
        return features
    
    def _encode_volatility_regime(self, volatility: float) -> List[float]:
        """Encode volatility regime with smooth encoding"""
        low_vol = max(0, 1 - abs(volatility - 0.10) / 0.10)  # Centered at 10%
        med_vol = max(0, 1 - abs(volatility - 0.20) / 0.10)  # Centered at 20%
        high_vol = max(0, 1 - abs(volatility - 0.30) / 0.10) # Centered at 30%
        return [low_vol, med_vol, high_vol]
    
    def _encode_rate_environment(self, rate: float) -> List[float]:
        """Encode rate environment"""
        low_rate = max(0, 1 - abs(rate - 0.01) / 0.02)  # Centered at 1%
        med_rate = max(0, 1 - abs(rate - 0.03) / 0.02)  # Centered at 3%
        high_rate = max(0, 1 - abs(rate - 0.05) / 0.02) # Centered at 5%
        return [low_rate, med_rate, high_rate]
    
    def _encode_currency(self, currency: str) -> List[float]:
        """Simple currency encoding"""
        currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CHF']
        encoding = [1.0 if currency == c else 0.0 for c in currencies]
        if currency not in currencies:
            encoding = [0.2] * len(currencies)  # Unknown currency
        return encoding
    
    def _classify_underlying(self, underlying: str) -> str:
        """Classify underlying asset type"""
        if any(index in underlying.upper() for index in ['SPX', 'NDX', 'DJI', 'FTSE', 'DAX']):
            return 'INDEX'
        elif any(fx in underlying.upper() for fx in ['EUR', 'USD', 'JPY', 'GBP', 'CHF']):
            return 'FX'
        elif any(comm in underlying.upper() for comm in ['GOLD', 'SILVER', 'OIL', 'COPPER']):
            return 'COMMODITY'
        else:
            return 'EQUITY'
    
    def _estimate_delta_sensitivity(self, trade: Dict) -> float:
        """Estimate delta sensitivity based on product type"""
        product_type = trade['product_type']
        if 'BARRIER' in product_type:
            return 0.6
        elif 'AUTOCALLABLE' in product_type:
            return 0.4
        else:
            return 0.5
    
    def _estimate_vega_sensitivity(self, trade: Dict) -> float:
        """Estimate vega sensitivity"""
        product_type = trade['product_type']
        if 'OPTION' in product_type:
            return 0.7
        elif 'AUTOCALLABLE' in product_type:
            return 0.5
        else:
            return 0.3
    
    def _estimate_gamma_sensitivity(self, trade: Dict) -> float:
        """Estimate gamma sensitivity"""
        if 'BARRIER' in trade.get('barrier_type', ''):
            return 0.8
        else:
            return 0.3
    
    def _calculate_complexity_score(self, trade: Dict) -> float:
        """Calculate product complexity score"""
        score = 0.0
        if trade.get('barrier_type') not in [None, 'NONE']:
            score += 0.3
        if trade.get('coupon_type') not in [None, 'NONE']:
            score += 0.2
        if 'AUTOCALL' in trade.get('barrier_type', ''):
            score += 0.2
        if trade['tenor'] > 365:
            score += 0.1
        if trade['notional'] > 10000000:
            score += 0.1
        if trade.get('observation_frequency') != 'MATURITY':
            score += 0.1
        return min(score, 1.0)
```

### 3. Qdrant-Powered Similarity Engine

```python
# qdrant_similarity_engine.py
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Filter, FieldCondition, Range, MatchValue
from typing import List, Dict, Optional, Tuple
import numpy as np
from datetime import datetime, timedelta

class QdrantSimilarityEngine:
    def __init__(self, 
                 qdrant_client: QdrantClient,
                 collection_name: str = "structured_trades",
                 feature_encoder: QdrantFeatureEncoder = None):
        
        self.client = qdrant_client
        self.collection_name = collection_name
        self.encoder = feature_encoder or QdrantFeatureEncoder()
        
    def initialize_collection(self):
        """Initialize Qdrant collection"""
        collection_manager = QdrantTradeCollection(self.client, self.collection_name)
        collection_manager.create_collection(vector_size=self.encoder.embedding_dim)
    
    def index_trades(self, trades: List[Dict]):
        """Index historical trades in Qdrant"""
        points = []
        
        for trade in trades:
            # Generate vector embedding
            vector = self.encoder.encode_trade(trade).tolist()
            
            # Build payload
            payload = TradePayloadBuilder.build_payload(trade)
            
            # Create point ID from trade_id
            point_id = self._trade_id_to_point_id(trade['trade_id'])
            
            points.append(models.PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            ))
        
        # Batch upload points
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
        print(f"Indexed {len(trades)} trades in Qdrant")
    
    def find_similar_trades(self, 
                          new_trade: Dict,
                          max_results: int = 50,
                          filters: Optional[Dict] = None,
                          score_threshold: float = 0.7) -> List[Dict]:
        """Find similar trades using Qdrant's powerful search"""
        
        # Generate query vector
        query_vector = self.encoder.encode_trade(new_trade).tolist()
        
        # Build search filters
        search_filter = self._build_search_filters(new_trade, filters)
        
        # Perform search
        search_results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=search_filter,
            limit=max_results * 2,  # Get extra for post-filtering
            score_threshold=score_threshold,
            with_payload=True,
            with_vectors=False
        )
        
        # Convert to trade format and apply business logic filters
        similar_trades = []
        for result in search_results:
            trade = self._point_to_trade(result)
            if trade and self._passes_business_filters(new_trade, trade):
                trade['similarity_score'] = result.score
                similar_trades.append(trade)
        
        return sorted(similar_trades, key=lambda x: x['similarity_score'], reverse=True)[:max_results]
    
    def hybrid_similarity_search(self,
                               new_trade: Dict,
                               natural_language_query: str = None,
                               max_results: int = 50) -> List[Dict]:
        """Advanced hybrid search combining vector and keyword search"""
        
        query_vector = self.encoder.encode_trade(new_trade).tolist()
        
        # Build sophisticated filters
        search_filter = self._build_hybrid_filters(new_trade)
        
        # Qdrant's hybrid search (vector + payload conditions)
        search_results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=search_filter,
            limit=max_results,
            score_threshold=0.6,  # Lower threshold for broader search
            with_payload=True,
            with_vectors=False
        )
        
        # Process results
        similar_trades = []
        for result in search_results:
            trade = self._point_to_trade(result)
            if trade:
                trade['similarity_score'] = result.score
                trade['search_type'] = 'hybrid'
                similar_trades.append(trade)
        
        return similar_trades
    
    def multi_stage_similarity_search(self, new_trade: Dict) -> Dict:
        """Multi-stage search with different strategies"""
        
        results = {}
        
        # Stage 1: Exact structure matches
        exact_filter = Filter(
            must=[
                FieldCondition(key="product_type", match=MatchValue(value=new_trade['product_type'])),
                FieldCondition(key="underlying_asset", match=MatchValue(value=new_trade['underlying_asset'])),
                FieldCondition(key="barrier_type", match=MatchValue(value=new_trade.get('barrier_type', 'NONE'))),
                FieldCondition(key="tenor_bucket", match=MatchValue(value=TradePayloadBuilder._get_tenor_bucket(new_trade['tenor']))),
            ]
        )
        
        results['exact_matches'] = self.find_similar_trades(
            new_trade, max_results=20, filters=exact_filter, score_threshold=0.8
        )
        
        # Stage 2: Same product type, different underlyings
        similar_product_filter = Filter(
            must=[
                FieldCondition(key="product_type", match=MatchValue(value=new_trade['product_type'])),
            ],
            should=[  # Boost similar underlyings
                FieldCondition(key="underlying_asset", match=MatchValue(value=new_trade['underlying_asset'])),
            ]
        )
        
        results['similar_products'] = self.find_similar_trades(
            new_trade, max_results=30, filters=similar_product_filter, score_threshold=0.7
        )
        
        # Stage 3: Broad similarity with recent trades only
        recent_filter = Filter(
            must=[
                FieldCondition(
                    key="trade_date",
                    range=Range(
                        gte=(datetime.now() - timedelta(days=90)).isoformat()
                    )
                )
            ]
        )
        
        results['recent_similar'] = self.find_similar_trades(
            new_trade, max_results=25, filters=recent_filter, score_threshold=0.6
        )
        
        # Combine and deduplicate
        all_trades = []
        seen_ids = set()
        
        for stage in ['exact_matches', 'similar_products', 'recent_similar']:
            for trade in results[stage]:
                if trade['trade_id'] not in seen_ids:
                    trade['search_stage'] = stage
                    all_trades.append(trade)
                    seen_ids.add(trade['trade_id'])
        
        return {
            'similar_trades': sorted(all_trades, key=lambda x: x['similarity_score'], reverse=True),
            'search_breakdown': {k: len(v) for k, v in results.items()}
        }
    
    def _build_search_filters(self, new_trade: Dict, additional_filters: Optional[Dict] = None) -> Optional[Filter]:
        """Build Qdrant filter for similarity search"""
        
        filter_conditions = []
        
        # Basic product matching
        filter_conditions.append(
            FieldCondition(key="product_type", match=MatchValue(value=new_trade['product_type']))
        )
        
        # Same underlying asset (boost relevance)
        filter_conditions.append(
            FieldCondition(key="underlying_asset", match=MatchValue(value=new_trade['underlying_asset']))
        )
        
        # Similar tenor (within 50%)
        tenor = new_trade['tenor']
        filter_conditions.append(
            FieldCondition(
                key="tenor",
                range=Range(
                    gte=int(tenor * 0.5),
                    lte=int(tenor * 1.5)
                )
            )
        )
        
        # Recent trades preferred (last 2 years)
        filter_conditions.append(
            FieldCondition(
                key="trade_date",
                range=Range(
                    gte=(datetime.now() - timedelta(days=730)).isoformat()
                )
            )
        )
        
        # Add any additional filters
        if additional_filters:
            for key, value in additional_filters.items():
                if isinstance(value, (int, float)):
                    filter_conditions.append(
                        FieldCondition(key=key, range=Range(gte=value*0.8, lte=value*1.2))
                    )
                else:
                    filter_conditions.append(
                        FieldCondition(key=key, match=MatchValue(value=value))
                    )
        
        return Filter(must=filter_conditions) if filter_conditions else None
    
    def _build_hybrid_filters(self, new_trade: Dict) -> Filter:
        """Build sophisticated filters for hybrid search"""
        
        must_conditions = [
            FieldCondition(key="product_type", match=MatchValue(value=new_trade['product_type'])),
        ]
        
        should_conditions = [
            # Boost same underlying
            FieldCondition(key="underlying_asset", match=MatchValue(value=new_trade['underlying_asset'])),
            
            # Boost similar client tier
            FieldCondition(key="client_tier", match=MatchValue(value=new_trade.get('client_tier', 'STANDARD'))),
            
            # Boost recent trades
            FieldCondition(
                key="trade_date",
                range=Range(
                    gte=(datetime.now() - timedelta(days=90)).isoformat()
                )
            ),
        ]
        
        return Filter(must=must_conditions, should=should_conditions)
    
    def _passes_business_filters(self, new_trade: Dict, candidate_trade: Dict) -> bool:
        """Apply business logic filters"""
        
        # Exclude the same trade if it exists
        if candidate_trade.get('trade_id') == new_trade.get('trade_id'):
            return False
        
        # Filter by minimum similarity score (already handled by Qdrant)
        
        # Additional business rules
        if candidate_trade.get('status') != 'EXECUTED':
            return False
        
        # Ensure reasonable margin comparison
        new_margin = new_trade.get('margin', 0.02)
        candidate_margin = candidate_trade.get('margin', 0.02)
        if abs(new_margin - candidate_margin) > 0.02:  # 200bps difference
            return False
        
        return True
    
    def _trade_id_to_point_id(self, trade_id: str) -> int:
        """Convert trade ID to Qdrant point ID"""
        return int(hashlib.md5(trade_id.encode()).hexdigest()[:8], 16)
    
    def _point_to_trade(self, point) -> Optional[Dict]:
        """Convert Qdrant point back to trade format"""
        try:
            payload = point.payload
            return {
                'trade_id': payload['trade_id'],
                'product_type': payload['product_type'],
                'underlying_asset': payload['underlying_asset'],
                'client_id': payload['client_id'],
                'tenor': payload['tenor'],
                'notional': payload['notional'],
                'margin': payload.get('margin', 0),
                'trade_date': payload['trade_date'],
                'client_tier': payload.get('client_tier', 'STANDARD'),
                'barrier_type': payload.get('barrier_type'),
                'coupon_type': payload.get('coupon_type'),
                'similarity_score': point.score
            }
        except KeyError as e:
            print(f"Error converting point to trade: {e}")
            return None
```

### 4. Deployment & Configuration

```python
# qdrant_config.py
from qdrant_client import QdrantClient
import os

class QdrantConfig:
    # Qdrant connection settings
    QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')
    QDRANT_API_KEY = os.getenv('QDRANT_API_KEY', None)
    
    # Collection settings
    COLLECTION_NAME = "structured_trades"
    VECTOR_SIZE = 256
    DISTANCE = "Cosine"
    
    # Performance settings
    BATCH_SIZE = 100
    SEARCH_LIMIT = 100
    SIMILARITY_THRESHOLD = 0.7
    
    @classmethod
    def get_client(cls) -> QdrantClient:
        """Get configured Qdrant client"""
        if cls.QDRANT_API_KEY:
            return QdrantClient(
                url=cls.QDRANT_URL,
                api_key=cls.QDRANT_API_KEY,
                timeout=60  # Increased timeout for large operations
            )
        else:
            return QdrantClient(
                url=cls.QDRANT_URL,
                timeout=60
            )

# docker-compose.qdrant.yml
"""
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    environment:
      - QDRANT__SERVICE__HTTP_PORT=6333
      - QDRANT__SERVICE__GRPC_PORT=6334
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped

volumes:
  qdrant_data:
"""

# Initialization script
def initialize_qdrant_engine():
    """Initialize the Qdrant similarity engine"""
    client = QdrantConfig.get_client()
    encoder = QdrantFeatureEncoder()
    engine = QdrantSimilarityEngine(client, QdrantConfig.COLLECTION_NAME, encoder)
    
    # Create collection
    engine.initialize_collection()
    
    # Load and index historical trades
    historical_trades = load_historical_trades()  # Your data loading function
    engine.index_trades(historical_trades)
    
    return engine
```

## Key Advantages of Qdrant for This Use Case

1. **High Performance**: Sub-millisecond search times even with millions of vectors
2. **Rich Filtering**: Complex boolean logic on payload data during search
3. **Hybrid Search**: Combine vector similarity with keyword matching
4. **Production Ready**: Built-in replication, backup, and monitoring
5. **Scalable**: Horizontal scaling for large trade databases
6. **Flexible**: Support for multiple distance metrics and vector types

This implementation provides a robust, high-performance similarity engine that can handle complex structured products similarity search with rich filtering and hybrid search capabilities.