from unittest.mock import AsyncMock

mock_auth = AsyncMock()
mock_auth.get_token.return_value = 'test_token_123'
mock_auth.refresh_token = AsyncMock()

print('Mock created successfully')
print('get_token method exists:', hasattr(mock_auth, 'get_token'))
print('refresh_token method exists:', hasattr(mock_auth, 'refresh_token'))