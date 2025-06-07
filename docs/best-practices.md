# Best Practices Guide

This guide covers production-ready patterns, performance optimization, security considerations, and code quality standards for FastMCP servers.

## Code Organization

### Project Structure

```
src/
├── server.py              # Main server entry point
├── config/
│   ├── __init__.py
│   ├── settings.py        # Configuration management
│   └── logging.py         # Logging configuration
├── tools/
│   ├── __init__.py
│   ├── base.py           # Base tool classes
│   ├── data_tools.py     # Data manipulation tools
│   ├── api_tools.py      # External API tools
│   └── admin_tools.py    # Administrative tools
├── resources/
│   ├── __init__.py
│   ├── static.py         # Static resources
│   └── dynamic.py        # Dynamic resources
├── models/
│   ├── __init__.py
│   ├── requests.py       # Request models
│   └── responses.py      # Response models
├── utils/
│   ├── __init__.py
│   ├── auth.py          # Authentication utilities
│   ├── cache.py         # Caching utilities
│   └── validation.py    # Validation helpers
└── exceptions/
    ├── __init__.py
    └── custom.py        # Custom exceptions
```

### Configuration Management

```python
# src/config/settings.py
import os
from functools import lru_cache
from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    """Application settings."""
    
    # Server Configuration
    app_name: str = Field(default="FastMCP Server", env="APP_NAME")
    version: str = Field(default="1.0.0", env="VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Transport Configuration
    port: int = Field(default=8000, env="PORT")
    host: str = Field(default="0.0.0.0", env="HOST")
    
    # Database Configuration
    database_url: str = Field(default="sqlite:///app.db", env="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # External APIs
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    external_api_key: str = Field(default="", env="EXTERNAL_API_KEY")
    
    # Authentication
    oauth_client_id: str = Field(default="", env="OAUTH_CLIENT_ID")
    oauth_client_secret: str = Field(default="", env="OAUTH_CLIENT_SECRET")
    jwt_secret_key: str = Field(default="dev-secret", env="JWT_SECRET_KEY")
    
    # Performance
    max_concurrent_requests: int = Field(default=100, env="MAX_CONCURRENT_REQUESTS")
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

# Usage in your server
settings = get_settings()
```

## Error Handling

### Structured Error Handling

```python
# src/exceptions/custom.py
from fastmcp.exceptions import ToolError

class ValidationError(ToolError):
    """Raised when input validation fails."""
    pass

class ExternalAPIError(ToolError):
    """Raised when external API calls fail."""
    pass

class AuthenticationError(ToolError):
    """Raised when authentication fails."""
    pass

class RateLimitError(ToolError):
    """Raised when rate limits are exceeded."""
    pass

# src/utils/error_handler.py
import logging
from typing import Any, Dict
from fastmcp.exceptions import ToolError

logger = logging.getLogger(__name__)

def handle_external_api_error(e: Exception, context: str = "") -> ToolError:
    """Convert external API errors to ToolError."""
    logger.error(f"External API error in {context}: {str(e)}")
    
    if "timeout" in str(e).lower():
        return ExternalAPIError(f"Request timeout: {context}")
    elif "401" in str(e) or "unauthorized" in str(e).lower():
        return ExternalAPIError(f"Authentication failed: {context}")
    elif "429" in str(e) or "rate limit" in str(e).lower():
        return RateLimitError(f"Rate limit exceeded: {context}")
    else:
        return ExternalAPIError(f"External service unavailable: {context}")

def safe_tool_execution(func):
    """Decorator for safe tool execution."""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ToolError:
            # Re-raise ToolErrors (they're safe to show to clients)
            raise
        except Exception as e:
            # Log the actual error for debugging
            logger.exception(f"Unexpected error in {func.__name__}")
            # Return generic error to client
            raise ToolError(f"Internal error in {func.__name__}")
    
    return wrapper
```

### Tool Error Handling Patterns

```python
# src/tools/data_tools.py
from typing import List, Dict, Any
from pydantic import ValidationError
import aiohttp
import asyncio

from ..exceptions.custom import ValidationError as CustomValidationError, ExternalAPIError
from ..utils.error_handler import handle_external_api_error, safe_tool_execution

@mcp.tool()
@safe_tool_execution
async def process_data(data: List[Dict[str, Any]], operation: str) -> Dict[str, Any]:
    """Process data with comprehensive error handling."""
    
    # Input validation
    if not data:
        raise CustomValidationError("Data list cannot be empty")
    
    if operation not in ["sum", "average", "count"]:
        raise CustomValidationError("Operation must be one of: sum, average, count")
    
    try:
        # Process data
        if operation == "sum":
            result = sum(item.get("value", 0) for item in data)
        elif operation == "average" and data:
            result = sum(item.get("value", 0) for item in data) / len(data)
        elif operation == "count":
            result = len(data)
        else:
            raise CustomValidationError(f"Cannot perform {operation} on empty data")
        
        return {
            "operation": operation,
            "result": result,
            "count": len(data)
        }
    
    except TypeError as e:
        raise CustomValidationError(f"Invalid data format: {str(e)}")
    except ZeroDivisionError:
        raise CustomValidationError("Cannot calculate average of empty dataset")

@mcp.tool()
@safe_tool_execution  
async def fetch_external_data(url: str, timeout: int = 30) -> Dict[str, Any]:
    """Fetch data from external API with proper error handling."""
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.json()
    
    except asyncio.TimeoutError:
        raise ExternalAPIError(f"Request to {url} timed out after {timeout}s")
    except aiohttp.ClientResponseError as e:
        raise handle_external_api_error(e, f"fetching {url}")
    except aiohttp.ClientError as e:
        raise handle_external_api_error(e, f"connecting to {url}")
    except Exception as e:
        raise handle_external_api_error(e, f"processing response from {url}")
```

## Input Validation and Data Models

### Comprehensive Pydantic Models

```python
# src/models/requests.py
from pydantic import BaseModel, Field, validator, root_validator
from typing import List, Optional, Union, Literal
from datetime import datetime
from enum import Enum

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class TaskRequest(BaseModel):
    """Request model for task creation."""
    
    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    description: Optional[str] = Field(None, max_length=1000, description="Task description")
    priority: Priority = Field(default=Priority.MEDIUM, description="Task priority")
    due_date: Optional[datetime] = Field(None, description="Task due date")
    tags: List[str] = Field(default_factory=list, max_items=10, description="Task tags")
    assignee: Optional[str] = Field(None, regex=r'^[a-zA-Z0-9_]+$', description="Username")
    
    @validator('due_date')
    def due_date_must_be_future(cls, v):
        if v and v <= datetime.now():
            raise ValueError('Due date must be in the future')
        return v
    
    @validator('tags')
    def validate_tags(cls, v):
        if v:
            # Remove duplicates and validate format
            unique_tags = list(set(tag.strip().lower() for tag in v if tag.strip()))
            if len(unique_tags) != len(v):
                raise ValueError('Tags must be unique')
            return unique_tags
        return v

class SearchRequest(BaseModel):
    """Request model for search operations."""
    
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    filters: Optional[Dict[str, Union[str, int, bool]]] = Field(default_factory=dict)
    limit: int = Field(default=10, ge=1, le=100, description="Number of results")
    offset: int = Field(default=0, ge=0, description="Results offset")
    sort_by: Optional[str] = Field(None, description="Sort field")
    sort_order: Literal["asc", "desc"] = Field(default="asc", description="Sort order")
    
    @root_validator
    def validate_search_params(cls, values):
        sort_by = values.get('sort_by')
        if sort_by and sort_by not in ['created_at', 'updated_at', 'title', 'priority']:
            raise ValueError('Invalid sort_by field')
        return values

# Usage in tools
@mcp.tool()
async def create_task(request: TaskRequest) -> Dict[str, Any]:
    """Create a task with validated input."""
    # The request is automatically validated by Pydantic
    return {
        "task_id": generate_task_id(),
        "title": request.title,
        "description": request.description,
        "priority": request.priority.value,
        "status": "created"
    }
```

### Advanced Validation Patterns

```python
# src/utils/validation.py
from typing import Any, Dict, List
from pydantic import BaseModel, validator
import re

class EmailValidator(BaseModel):
    """Email validation helper."""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

class URLValidator(BaseModel):
    """URL validation helper."""
    
    @staticmethod
    def validate_url(url: str) -> bool:
        pattern = r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)?$'
        return bool(re.match(pattern, url))

class BusinessRuleValidator:
    """Custom business rule validations."""
    
    @staticmethod
    def validate_user_permissions(user_id: str, required_permissions: List[str]) -> bool:
        """Validate user has required permissions."""
        # Implementation depends on your auth system
        user_permissions = get_user_permissions(user_id)
        return all(perm in user_permissions for perm in required_permissions)
    
    @staticmethod
    def validate_data_consistency(data: Dict[str, Any]) -> List[str]:
        """Validate data consistency rules."""
        errors = []
        
        # Example: Check date ranges
        if data.get('start_date') and data.get('end_date'):
            if data['start_date'] >= data['end_date']:
                errors.append("Start date must be before end date")
        
        # Example: Check numeric ranges
        if data.get('min_value') and data.get('max_value'):
            if data['min_value'] >= data['max_value']:
                errors.append("Min value must be less than max value")
        
        return errors

# Usage in tools
@mcp.tool()
async def validated_tool(email: str, url: str, ctx: Context) -> Dict[str, Any]:
    """Tool with comprehensive validation."""
    
    # Validate email
    if not EmailValidator.validate_email(email):
        raise ValidationError("Invalid email format")
    
    # Validate URL
    if not URLValidator.validate_url(url):
        raise ValidationError("Invalid URL format")
    
    # Validate business rules
    if not BusinessRuleValidator.validate_user_permissions(ctx.client_id, ["read_data"]):
        raise AuthenticationError("Insufficient permissions")
    
    return {"email": email, "url": url, "status": "validated"}
```

## Performance Optimization

### Async Patterns and Concurrency

```python
# src/utils/concurrency.py
import asyncio
from typing import List, Dict, Any, Callable, Awaitable
import aiohttp
from contextlib import asynccontextmanager

class ConcurrencyManager:
    """Manage concurrent operations with limits."""
    
    def __init__(self, max_concurrent: int = 10):
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def run_with_limit(self, coro: Awaitable) -> Any:
        """Run coroutine with concurrency limit."""
        async with self.semaphore:
            return await coro

# Global concurrency manager
concurrency = ConcurrencyManager(max_concurrent=50)

@mcp.tool()
async def batch_fetch_data(urls: List[str]) -> List[Dict[str, Any]]:
    """Fetch data from multiple URLs concurrently."""
    
    async def fetch_single(session: aiohttp.ClientSession, url: str) -> Dict[str, Any]:
        """Fetch data from a single URL."""
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                return {"url": url, "data": data, "status": "success"}
        except Exception as e:
            return {"url": url, "error": str(e), "status": "error"}
    
    async with aiohttp.ClientSession() as session:
        # Limit concurrent requests
        tasks = [
            concurrency.run_with_limit(fetch_single(session, url))
            for url in urls
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return results

@mcp.tool()
async def parallel_processing(data_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Process multiple data items in parallel."""
    
    async def process_item(item: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single data item."""
        # Simulate processing time
        await asyncio.sleep(0.1)
        
        processed_value = item.get("value", 0) * 2
        return {
            "id": item.get("id"),
            "original_value": item.get("value"),
            "processed_value": processed_value
        }
    
    # Process items concurrently with limit
    tasks = [
        concurrency.run_with_limit(process_item(item))
        for item in data_items
    ]
    
    processed_items = await asyncio.gather(*tasks)
    
    return {
        "total_items": len(data_items),
        "processed_items": processed_items,
        "summary": {
            "total_original": sum(item.get("value", 0) for item in data_items),
            "total_processed": sum(item["processed_value"] for item in processed_items)
        }
    }
```

### Caching Strategies

```python
# src/utils/cache.py
import redis.asyncio as redis
import json
import hashlib
from typing import Any, Optional, Union
from datetime import timedelta
import functools

class CacheManager:
    """Centralized cache management."""
    
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
    
    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = json.dumps([args, sorted(kwargs.items())], sort_keys=True)
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"{prefix}:{key_hash}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            value = await self.redis.get(key)
            return json.loads(value) if value else None
        except Exception:
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache."""
        try:
            await self.redis.setex(key, ttl, json.dumps(value))
            return True
        except Exception:
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            await self.redis.delete(key)
            return True
        except Exception:
            return False
    
    def cached(self, prefix: str, ttl: int = 3600):
        """Decorator for caching function results."""
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self._make_key(prefix, *args, **kwargs)
                
                # Try to get from cache
                cached_result = await self.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Execute function and cache result
                result = await func(*args, **kwargs)
                await self.set(cache_key, result, ttl)
                return result
            
            return wrapper
        return decorator

# Global cache manager
cache = CacheManager(get_settings().redis_url)

# Usage in tools
@mcp.tool()
@cache.cached("weather_data", ttl=1800)  # Cache for 30 minutes
async def get_weather_data(city: str, country: str = "US") -> Dict[str, Any]:
    """Get weather data with caching."""
    # This function will only be called if data is not in cache
    async with aiohttp.ClientSession() as session:
        url = f"https://api.weather.com/v1/current?city={city}&country={country}"
        async with session.get(url) as response:
            return await response.json()

@mcp.tool()
async def expensive_calculation(numbers: List[int]) -> Dict[str, Any]:
    """Perform expensive calculation with manual caching."""
    
    # Check cache first
    cache_key = cache._make_key("calculation", numbers)
    cached_result = await cache.get(cache_key)
    
    if cached_result:
        cached_result["from_cache"] = True
        return cached_result
    
    # Perform calculation
    result = {
        "sum": sum(numbers),
        "average": sum(numbers) / len(numbers) if numbers else 0,
        "max": max(numbers) if numbers else None,
        "min": min(numbers) if numbers else None,
        "from_cache": False
    }
    
    # Cache result for 1 hour
    await cache.set(cache_key, result, ttl=3600)
    return result
```

### Database Connection Pooling

```python
# src/utils/database.py
import asyncpg
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncContextManager, Dict, Any, List

class DatabaseManager:
    """Database connection manager with pooling."""
    
    def __init__(self, database_url: str, min_connections: int = 5, max_connections: int = 20):
        self.database_url = database_url
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.pool = None
    
    async def connect(self):
        """Initialize connection pool."""
        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=self.min_connections,
            max_size=self.max_connections
        )
    
    async def disconnect(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncContextManager[asyncpg.Connection]:
        """Get database connection from pool."""
        async with self.pool.acquire() as connection:
            yield connection
    
    async def execute_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute query and return results."""
        async with self.get_connection() as conn:
            results = await conn.fetch(query, *args)
            return [dict(row) for row in results]
    
    async def execute_single(self, query: str, *args) -> Dict[str, Any]:
        """Execute query and return single result."""
        async with self.get_connection() as conn:
            result = await conn.fetchrow(query, *args)
            return dict(result) if result else {}

# Global database manager
db = DatabaseManager(get_settings().database_url)

# Usage in tools
@mcp.tool()
async def get_user_profile(user_id: str) -> Dict[str, Any]:
    """Get user profile from database."""
    
    query = """
        SELECT id, username, email, created_at, last_login
        FROM users 
        WHERE id = $1 AND active = true
    """
    
    user = await db.execute_single(query, user_id)
    
    if not user:
        raise ValidationError(f"User {user_id} not found")
    
    return {
        "user_id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "member_since": user["created_at"].isoformat(),
        "last_active": user["last_login"].isoformat() if user["last_login"] else None
    }
```

## Security Best Practices

### Input Sanitization

```python
# src/utils/security.py
import re
import html
from typing import Any, Dict
import bleach

class InputSanitizer:
    """Centralized input sanitization."""
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """Sanitize string input."""
        if not isinstance(value, str):
            raise ValueError("Input must be a string")
        
        # Truncate length
        value = value[:max_length]
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # HTML escape
        value = html.escape(value)
        
        return value.strip()
    
    @staticmethod
    def sanitize_html(value: str, allowed_tags: List[str] = None) -> str:
        """Sanitize HTML content."""
        if allowed_tags is None:
            allowed_tags = ['p', 'br', 'strong', 'em', 'ul', 'ol', 'li']
        
        return bleach.clean(value, tags=allowed_tags, strip=True)
    
    @staticmethod
    def validate_sql_injection(value: str) -> bool:
        """Check for potential SQL injection patterns."""
        dangerous_patterns = [
            r"(\bUNION\b.*\bSELECT\b)",
            r"(\bDROP\b.*\bTABLE\b)",
            r"(\bINSERT\b.*\bINTO\b)",
            r"(\bDELETE\b.*\bFROM\b)",
            r"(\bUPDATE\b.*\bSET\b)",
            r"('.*OR.*'.*')",
            r"(\bEXEC\b|\bEXECUTE\b)",
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return False
        
        return True
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe storage."""
        # Remove dangerous characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        
        # Remove leading/trailing dots and spaces
        filename = filename.strip(' .')
        
        # Limit length
        filename = filename[:255]
        
        return filename or "unnamed_file"

# Usage in tools
@mcp.tool()
async def create_document(title: str, content: str, filename: str) -> Dict[str, Any]:
    """Create document with sanitized input."""
    
    # Sanitize inputs
    safe_title = InputSanitizer.sanitize_string(title, max_length=200)
    safe_content = InputSanitizer.sanitize_html(content)
    safe_filename = InputSanitizer.sanitize_filename(filename)
    
    # Additional validation
    if not InputSanitizer.validate_sql_injection(safe_title):
        raise ValidationError("Invalid characters in title")
    
    # Create document
    document_id = await create_document_in_db(safe_title, safe_content, safe_filename)
    
    return {
        "document_id": document_id,
        "title": safe_title,
        "filename": safe_filename,
        "status": "created"
    }
```

### Rate Limiting

```python
# src/utils/rate_limit.py
import time
from collections import defaultdict, deque
from typing import Dict, Optional
import asyncio

class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.buckets: Dict[str, deque] = defaultdict(deque)
        self.lock = asyncio.Lock()
    
    async def is_allowed(self, key: str) -> bool:
        """Check if request is allowed for the given key."""
        async with self.lock:
            now = time.time()
            bucket = self.buckets[key]
            
            # Remove old requests outside the window
            while bucket and bucket[0] <= now - self.window_seconds:
                bucket.popleft()
            
            # Check if under limit
            if len(bucket) >= self.max_requests:
                return False
            
            # Add current request
            bucket.append(now)
            return True
    
    async def get_remaining(self, key: str) -> int:
        """Get remaining requests for the key."""
        async with self.lock:
            now = time.time()
            bucket = self.buckets[key]
            
            # Remove old requests
            while bucket and bucket[0] <= now - self.window_seconds:
                bucket.popleft()
            
            return max(0, self.max_requests - len(bucket))

# Global rate limiters
general_limiter = RateLimiter(max_requests=1000, window_seconds=3600)  # 1000/hour
expensive_limiter = RateLimiter(max_requests=10, window_seconds=60)    # 10/minute

# Rate limiting decorator
def rate_limit(limiter: RateLimiter, key_func: Optional[callable] = None):
    """Rate limiting decorator."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract context if available
            ctx = kwargs.get('ctx') or (args[-1] if args and hasattr(args[-1], 'client_id') else None)
            
            if ctx and ctx.client_id:
                rate_key = key_func(ctx) if key_func else ctx.client_id
                
                if not await limiter.is_allowed(rate_key):
                    remaining = await limiter.get_remaining(rate_key)
                    raise RateLimitError(f"Rate limit exceeded. {remaining} requests remaining.")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Usage in tools
@mcp.tool()
@rate_limit(general_limiter)
async def regular_tool(data: str, ctx: Context) -> Dict[str, Any]:
    """Regular tool with standard rate limiting."""
    return {"processed": data, "user": ctx.client_id}

@mcp.tool()
@rate_limit(expensive_limiter, key_func=lambda ctx: f"expensive:{ctx.client_id}")
async def expensive_tool(complex_data: List[Dict], ctx: Context) -> Dict[str, Any]:
    """Expensive tool with stricter rate limiting."""
    # Simulate expensive operation
    await asyncio.sleep(2)
    return {"processed_count": len(complex_data)}
```

## Logging and Monitoring

### Structured Logging

```python
# src/config/logging.py
import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict

class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ["name", "msg", "args", "levelname", "levelno", 
                          "pathname", "filename", "module", "lineno", 
                          "funcName", "created", "msecs", "relativeCreated", 
                          "thread", "threadName", "processName", "process",
                          "getMessage", "exc_info", "exc_text", "stack_info"]:
                log_obj[key] = value
        
        return json.dumps(log_obj)

def setup_logging(level: str = "INFO", structured: bool = True):
    """Setup application logging."""
    
    # Clear existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    
    if structured:
        handler.setFormatter(StructuredFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )
    
    # Configure root logger
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

# Usage in tools
logger = logging.getLogger(__name__)

@mcp.tool()
async def monitored_tool(operation: str, data: Dict[str, Any], ctx: Context) -> Dict[str, Any]:
    """Tool with comprehensive monitoring."""
    
    start_time = time.time()
    
    logger.info(
        "Tool execution started",
        extra={
            "tool_name": "monitored_tool",
            "user_id": ctx.client_id,
            "operation": operation,
            "data_size": len(str(data))
        }
    )
    
    try:
        # Simulate processing
        result = {"operation": operation, "status": "completed"}
        
        logger.info(
            "Tool execution completed",
            extra={
                "tool_name": "monitored_tool",
                "user_id": ctx.client_id,
                "operation": operation,
                "execution_time": time.time() - start_time,
                "success": True
            }
        )
        
        return result
    
    except Exception as e:
        logger.error(
            "Tool execution failed",
            extra={
                "tool_name": "monitored_tool",
                "user_id": ctx.client_id,
                "operation": operation,
                "execution_time": time.time() - start_time,
                "error": str(e),
                "success": False
            },
            exc_info=True
        )
        raise
```

## Testing Best Practices

### Test Organization

```python
# tests/conftest.py
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from fastmcp import FastMCP, Client

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def test_server():
    """Create test server with common tools."""
    server = FastMCP("Test Server")
    
    @server.tool()
    async def test_tool(message: str) -> str:
        return f"Test: {message}"
    
    return server

@pytest.fixture
async def mock_external_api():
    """Mock external API responses."""
    mock = AsyncMock()
    mock.get.return_value.__aenter__.return_value.json.return_value = {
        "status": "success",
        "data": "mocked_response"
    }
    return mock

# Test categories
class TestToolFunctionality:
    """Tests for basic tool functionality."""
    
    async def test_basic_tool_call(self, test_server):
        async with Client(test_server) as client:
            result = await client.call_tool("test_tool", {"message": "hello"})
            assert result[0].text == "Test: hello"
    
    async def test_invalid_parameters(self, test_server):
        async with Client(test_server) as client:
            with pytest.raises(Exception):
                await client.call_tool("test_tool", {"wrong_param": "value"})

class TestErrorHandling:
    """Tests for error handling."""
    
    async def test_tool_error_propagation(self):
        server = FastMCP("Error Test Server")
        
        @server.tool()
        async def failing_tool() -> str:
            raise ValueError("Test error")
        
        async with Client(server) as client:
            with pytest.raises(Exception):
                await client.call_tool("failing_tool", {})

class TestPerformance:
    """Performance and load tests."""
    
    async def test_concurrent_requests(self, test_server):
        async with Client(test_server) as client:
            tasks = [
                client.call_tool("test_tool", {"message": f"msg_{i}"})
                for i in range(10)
            ]
            results = await asyncio.gather(*tasks)
            assert len(results) == 10
```

## Documentation Standards

### Code Documentation

```python
# src/tools/example_tools.py
from typing import List, Dict, Any, Optional
from fastmcp import FastMCP, Context

@mcp.tool()
async def comprehensive_example_tool(
    required_param: str,
    optional_param: Optional[int] = None,
    list_param: List[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Comprehensive example tool demonstrating best practices.
    
    This tool serves as an example of proper documentation, error handling,
    validation, and response formatting for FastMCP tools.
    
    Args:
        required_param: A required string parameter for the operation
        optional_param: An optional integer parameter (default: None)
        list_param: Optional list of strings to process (default: empty list)
        ctx: MCP context for authentication and user information
        
    Returns:
        Dict containing:
            - status: Operation status ("success" or "error")
            - data: Processed data based on input parameters
            - metadata: Additional information about the operation
            
    Raises:
        ValidationError: When input parameters are invalid
        AuthenticationError: When user lacks required permissions
        ExternalAPIError: When external service calls fail
        
    Example:
        >>> await comprehensive_example_tool(
        ...     required_param="test_value",
        ...     optional_param=42,
        ...     list_param=["item1", "item2"]
        ... )
        {
            "status": "success",
            "data": {
                "processed_param": "test_value",
                "calculated_value": 84,
                "processed_items": ["ITEM1", "ITEM2"]
            },
            "metadata": {
                "user_id": "user123",
                "processing_time": 0.023,
                "items_processed": 2
            }
        }
    """
    # Implementation here...
```

## Next Steps

- **Authentication**: Review [authentication.md](authentication.md) for security implementation
- **Deployment**: See [deployment.md](deployment.md) for production deployment
- **Testing**: Check [testing.md](testing.md) for comprehensive testing strategies
- **Troubleshooting**: Common issues and solutions in your production environment