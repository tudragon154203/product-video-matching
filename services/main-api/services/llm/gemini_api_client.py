import httpx
from fastapi import HTTPException
from common_py.logging_config import configure_logging

logger = configure_logging("main-api:gemini_api_client")


class GeminiAPIClient:
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def generate_content(self, prompt: str, timeout_s: int) -> dict:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")

        headers = {"x-goog-api-key": f"{self.api_key}"}
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
                    f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                text = data.get("candidates", [{}])[0].get(
                    "content", {}).get("parts", [{}])[0].get("text", "")
                return {"response": text}
            except httpx.RequestError as e:
                logger.error("Gemini request failed", error=str(e))
                raise HTTPException(
                    status_code=500, detail=f"Gemini request failed: {str(e)}")
            except httpx.HTTPStatusError as e:
                logger.error("Gemini request failed",
                             status_code=e.response.status_code, error=e.response.text)
                raise HTTPException(
                    status_code=500, detail=f"Gemini request failed: {e.response.text}")
