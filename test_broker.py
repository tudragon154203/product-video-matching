#!/usr/bin/env python3
import asyncio
from common_py.messaging import MessageBroker

async def test_broker():
    try:
        broker = MessageBroker('amqp://guest:guest@localhost:5672//')
        await broker.connect()
        print('Connected to broker successfully')
        await broker.disconnect()
        print('Disconnected successfully')
        return True
    except Exception as e:
        print(f'Failed to connect to broker: {e}')
        return False

if __name__ == "__main__":
    success = asyncio.run(test_broker())
    exit(0 if success else 1)
