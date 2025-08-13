#!/usr/bin/env python3
import httpx
import asyncio
import json

async def test_ollama_generate():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'http://host.docker.internal:11434/api/generate',
                json={
                    'model': 'qwen3:4b-instruct',
                    'prompt': 'Test prompt',
                    'stream': False,
                    'options': {'timeout': 60000}
                },
                timeout=60
            )
            print('Generate response status:', response.status_code)
            if response.status_code == 200:
                data = response.json()
                print('Response keys:', list(data.keys()))
                print('Response text length:', len(data.get('response', '')))
            else:
                print('Error response:', response.text)
    except Exception as e:
        print('Generate request failed:', str(e))
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ollama_generate())