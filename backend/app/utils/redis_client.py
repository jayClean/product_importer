"""Helper function to create Redis clients with SSL support for Upstash and other providers."""

from __future__ import annotations

import ssl
from typing import Any

from redis import Redis


def create_redis_client(url: str, **kwargs: Any) -> Redis:
    """Create a Redis client with proper SSL configuration.

    Handles SSL/TLS connections for services like Upstash Redis that require SSL.
    Uses the simple from_url approach, then configures SSL certificate verification.

    Args:
        url: Redis connection URL (redis:// or rediss://)
        **kwargs: Additional arguments (decode_responses, socket_connect_timeout, etc.)

    Returns:
        Configured Redis client
    """
    # If it's Upstash but uses redis://, convert to rediss://
    if ".upstash.io" in url and url.startswith("redis://"):
        url = url.replace("redis://", "rediss://", 1)

    # Use the simple from_url approach (like the example)
    client = Redis.from_url(url, **kwargs)

    # If using SSL (rediss:// or Upstash), configure certificate verification
    if url.startswith("rediss://") or ".upstash.io" in url:
        # Disable certificate verification for Upstash and similar services
        # Access the connection pool and update SSL settings
        if hasattr(client, "connection_pool") and hasattr(
            client.connection_pool, "connection_kwargs"
        ):
            client.connection_pool.connection_kwargs["ssl_cert_reqs"] = ssl.CERT_NONE

    return client
