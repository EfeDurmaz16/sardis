# Error Handling

The SDK provides structured error handling with specific exception types.

## Exception Hierarchy

```
SardisError (base)
├── APIError (HTTP errors)
│   ├── AuthenticationError (401)
│   ├── ForbiddenError (403)
│   ├── NotFoundError (404)
│   ├── ValidationError (422)
│   └── RateLimitError (429)
└── NetworkError (connection issues)
```

## Exception Types

### APIError

Base exception for all API errors.

```python
from sardis_sdk.models.errors import APIError

try:
    result = await client.payments.execute(...)
except APIError as e:
    print(f"Status: {e.status_code}")
    print(f"Message: {e.message}")
    print(f"Details: {e.details}")
```

### AuthenticationError

Raised when API key is invalid or missing.

```python
from sardis_sdk.models.errors import AuthenticationError

try:
    client = SardisClient(api_key="invalid_key")
    await client.payments.execute(...)
except AuthenticationError:
    print("Invalid or missing API key")
```

### RateLimitError

Raised when rate limit is exceeded.

```python
from sardis_sdk.models.errors import RateLimitError
import asyncio

try:
    result = await client.payments.execute(...)
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
    await asyncio.sleep(e.retry_after)
    # Retry request
```

### ValidationError

Raised when request parameters are invalid.

```python
from sardis_sdk.models.errors import ValidationError

try:
    result = await client.payments.execute(
        amount=-100,  # Invalid negative amount
    )
except ValidationError as e:
    print(f"Validation failed: {e.message}")
    for error in e.details:
        print(f"  - {error['field']}: {error['message']}")
```

## Automatic Retry

The SDK automatically retries on transient errors:

```python
client = SardisClient(
    api_key="sk_...",
    max_retries=3,      # Retry up to 3 times
    retry_delay=1.0,    # Wait 1 second between retries
)
```

Retried errors:
- 429 Rate Limit (with exponential backoff)
- 500 Internal Server Error
- 502 Bad Gateway
- 503 Service Unavailable
- 504 Gateway Timeout
- Network connection errors

## Best Practices

### Use Specific Exceptions

```python
try:
    result = await client.payments.execute(...)
except AuthenticationError:
    # Re-authenticate
    pass
except RateLimitError as e:
    # Wait and retry
    await asyncio.sleep(e.retry_after)
except ValidationError:
    # Check request parameters
    pass
except APIError:
    # Generic API error handling
    pass
```

### Log Errors

```python
import logging

logger = logging.getLogger(__name__)

try:
    result = await client.payments.execute(...)
except APIError as e:
    logger.error(
        "Payment failed",
        extra={
            "status_code": e.status_code,
            "message": e.message,
            "request_id": e.request_id,
        }
    )
    raise
```

### Handle Network Errors

```python
from sardis_sdk.models.errors import NetworkError

try:
    result = await client.payments.execute(...)
except NetworkError as e:
    print("Network error - check internet connection")
    print(f"Details: {e}")
```

## Error Response Format

All API errors include:

```python
{
    "status_code": 400,
    "message": "Human readable error message",
    "code": "validation_error",
    "request_id": "req_abc123",
    "details": {
        "field": "amount",
        "error": "must be positive"
    }
}
```

