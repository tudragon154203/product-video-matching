import httpx
import base64
from typing import Dict, Any
from common_py.logging_config import configure_logging

logger = configure_logging("dropship-product-finder")

class eBayAuthAPIClient:
    """Client for interacting with the eBay OAuth 2.0 token endpoint."""

    def __init__(self, client_id: str, client_secret: str, token_url: str, scopes: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.scopes = scopes

    async def request_access_token(self) -> Dict[str, Any]:
        """
        Requests a new access token from the eBay OAuth 2.0 token endpoint.
        
        Raises:
            httpx.HTTPStatusError: If the API call returns an unsuccessful HTTP status code.
            httpx.RequestError: If a network-related error occurs.
            Exception: For any other unexpected errors.
        """
        try:
            credentials = f"{self.client_id}:{self.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {encoded_credentials}"
            }

            data = {
                "grant_type": "client_credentials",
                "scope": self.scopes
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.token_url, headers=headers, data=data)
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error("eBay token request failed with HTTP error", 
                        status_code=e.response.status_code, 
                        error_response=e.response.text)
            raise
        except httpx.RequestError as e:
            logger.error("eBay token request failed with network error", error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error during eBay token request", error=str(e))
            raise
