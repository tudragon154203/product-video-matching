import httpx
import json
from typing import Dict, Any
from fastapi import HTTPException
from common_py.logging_config import configure_logging

logger = configure_logging("main-api:ollama_api_client")


class OllamaAPIClient:
    def __init__(self, ollama_host: str):
        self.ollama_host = ollama_host

    async def generate(self, model: str, prompt: str, timeout_s: int, options: dict = None) -> dict:
        if options is None:
            options = {}

        options["timeout"] = timeout_s * 1000

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.ollama_host}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "options": options
                    },
                    timeout=timeout_s
                )
                response.raise_for_status()
                return response.json()
            except UnicodeEncodeError as e:
                logger.error(
                    "Unicode encoding error in Ollama response", error=str(e))
                try:
                    text = response.text.encode('utf-8').decode('utf-8')
                    data = json.loads(text)
                    return data
                except Exception as inner_e:
                    logger.error("Failed to handle Unicode error",
                                 error=str(inner_e))
                    raise HTTPException(
                        status_code=500, detail=f"Ollama request failed with encoding error: {str(e)}")
            except httpx.RequestError as e:
                logger.error("Ollama request failed", error=str(e))
                raise HTTPException(
                    status_code=500, detail=f"Ollama request failed: {str(e)}")
            except httpx.HTTPStatusError as e:
                logger.error("Ollama request failed",
                             status_code=e.response.status_code, error=e.response.text)
                raise HTTPException(
                    status_code=500, detail=f"Ollama request failed: {e.response.text}")
