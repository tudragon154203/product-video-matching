import asyncio
from services.ebay_auth_api_client import eBayAuthService
from config_loader import config

async def main():
    auth = eBayAuthService(config, None)
    token = await auth.get_access_token()
    print("Access Token:", token)

if __name__ == "__main__":
    asyncio.run(main())