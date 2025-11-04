"""HTTP Client package for dynamic API interaction.

This package provides two main classes:
- ApiClient: Totally dynamic API client without schema constraints
- SchemaApiClient: API client with schema validation and IntelliSense support
"""

from .api_client import ApiClient
from .enhanced_api_client import EnhancedApiClient, EnhancedApiPath, EnhancedQueryPath
from .exceptions import (
    AuthenticationError,
    HttpClientError,
    RequestTimeoutError,
    ValidationError,
)
from .types import ApiKeyAuth, Auth, BasicAuth, BearerAuth

__version__ = "0.1.0"
__all__ = [
    "ApiClient",
    "ApiKeyAuth",
    "Auth",
    "AuthenticationError",
    "BasicAuth",
    "BearerAuth",
    "EnhancedApiClient",
    "EnhancedApiPath",
    "EnhancedQueryPath",
    "HttpClientError",
    "RequestTimeoutError",
    "ValidationError",
]
