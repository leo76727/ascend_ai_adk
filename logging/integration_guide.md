# Agent Tracing Framework - Integration Guide

## Overview

This framework provides comprehensive tracing and logging for Google ADK agents with MongoDB storage, PII scrubbing, and powerful query capabilities.

## Architecture

```
User Request
    ↓
TracedADKAgent (wrapper)
    ↓
Tracer (creates trace context)
    ↓
├─ Spans (captures operations)
├─ Logger (structured logging)
└─ PIIScrubber (removes sensitive data)
    ↓
MongoDB Storage (async writes)
    ↓
TraceAnalyzer (querying & analysis)
```

## Installation

```bash
# Install dependencies
pip install motor pymongo google-genai-sdk

# Or add to requirements.txt:
motor==3.3.2
pymongo==4.6.1
google-genai-sdk==latest
```

## MongoDB Setup

```bash
# Start MongoDB locally
docker run -d -p 27017:27017 --name agent-traces mongo:7

```

## Configuration

Create `config.py`:

```python
import os

class Config:
    # MongoDB
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
    MONGO_DATABASE = os.getenv('MONGO_DATABASE', 'agent_traces')
    
    # Service
    SERVICE_NAME = os.getenv('SERVICE_NAME', 'adk-agent')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')  # DEBUG, INFO, WARNING, ERROR
    
    # PII Scrubbing
    ENABLE_PII_SCRUBBING = os.getenv('ENABLE_PII_SCRUBBING', 'true').lower() == 'true'
    
    # Performance
    MAX_CONCURRENT_WRITES = int(os.getenv('MAX_CONCURRENT_WRITES', '10'))
```

## Integration with Google ADK

### Step 1: Initialize Components

```python
from tracer import Tracer, StructuredLogger, MongoDBStorage, TracedADKAgent
from config import Config

# Initialize once at application startup
tracer = Tracer(service_name=Config.SERVICE_NAME)
logger = StructuredLogger("agent", min_level=Config.LOG_LEVEL)
storage = MongoDBStorage(Config.MONGO_URI, database=Config.MONGO_DATABASE)
```

### Step 2: Wrap Your ADK Agent

```python
import genai
from genai.adk import Agent, Tool

# Define your ADK agent
async def search_tool(query: str) -> str:
    """Search tool implementation"""
    # Your search logic
    return f"Search results for: {query}"

agent = Agent(
    model="gemini-2.0-flash",
    tools=[Tool(search_tool, description="Search the web")],
    system_instruction="You are a helpful assistant"
)

# Wrap with tracing
traced_agent = TracedADKAgent(agent, tracer, storage, logger)
```

### Step 3: Use the Traced Agent

```python
async def handle_user_request(user_input: str, user_id: str):
    """Handle incoming user request with tracing"""
    try:
        response = await traced_agent.run(
            user_input=user_input,
            user_id=user_id
        )
        return response
    except Exception as e:
        print(f"Error: {e}")
        raise
```

## Advanced Usage

### Manual Instrumentation

For custom operations, use the tracer directly:

```python
async def custom_operation():
    # Start trace manually
    trace = tracer.start_trace(user_id="user_123", operation="custom")
    
    try:
        # Create nested spans
        with tracer.start_span("database_query", "database", 
                              query="SELECT * FROM users") as span:
            # Your database operation
            result = await db.query()
            span.set_attribute("rows_returned", len(result))
            span.add_event("query_completed", {"row_count": len(result)})
        
        with tracer.start_span("external_api", "http",
                              endpoint="https://api.example.com") as span:
            # External API call
            response = await api_client.get()
            span.set_attribute("status_code", response.status)
        
    finally:
        # Always end trace
        completed_trace = tracer.end_trace()
        await storage.store_trace(completed_trace)
        await storage.store_spans(completed_trace.trace_id, completed_trace.spans)
```

### Custom Logging

```python
# Log with automatic trace correlation
logger.info("Processing payment", 
           amount=100.50,
           currency="USD",
           payment_method="credit_card")

logger.error("Payment failed",
            error_code="INSUFFICIENT_FUNDS",
            retry_count=3)
```

### Tool Execution Tracking

```python
# The framework automatically tracks ADK tool calls
# But you can add custom instrumentation:

@traced_tool  # Decorator for automatic tracing
async def my_custom_tool(param: str) -> str:
    with tracer.start_span("custom_tool_logic", "tool",
                          param=param) as span:
        # Tool logic
        result = await process(param)
        span.set_attribute("result_length", len(result))
        return result
```

## Querying Traces

### Using the CLI

```bash
# System health
python trace_queries.py health

# Recent errors
python trace_queries.py errors

# Slow traces
python trace_queries.py slow

# Specific trace
python trace_queries.py trace abc-123-def

# Search traces
python trace_queries.py search "weather in NYC"
```

### Programmatic Queries

```python
from trace_queries import TraceAnalyzer

analyzer = TraceAnalyzer(Config.MONGO_URI, Config.MONGO_DATABASE)

# Get health metrics
health = await analyzer.get_health_summary(hours=24)
print(f"Error rate: {health['error_rate']:.2f}%")

# Find slow operations
slow_traces = await analyzer.get_slow_traces(threshold_ms=5000, hours=24)

# Error analysis
error_summary = await analyzer.get_error_summary(hours=24)

# Performance by span type
perf = await analyzer.get_span_performance(span_type="tool_execution")

# User activity
users = await analyzer.get_user_activity(hours=24, limit=10)

# Search
results = await analyzer.search_traces("error in payment", hours=168)
```

## MongoDB Queries

### Direct MongoDB Queries

```javascript
// Find all traces with errors in the last 24 hours
db.traces.find({
  "trace_id": {
    "$in": db.spans.distinct("trace_id", {
      "status": "error",
      "start_time": { "$gte": new Date(Date.now() - 24*60*60*1000) }
    })
  }
}).sort({ "start_time": -1 })

// Average latency by hour
db.traces.aggregate([
  {
    "$match": {
      "start_time": { "$gte": new Date(Date.now() - 24*60*60*1000) }
    }
  },
  {
    "$group": {
      "_id": {
        "$dateToString": {
          "format": "%Y-%m-%d %H:00",
          "date": "$start_time"
        }
      },
      "avg_duration": { "$avg": "$duration_ms" },
      "count": { "$sum": 1 }
    }
  },
  { "$sort": { "_id": 1 } }
])

// Most common errors
db.spans.aggregate([
  {
    "$match": {
      "status": "error",
      "start_time": { "$gte": new Date(Date.now() - 24*60*60*1000) }
    }
  },
  {
    "$group": {
      "_id": "$error",
      "count": { "$sum": 1 },
      "spans": { "$push": "$name" }
    }
  },
  { "$sort": { "count": -1 } }
])
```

## Monitoring & Alerts

### Setup Alerts

```python
async def check_error_rate():
    """Alert if error rate exceeds threshold"""
    health = await analyzer.get_health_summary(hours=1)
    
    if health['error_rate'] > 5.0:  # 5% threshold
        # Send alert (email, Slack, PagerDuty, etc.)
        await send_alert(
            title="High Error Rate",
            message=f"Error rate is {health['error_rate']:.2f}%",
            severity="warning"
        )

async def check_latency():
    """Alert if p95 latency is too high"""
    latency = await analyzer.get_latency_percentiles(hours=1)
    
    if latency['p95'] > 10000:  # 10 seconds
        await send_alert(
            title="High Latency",
            message=f"P95 latency is {latency['p95']:.0f}ms",
            severity="critical"
        )

# Run checks periodically
import asyncio

async def monitoring_loop():
    while True:
        await check_error_rate()
        await check_latency()
        await asyncio.sleep(300)  # Check every 5 minutes
```

### Metrics Export

Export metrics to Prometheus, Grafana, or other monitoring tools:

```python
from prometheus_client import Counter, Histogram, start_http_server

# Define metrics
request_counter = Counter('agent_requests_total', 'Total requests')
error_counter = Counter('agent_errors_total', 'Total errors')
latency_histogram = Histogram('agent_latency_seconds', 'Request latency')

# Update metrics from traces
async def update_metrics():
    health = await analyzer.get_health_summary(hours=1)
    request_counter.inc(health['total_requests'])
    error_counter.inc(health['error_count'])

# Start metrics server
start_http_server(8000)
```

## Best Practices

### 1. Span Naming
- Use descriptive, consistent names: `tool_search`, `llm_call`, `db_query`
- Include operation type in span name
- Keep names under 50 characters

### 2. Attribute Usage
- Add context that helps debugging: input parameters, result size
- Don't log full payloads in attributes (use truncation)
- Use consistent attribute names across spans

### 3. Error Handling
- Always capture exceptions in spans
- Include error context (stack trace, input state)
- Mark spans with error status

### 4. Performance
- Batch MongoDB writes when possible
- Use async operations to avoid blocking
- Set TTL on old traces (auto-deletion)

### 5. PII Protection
- Review PII patterns regularly
- Test scrubbing with real data
- Never log credit card numbers, SSNs, passwords

## Production Deployment

### Environment Variables

```bash
export MONGO_URI="mongodb+srv://user:pass@cluster.mongodb.net"
export MONGO_DATABASE="agent_traces_prod"
export SERVICE_NAME="production-agent"
export LOG_LEVEL="WARNING"
export ENABLE_PII_SCRUBBING="true"
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY tracer.py trace_queries.py config.py ./
COPY your_agent.py .

CMD ["python", "your_agent.py"]
```

### MongoDB Indexes

```python
# Run once to ensure indexes exist
async def setup_indexes():
    await storage.traces.create_index([("start_time", -1)])
    await storage.traces.create_index([("user_id", 1), ("start_time", -1)])
    await storage.traces.create_index([("metadata.user_input", "text")])
    
    await storage.spans.create_index([("trace_id", 1), ("start_time", 1)])
    await storage.spans.create_index([("status", 1), ("start_time", -1)])
    
    await storage.logs.create_index([("trace_id", 1), ("timestamp", 1)])
    await storage.logs.create_index([("level", 1), ("timestamp", -1)])
    
    # TTL index - auto-delete traces older than 30 days
    await storage.traces.create_index(
        [("start_time", 1)],
        expireAfterSeconds=30*24*60*60
    )
```

### Scaling Considerations

- **100 requests/day** = ~4 requests/hour = Very low load
- **10 concurrent requests** = Peak capacity
- MongoDB can easily handle this scale on smallest instance
- Consider MongoDB Atlas M0 (free tier) or M2 ($9/month)
- No special scaling needed for this volume

## Troubleshooting

### Issue: Traces not appearing in MongoDB

```python
# Check connection
try:
    await storage.client.admin.command('ping')
    print("MongoDB connected!")
except Exception as e:
    print(f"MongoDB connection failed: {e}")

# Check if data is being written
trace = tracer.start_trace()
tracer.end_trace()
await storage.store_trace(trace)
```

### Issue: High latency from tracing

- Ensure MongoDB writes are async
- Batch span writes
- Check network latency to MongoDB
- Consider using local MongoDB for development

### Issue: PII not being scrubbed

```python
# Test scrubbing
from tracer import PIIScrubber

test_data = "Contact me at john@example.com or 555-123-4567"
scrubbed = PIIScrubber.scrub(test_data)
print(scrubbed)  # Should show [REDACTED_EMAIL] and [REDACTED_PHONE]

# Add custom patterns
PIIScrubber.PATTERNS['custom'] = r'your-pattern-here'
```

## Next Steps

1. **Set up monitoring dashboard** - Use MongoDB Charts or Grafana
2. **Create alerts** - For error rates and latency spikes
3. **Add custom spans** - Instrument business-critical operations
4. **Review traces weekly** - Identify optimization opportunities
5. **Tune PII scrubbing** - Add domain-specific patterns

## Support

For issues or questions:
- Review MongoDB logs: `db.traces.find().limit(5)`
- Check agent logs for errors
- Verify trace_id propagation through spans
- Test with simple requests first