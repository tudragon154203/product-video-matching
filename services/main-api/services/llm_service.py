import asyncio
import httpx
from typing import Dict, Any
from fastapi import HTTPException
from common_py.logging_config import configure_logging
from config_loader import config

# Configure logger
logger = configure_logging("main-api")

class LLMService:
    def __init__(self):
        pass

    async def call_ollama(self, model: str, prompt: str, timeout_s: int, options: dict = None) -> dict:
        """Call Ollama API."""
        if options is None:
            options = {}
        
        # Ensure timeout is in options
        options["timeout"] = timeout_s * 1000  # Convert to milliseconds
        
        # Use httpx to call Ollama API directly
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{config.OLLAMA_HOST}/api/generate",
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
                logger.error("Unicode encoding error in Ollama response", error=str(e))
                # Try to decode with error handling
                try:
                    text = response.text.encode('utf-8').decode('utf-8')
                    import json as json_module
                    data = json_module.loads(text)
                    return data
                except Exception as inner_e:
                    logger.error("Failed to handle Unicode error", error=str(inner_e))
                    raise HTTPException(status_code=500, detail=f"Ollama request failed with encoding error: {str(e)}")
            except httpx.RequestError as e:
                logger.error("Ollama request failed", error=str(e))
                raise HTTPException(status_code=500, detail=f"Ollama request failed: {str(e)}")
            except httpx.HTTPStatusError as e:
                logger.error("Ollama request failed", status_code=e.response.status_code, error=e.response.text)
                raise HTTPException(status_code=500, detail=f"Ollama request failed: {e.response.text}")

    async def call_gemini(self, model: str, prompt: str, timeout_s: int, **kwargs) -> dict:
        """Call Gemini API."""
        if not config.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set")
        
        headers = {"x-goog-api-key": f"{config.GEMINI_API_KEY}"}
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
        }
        
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            try:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                # Extract text from Gemini response
                text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                return {"response": text}
            except httpx.RequestError as e:
                logger.error("Gemini request failed", error=str(e))
                raise HTTPException(status_code=500, detail=f"Gemini request failed: {str(e)}")
            except httpx.HTTPStatusError as e:
                logger.error("Gemini request failed", status_code=e.response.status_code, error=e.response.text)
                raise HTTPException(status_code=500, detail=f"Gemini request failed: {e.response.text}")

    async def call_llm(self, kind: str, prompt: str, **kwargs) -> dict:
        """Call LLM with fallback from Ollama to Gemini."""
        timeout_s = config.LLM_TIMEOUT
        model = config.OLLAMA_MODEL_CLASSIFY if kind == "classify" else config.OLLAMA_MODEL_GENERATE
        
        try:
            return await self.call_ollama(model=model, prompt=prompt, timeout_s=timeout_s, **kwargs)
        except (asyncio.TimeoutError, httpx.HTTPError, Exception) as e:
            logger.warning({
                "phase": "llm_call", 
                "provider": "ollama", 
                "status": "error", 
                "fallback": "gemini", 
                "reason": str(e)
            })
            
            # Skip fallback if GEMINI_API_KEY is not set
            if not config.GEMINI_API_KEY:
                logger.warning({
                    "phase": "llm_call",
                    "provider": "gemini",
                    "status": "skipped",
                    "reason": "GEMINI_API_KEY not set"
                })
                # Re-raise the original exception since we can't fallback
                raise
            
            return await self.call_gemini(model=config.GEMINI_MODEL, prompt=prompt, timeout_s=timeout_s, **kwargs)