"""
Agent Tracing and Logging Framework for Google ADK
Supports MongoDB storage with PII scrubbing and structured tracing
"""

import uuid
import time
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from contextlib import contextmanager
from functools import wraps
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
import threading

# ============================================================================
# PII SCRUBBING
# ============================================================================

class PIIScrubber:
    """Removes or masks PII from logs"""
    
    # Patterns for common PII
    PATTERNS = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'phone': r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b',
        'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
        'ip_address': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
    }
    
    @classmethod
    def scrub(cls, text: str, mask: str = "[REDACTED]") -> str:
        """Scrub PII from text"""
        if not isinstance(text, str):
            return text
        
        scrubbed = text
        for pattern_name, pattern in cls.PATTERNS.items():
            scrubbed = re.sub(pattern, f"{mask}_{pattern_name.upper()}", scrubbed)
        
        return scrubbed
    
    @classmethod
    def scrub_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively scrub PII from dictionary"""
        scrubbed = {}
        for key, value in data.items():
            if isinstance(value, str):
                scrubbed[key] = cls.scrub(value)
            elif isinstance(value, dict):
                scrubbed[key] = cls.scrub_dict(value)
            elif isinstance(value, list):
                scrubbed[key] = [cls.scrub(v) if isinstance(v, str) else v for v in value]
            else:
                scrubbed[key] = value
        return scrubbed


# ============================================================================
# TRACE CONTEXT
# ============================================================================

class TraceContext:
    """Manages trace context for a single request"""
    
    def __init__(self, trace_id: Optional[str] = None, user_id: Optional[str] = None):
        self.trace_id = trace_id or str(uuid.uuid4())
        self.user_id = user_id
        self.start_time = time.time()
        self.spans: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}
        self.current_span: Optional[str] = None
    
    def add_metadata(self, key: str, value: Any):
        """Add metadata to trace"""
        self.metadata[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MongoDB document"""
        return {
            'trace_id': self.trace_id,
            'user_id': self.user_id,
            'start_time': datetime.fromtimestamp(self.start_time),
            'end_time': datetime.now(),
            'duration_ms': (time.time() - self.start_time) * 1000,
            'metadata': self.metadata,
            'span_count': len(self.spans)
        }


# Thread-local storage for trace context
_trace_context = threading.local()


def get_trace_context() -> Optional[TraceContext]:
    """Get current trace context"""
    return getattr(_trace_context, 'current', None)


def set_trace_context(ctx: TraceContext):
    """Set current trace context"""
    _trace_context.current = ctx


def clear_trace_context():
    """Clear current trace context"""
    _trace_context.current = None


# ============================================================================
# TRACER
# ============================================================================

class Span:
    """Represents a single operation/step in agent execution"""
    
    def __init__(self, name: str, span_type: str, parent_id: Optional[str] = None):
        self.span_id = str(uuid.uuid4())
        self.name = name
        self.span_type = span_type  # 'agent_call', 'tool_execution', 'llm_call', etc.
        self.parent_id = parent_id
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.attributes: Dict[str, Any] = {}
        self.events: List[Dict[str, Any]] = []
        self.status: str = 'in_progress'  # 'success', 'error'
        self.error: Optional[str] = None
    
    def set_attribute(self, key: str, value: Any):
        """Add attribute to span"""
        self.attributes[key] = value
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add event to span"""
        self.events.append({
            'name': name,
            'timestamp': datetime.now(),
            'attributes': attributes or {}
        })
    
    def end(self, status: str = 'success', error: Optional[str] = None):
        """End the span"""
        self.end_time = time.time()
        self.status = status
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MongoDB document"""
        return {
            'span_id': self.span_id,
            'name': self.name,
            'type': self.span_type,
            'parent_id': self.parent_id,
            'start_time': datetime.fromtimestamp(self.start_time),
            'end_time': datetime.fromtimestamp(self.end_time) if self.end_time else None,
            'duration_ms': (self.end_time - self.start_time) * 1000 if self.end_time else None,
            'attributes': PIIScrubber.scrub_dict(self.attributes),
            'events': self.events,
            'status': self.status,
            'error': self.error
        }


class Tracer:
    """Main tracing interface"""
    
    def __init__(self, service_name: str = "adk-agent"):
        self.service_name = service_name
    
    def start_trace(self, user_id: Optional[str] = None, **metadata) -> TraceContext:
        """Start a new trace"""
        ctx = TraceContext(user_id=user_id)
        ctx.metadata.update(metadata)
        ctx.metadata['service_name'] = self.service_name
        set_trace_context(ctx)
        return ctx
    
    @contextmanager
    def start_span(self, name: str, span_type: str, **attributes):
        """Context manager for creating spans"""
        ctx = get_trace_context()
        if not ctx:
            raise RuntimeError("No active trace context. Call start_trace() first.")
        
        # Create span with parent relationship
        parent_id = ctx.current_span
        span = Span(name, span_type, parent_id)
        
        # Set attributes
        for key, value in attributes.items():
            span.set_attribute(key, value)
        
        # Set as current span
        ctx.current_span = span.span_id
        
        try:
            yield span
            span.end(status='success')
        except Exception as e:
            span.end(status='error', error=str(e))
            raise
        finally:
            # Add to context and restore parent
            ctx.spans.append(span)
            ctx.current_span = parent_id
    
    def end_trace(self) -> TraceContext:
        """End current trace"""
        ctx = get_trace_context()
        if not ctx:
            raise RuntimeError("No active trace context.")
        clear_trace_context()
        return ctx


# ============================================================================
# LOGGER
# ============================================================================

class StructuredLogger:
    """Structured logger with trace correlation"""
    
    LEVELS = {
        'DEBUG': 10,
        'INFO': 20,
        'WARNING': 30,
        'ERROR': 40,
        'CRITICAL': 50
    }
    
    def __init__(self, name: str, min_level: str = 'INFO'):
        self.name = name
        self.min_level = self.LEVELS[min_level]
    
    def _log(self, level: str, message: str, **extra):
        """Internal log method"""
        if self.LEVELS[level] < self.min_level:
            return
        
        ctx = get_trace_context()
        
        log_entry = {
            'timestamp': datetime.now(),
            'level': level,
            'logger_name': self.name,
            'message': PIIScrubber.scrub(message),
            'trace_id': ctx.trace_id if ctx else None,
            'span_id': ctx.current_span if ctx else None,
            **PIIScrubber.scrub_dict(extra)
        }
        
        return log_entry
    
    def debug(self, message: str, **extra) -> Optional[Dict]:
        return self._log('DEBUG', message, **extra)
    
    def info(self, message: str, **extra) -> Optional[Dict]:
        return self._log('INFO', message, **extra)
    
    def warning(self, message: str, **extra) -> Optional[Dict]:
        return self._log('WARNING', message, **extra)
    
    def error(self, message: str, **extra) -> Optional[Dict]:
        return self._log('ERROR', message, **extra)
    
    def critical(self, message: str, **extra) -> Optional[Dict]:
        return self._log('CRITICAL', message, **extra)


# ============================================================================
# MONGODB STORAGE
# ============================================================================

class MongoDBStorage:
    """Handles storage of traces, spans, and logs in MongoDB"""
    
    def __init__(self, connection_string: str, database: str = "agent_traces"):
        self.client = AsyncIOMotorClient(connection_string)
        self.db = self.client[database]
        self.traces = self.db['traces']
        self.spans = self.db['spans']
        self.logs = self.db['logs']
        
        # Create indexes
        asyncio.create_task(self._create_indexes())
    
    async def _create_indexes(self):
        """Create MongoDB indexes for efficient querying"""
        await self.traces.create_index('trace_id', unique=True)
        await self.traces.create_index('start_time')
        await self.traces.create_index('user_id')
        
        await self.spans.create_index('trace_id')
        await self.spans.create_index('span_id', unique=True)
        await self.spans.create_index([('trace_id', 1), ('start_time', 1)])
        
        await self.logs.create_index('trace_id')
        await self.logs.create_index('timestamp')
        await self.logs.create_index('level')
    
    async def store_trace(self, trace: TraceContext):
        """Store completed trace"""
        trace_doc = trace.to_dict()
        await self.traces.insert_one(trace_doc)
    
    async def store_spans(self, trace_id: str, spans: List[Span]):
        """Store spans for a trace"""
        span_docs = []
        for span in spans:
            doc = span.to_dict()
            doc['trace_id'] = trace_id
            span_docs.append(doc)
        
        if span_docs:
            await self.spans.insert_many(span_docs)
    
    async def store_log(self, log_entry: Dict[str, Any]):
        """Store individual log entry"""
        if log_entry:
            await self.logs.insert_one(log_entry)
    
    async def get_trace(self, trace_id: str) -> Optional[Dict]:
        """Retrieve trace by ID"""
        return await self.traces.find_one({'trace_id': trace_id})
    
    async def get_spans(self, trace_id: str) -> List[Dict]:
        """Get all spans for a trace"""
        cursor = self.spans.find({'trace_id': trace_id}).sort('start_time', 1)
        return await cursor.to_list(length=None)
    
    async def get_logs(self, trace_id: str, level: Optional[str] = None) -> List[Dict]:
        """Get logs for a trace"""
        query = {'trace_id': trace_id}
        if level:
            query['level'] = level
        cursor = self.logs.find(query).sort('timestamp', 1)
        return await cursor.to_list(length=None)
    
    async def query_traces(self, 
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None,
                          status: Optional[str] = None,
                          user_id: Optional[str] = None,
                          limit: int = 100) -> List[Dict]:
        """Query traces with filters"""
        query = {}
        
        if start_date or end_date:
            query['start_time'] = {}
            if start_date:
                query['start_time']['$gte'] = start_date
            if end_date:
                query['start_time']['$lte'] = end_date
        
        if user_id:
            query['user_id'] = user_id
        
        cursor = self.traces.find(query).sort('start_time', -1).limit(limit)
        return await cursor.to_list(length=limit)


# ============================================================================
# ADK INTEGRATION
# ============================================================================

class TracedADKAgent:
    """Wrapper for ADK Agent with automatic tracing"""
    
    def __init__(self, adk_agent, tracer: Tracer, storage: MongoDBStorage, logger: StructuredLogger):
        self.agent = adk_agent
        self.tracer = tracer
        self.storage = storage
        self.logger = logger
    
    async def run(self, user_input: str, user_id: Optional[str] = None, **kwargs):
        """Run agent with tracing"""
        # Start trace
        trace = self.tracer.start_trace(
            user_id=user_id,
            user_input=PIIScrubber.scrub(user_input)
        )
        
        try:
            # Main agent execution span
            with self.tracer.start_span('agent_execution', 'agent_call', 
                                       input=user_input[:200]) as span:
                
                # Log request
                log_entry = self.logger.info('Agent request received', 
                                            user_id=user_id,
                                            input_length=len(user_input))
                if log_entry:
                    await self.storage.store_log(log_entry)
                
                # Execute agent (you'll need to adapt this to ADK's API)
                response = await self._execute_agent(user_input, **kwargs)
                
                span.set_attribute('output', str(response)[:200])
                span.set_attribute('success', True)
                
                # Log response
                log_entry = self.logger.info('Agent response generated',
                                            response_length=len(str(response)))
                if log_entry:
                    await self.storage.store_log(log_entry)
                
                return response
                
        except Exception as e:
            # Log error
            log_entry = self.logger.error(f'Agent execution failed: {str(e)}',
                                         exception=str(e))
            if log_entry:
                await self.storage.store_log(log_entry)
            raise
            
        finally:
            # End trace and store
            completed_trace = self.tracer.end_trace()
            await self.storage.store_trace(completed_trace)
            await self.storage.store_spans(completed_trace.trace_id, completed_trace.spans)
    
    async def _execute_agent(self, user_input: str, **kwargs):
        """Execute the ADK agent with instrumentation"""
        # This is where you'd integrate with Google ADK's actual API
        # For example, if ADK has a .run() or .execute() method:
        
        # Track tool calls
        if hasattr(self.agent, 'tools'):
            for tool in self.agent.tools:
                # Wrap tool execution
                original_run = tool.run
                
                async def traced_tool_run(*args, **kwargs):
                    with self.tracer.start_span(f'tool_{tool.name}', 'tool_execution',
                                               tool_name=tool.name,
                                               args=str(args)[:200]) as tool_span:
                        result = await original_run(*args, **kwargs)
                        tool_span.set_attribute('result', str(result)[:200])
                        return result
                
                tool.run = traced_tool_run
        
        # Execute the agent
        response = await self.agent.run(user_input, **kwargs)
        
        return response


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

async def example_usage():
    """Example of how to use the tracing framework"""
    
    # Initialize components
    tracer = Tracer(service_name="my-adk-agent")
    logger = StructuredLogger("agent", min_level="INFO")
    storage = MongoDBStorage("mongodb://localhost:27017", database="agent_traces")
    
    # Initialize your ADK agent (pseudocode)
    # adk_agent = YourADKAgent(...)
    
    # Wrap with tracing
    # traced_agent = TracedADKAgent(adk_agent, tracer, storage, logger)
    
    # Use the agent
    # response = await traced_agent.run(
    #     user_input="What's the weather like?",
    #     user_id="user_123"
    # )
    
    # Query traces later
    recent_traces = await storage.query_traces(limit=10)
    for trace in recent_traces:
        print(f"Trace {trace['trace_id']}: {trace['duration_ms']}ms")
        
        # Get detailed spans
        spans = await storage.get_spans(trace['trace_id'])
        for span in spans:
            print(f"  - {span['name']}: {span['duration_ms']}ms")


if __name__ == "__main__":
    asyncio.run(example_usage())