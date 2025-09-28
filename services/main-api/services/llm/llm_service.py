import asyncio
from fastapi import HTTPException
from common_py.logging_config import configure_logging
from config_loader import config
from .ollama_api_client import OllamaAPIClient
from .gemini_api_client import GeminiAPIClient

# Configure logger
logger = configure_logging("main-api:llm_service")


class LLMService:
    def __init__(self):
        self.ollama_client = OllamaAPIClient(config.OLLAMA_HOST)
        self.gemini_client = GeminiAPIClient(
            config.GEMINI_API_KEY, config.GEMINI_MODEL)

    async def call_ollama(self, model: str, prompt: str, timeout_s: int, options: dict = None) -> dict:
        """Call Ollama API."""
        return await self.ollama_client.generate(model, prompt, timeout_s, options)

    async def call_gemini(self, model: str, prompt: str, timeout_s: int, **kwargs) -> dict:
        """Call Gemini API."""
        return await self.gemini_client.generate_content(prompt, timeout_s)

    async def call_llm(self, kind: str, prompt: str, **kwargs) -> dict:
        """
        Call LLM with primary Gemini provider and Ollama fallback.

        This method follows the new priority order:
        1. First attempts to call Gemini API (production-ready)
        2. Falls back to Ollama only if Gemini fails

        Args:
            kind: The type of LLM call ("classify" or "generate")
            prompt: The prompt to send to the LLM
            **kwargs: Additional options for the LLM call

        Returns:
            dict: LLM response containing the "response" key

        Raises:
            HTTPException: If both Gemini and Ollama fail
            Exception: Original exception if no fallback is available
        """
        timeout_s = config.LLM_TIMEOUT
        model = config.OLLAMA_MODEL_CLASSIFY if kind == "classify" else config.OLLAMA_MODEL_GENERATE

        # Skip Gemini if GEMINI_API_KEY is not set
        if not config.GEMINI_API_KEY:
            logger.warning({
                "phase": "llm_call",
                "provider": "gemini",
                "status": "skipped",
                "reason": "GEMINI_API_KEY not set"
            })
            # Fall back to Ollama directly
            return await self.call_ollama(model=model, prompt=prompt, timeout_s=timeout_s, **kwargs)

        try:
            # Try Gemini first (production-ready)
            return await self.call_gemini(model=config.GEMINI_MODEL, prompt=prompt, timeout_s=timeout_s, **kwargs)
        except (asyncio.TimeoutError, HTTPException, Exception) as e:
            logger.warning({
                "phase": "llm_call",
                "provider": "gemini",
                "status": "error",
                "fallback": "ollama",
                "reason": str(e)
            })

            # Fall back to Ollama
            return await self.call_ollama(model=model, prompt=prompt, timeout_s=timeout_s, **kwargs)
