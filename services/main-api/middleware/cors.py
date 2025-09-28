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
        # Allow any localhost port for development
        allow_origin_regex=r"http://localhost:[0-9]+",
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
