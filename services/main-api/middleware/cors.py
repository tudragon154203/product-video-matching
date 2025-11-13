"""
CORS (Cross-Origin Resource Sharing) middleware configuration
for the main-api service. This module handles cross-origin requests
from the frontend application.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def add_cors_middleware(app: FastAPI) -> None:
    """
    Add CORS middleware to the FastAPI application.

    Args:
        app: The FastAPI application instance
    """
    app.add_middleware(
        CORSMiddleware,
        # Allow any localhost port for development and Tailscale clients
        allow_origins=[
            # Localhost development
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "http://127.0.0.1:8080",
        ],
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1):[0-9]+|http(s)?://[a-zA-Z0-9\-]+\.tail[a-zA-Z0-9\-]+\.ts\.net:[0-9]+",
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
