"""
Query utilities and analysis tools for agent traces
Provides easy access to trace data for debugging and monitoring
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio


class TraceAnalyzer:
    """Utilities for analyzing trace data"""
    
    def __init__(self, connection_string: str, database: str = "agent_traces"):
        self.client = AsyncIOMotorClient(connection_string)
        self.db = self.client[database]
        self.traces = self.db['traces']
        self.spans = self.db['spans']
        self.logs = self.db['logs']
    
    # ========================================================================
    # ERROR ANALYSIS
    # ========================================================================
    
    async def get_failed_traces(self, hours: int = 24, limit: int = 50) -> List[Dict]:
        """Get traces that encountered errors"""
        since = datetime.now() - timedelta(hours=hours)
        
        # Find traces with error spans
        error_span_ids = await self.spans.distinct(
            'trace_id',
            {'status': 'error', 'start_time': {'$gte': since}}
        )
        
        traces = await self.traces.find(
            {'trace_id': {'$in': error_span_ids}}
        ).sort('start_time', -1).limit(limit).to_list(length=limit)
        
        # Enrich with error details
        for trace in traces:
            error_spans = await self.spans.find(
                {'trace_id': trace['trace_id'], 'status': 'error'}
            ).to_list(length=None)
            trace['errors'] = [
                {
                    'span_name': s['name'],
                    'error': s['error'],
                    'time': s['start_time']
                }
                for s in error_spans
            ]
        
        return traces
    
    async def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of errors by type"""
        since = datetime.now() - timedelta(hours=hours)
        
        pipeline = [
            {'$match': {'status': 'error', 'start_time': {'$gte': since}}},
            {'$group': {
                '_id': '$name',
                'count': {'$sum': 1},
                'errors': {'$push': '$error'}
            }},
            {'$sort': {'count': -1}}
        ]
        
        error_groups = await self.spans.aggregate(pipeline).to_list(length=None)
        
        return {
            'total_errors': sum(g['count'] for g in error_groups),
            'by_span_type': error_groups
        }
    
    # ========================================================================
    # PERFORMANCE ANALYSIS
    # ========================================================================
    
    async def get_slow_traces(self, threshold_ms: float = 5000, hours: int = 24, 
                             limit: int = 50) -> List[Dict]:
        """Get traces slower than threshold"""
        since = datetime.now() - timedelta(hours=hours)
        
        traces = await self.traces.find({
            'duration_ms': {'$gte': threshold_ms},
            'start_time': {'$gte': since}
        }).sort('duration_ms', -1).limit(limit).to_list(length=limit)
        
        # Add span breakdown
        for trace in traces:
            spans = await self.spans.find(
                {'trace_id': trace['trace_id']}
            ).sort('duration_ms', -1).limit(10).to_list(length=10)
            
            trace['slowest_spans'] = [
                {
                    'name': s['name'],
                    'duration_ms': s['duration_ms'],
                    'type': s['type']
                }
                for s in spans
            ]
        
        return traces
    
    async def get_latency_percentiles(self, hours: int = 24) -> Dict[str, float]:
        """Calculate latency percentiles"""
        since = datetime.now() - timedelta(hours=hours)
        
        pipeline = [
            {'$match': {'start_time': {'$gte': since}}},
            {'$group': {
                '_id': None,
                'durations': {'$push': '$duration_ms'}
            }},
            {'$project': {
                'p50': {'$percentile': {'input': '$durations', 'p': [0.5], 'method': 'approximate'}},
                'p95': {'$percentile': {'input': '$durations', 'p': [0.95], 'method': 'approximate'}},
                'p99': {'$percentile': {'input': '$durations', 'p': [0.99], 'method': 'approximate'}},
                'avg': {'$avg': '$durations'},
                'max': {'$max': '$durations'}
            }}
        ]
        
        result = await self.traces.aggregate(pipeline).to_list(length=1)
        
        if result:
            return {
                'p50': result[0].get('p50', [0])[0],
                'p95': result[0].get('p95', [0])[0],
                'p99': result[0].get('p99', [0])[0],
                'avg': result[0].get('avg', 0),
                'max': result[0].get('max', 0)
            }
        return {}
    
    async def get_span_performance(self, span_type: Optional[str] = None, 
                                   hours: int = 24) -> List[Dict]:
        """Analyze performance by span type"""
        since = datetime.now() - timedelta(hours=hours)
        
        match_stage = {'start_time': {'$gte': since}}
        if span_type:
            match_stage['type'] = span_type
        
        pipeline = [
            {'$match': match_stage},
            {'$group': {
                '_id': {'name': '$name', 'type': '$type'},
                'count': {'$sum': 1},
                'avg_duration': {'$avg': '$duration_ms'},
                'max_duration': {'$max': '$duration_ms'},
                'min_duration': {'$min': '$duration_ms'}
            }},
            {'$sort': {'avg_duration': -1}}
        ]
        
        results = await self.spans.aggregate(pipeline).to_list(length=None)
        
        return [
            {
                'span_name': r['_id']['name'],
                'span_type': r['_id']['type'],
                'count': r['count'],
                'avg_duration_ms': round(r['avg_duration'], 2),
                'max_duration_ms': round(r['max_duration'], 2),
                'min_duration_ms': round(r['min_duration'], 2)
            }
            for r in results
        ]
    
    # ========================================================================
    # USAGE PATTERNS
    # ========================================================================
    
    async def get_request_volume(self, hours: int = 24, 
                                 bucket_minutes: int = 60) -> List[Dict]:
        """Get request volume over time"""
        since = datetime.now() - timedelta(hours=hours)
        
        pipeline = [
            {'$match': {'start_time': {'$gte': since}}},
            {'$group': {
                '_id': {
                    '$dateTrunc': {
                        'date': '$start_time',
                        'unit': 'minute',
                        'binSize': bucket_minutes
                    }
                },
                'count': {'$sum': 1},
                'avg_duration': {'$avg': '$duration_ms'}
            }},
            {'$sort': {'_id': 1}}
        ]
        
        results = await self.traces.aggregate(pipeline).to_list(length=None)
        
        return [
            {
                'timestamp': r['_id'],
                'request_count': r['count'],
                'avg_duration_ms': round(r['avg_duration'], 2)
            }
            for r in results
        ]
    
    async def get_user_activity(self, hours: int = 24, limit: int = 20) -> List[Dict]:
        """Get most active users"""
        since = datetime.now() - timedelta(hours=hours)
        
        pipeline = [
            {'$match': {'start_time': {'$gte': since}, 'user_id': {'$ne': None}}},
            {'$group': {
                '_id': '$user_id',
                'request_count': {'$sum': 1},
                'avg_duration': {'$avg': '$duration_ms'},
                'last_request': {'$max': '$start_time'}
            }},
            {'$sort': {'request_count': -1}},
            {'$limit': limit}
        ]
        
        results = await self.traces.aggregate(pipeline).to_list(length=limit)
        
        return [
            {
                'user_id': r['_id'],
                'request_count': r['request_count'],
                'avg_duration_ms': round(r['avg_duration'], 2),
                'last_request': r['last_request']
            }
            for r in results
        ]
    
    # ========================================================================
    # DETAILED TRACE INSPECTION
    # ========================================================================
    
    async def get_trace_details(self, trace_id: str) -> Dict[str, Any]:
        """Get complete details for a trace"""
        trace = await self.traces.find_one({'trace_id': trace_id})
        if not trace:
            return None
        
        # Get all spans
        spans = await self.spans.find(
            {'trace_id': trace_id}
        ).sort('start_time', 1).to_list(length=None)
        
        # Get all logs
        logs = await self.logs.find(
            {'trace_id': trace_id}
        ).sort('timestamp', 1).to_list(length=None)
        
        # Build span tree
        span_tree = self._build_span_tree(spans)
        
        return {
            'trace': trace,
            'span_tree': span_tree,
            'logs': logs,
            'summary': {
                'total_duration_ms': trace.get('duration_ms', 0),
                'span_count': len(spans),
                'log_count': len(logs),
                'has_errors': any(s['status'] == 'error' for s in spans)
            }
        }
    
    def _build_span_tree(self, spans: List[Dict]) -> List[Dict]:
        """Build hierarchical span tree"""
        span_map = {s['span_id']: s for s in spans}
        root_spans = []
        
        for span in spans:
            span['children'] = []
            parent_id = span.get('parent_id')
            
            if parent_id and parent_id in span_map:
                span_map[parent_id]['children'].append(span)
            else:
                root_spans.append(span)
        
        return root_spans
    
    async def search_traces(self, 
                          query: str,
                          hours: int = 24,
                          limit: int = 50) -> List[Dict]:
        """Search traces by user input or metadata"""
        since = datetime.now() - timedelta(hours=hours)
        
        # Search in metadata.user_input
        traces = await self.traces.find({
            'start_time': {'$gte': since},
            '$or': [
                {'metadata.user_input': {'$regex': query, '$options': 'i'}},
                {'metadata': {'$regex': query, '$options': 'i'}}
            ]
        }).sort('start_time', -1).limit(limit).to_list(length=limit)
        
        return traces
    
    # ========================================================================
    # HEALTH METRICS
    # ========================================================================
    
    async def get_health_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get overall system health metrics"""
        since = datetime.now() - timedelta(hours=hours)
        
        # Total requests
        total_traces = await self.traces.count_documents(
            {'start_time': {'$gte': since}}
        )
        
        # Error rate
        error_traces = await self.traces.count_documents({
            'trace_id': {
                '$in': await self.spans.distinct(
                    'trace_id',
                    {'status': 'error', 'start_time': {'$gte': since}}
                )
            }
        })
        
        # Latency stats
        latency = await self.get_latency_percentiles(hours)
        
        # Request volume
        recent_volume = await self.get_request_volume(hours=1, bucket_minutes=15)
        
        return {
            'period_hours': hours,
            'total_requests': total_traces,
            'error_count': error_traces,
            'error_rate': (error_traces / total_traces * 100) if total_traces > 0 else 0,
            'latency_p95_ms': latency.get('p95', 0),
            'latency_avg_ms': latency.get('avg', 0),
            'recent_volume': recent_volume[-4:] if recent_volume else [],
            'status': 'healthy' if (error_traces / total_traces if total_traces > 0 else 0) < 0.05 else 'degraded'
        }


# ============================================================================
# CLI TOOL FOR QUERYING
# ============================================================================

async def cli_main():
    """Command-line interface for trace analysis"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python trace_queries.py <command> [args]")
        print("\nCommands:")
        print("  health - Show system health summary")
        print("  errors - Show recent errors")
        print("  slow - Show slow traces")
        print("  trace <trace_id> - Show detailed trace")
        print("  search <query> - Search traces")
        return
    
    analyzer = TraceAnalyzer("mongodb://localhost:27017")
    command = sys.argv[1]
    
    if command == "health":
        health = await analyzer.get_health_summary(hours=24)
        print("\n=== System Health (Last 24h) ===")
        print(f"Status: {health['status'].upper()}")
        print(f"Total Requests: {health['total_requests']}")
        print(f"Error Rate: {health['error_rate']:.2f}%")
        print(f"P95 Latency: {health['latency_p95_ms']:.0f}ms")
        print(f"Avg Latency: {health['latency_avg_ms']:.0f}ms")
    
    elif command == "errors":
        errors = await analyzer.get_failed_traces(hours=24, limit=10)
        print("\n=== Recent Errors ===")
        for trace in errors:
            print(f"\nTrace: {trace['trace_id']}")
            print(f"Time: {trace['start_time']}")
            print(f"Duration: {trace['duration_ms']:.0f}ms")
            for error in trace['errors']:
                print(f"  - {error['span_name']}: {error['error']}")
    
    elif command == "slow":
        slow = await analyzer.get_slow_traces(threshold_ms=3000, hours=24, limit=10)
        print("\n=== Slow Traces (>3s) ===")
        for trace in slow:
            print(f"\nTrace: {trace['trace_id']}")
            print(f"Duration: {trace['duration_ms']:.0f}ms")
            print("Slowest spans:")
            for span in trace['slowest_spans'][:5]:
                print(f"  - {span['name']}: {span['duration_ms']:.0f}ms")
    
    elif command == "trace" and len(sys.argv) > 2:
        trace_id = sys.argv[2]
        details = await analyzer.get_trace_details(trace_id)
        if details:
            print(f"\n=== Trace {trace_id} ===")
            print(f"Duration: {details['summary']['total_duration_ms']:.0f}ms")
            print(f"Spans: {details['summary']['span_count']}")
            print(f"Logs: {details['summary']['log_count']}")
            print(f"Status: {'ERROR' if details['summary']['has_errors'] else 'SUCCESS'}")
            print("\nSpan Tree:")
            _print_span_tree(details['span_tree'])
        else:
            print(f"Trace {trace_id} not found")
    
    elif command == "search" and len(sys.argv) > 2:
        query = " ".join(sys.argv[2:])
        results = await analyzer.search_traces(query, hours=24, limit=10)
        print(f"\n=== Search Results for '{query}' ===")
        for trace in results:
            print(f"\nTrace: {trace['trace_id']}")
            print(f"Time: {trace['start_time']}")
            print(f"Input: {trace['metadata'].get('user_input', 'N/A')[:100]}")


def _print_span_tree(spans: List[Dict], indent: int = 0):
    """Pretty print span tree"""
    for span in spans:
        prefix = "  " * indent + "└─ "
        status = "✓" if span['status'] == 'success' else "✗"
        print(f"{prefix}{status} {span['name']} ({span['duration_ms']:.0f}ms)")
        if span.get('children'):
            _print_span_tree(span['children'], indent + 1)


if __name__ == "__main__":
    asyncio.run(cli_main())