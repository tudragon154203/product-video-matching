from typing import AsyncGenerator, Annotated
from fastapi import Depends, Request
from contextlib import asynccontextmanager

from common_py.database import DatabaseManager
from core.config import get_settings


class DatabaseManagerSingleton:
    _instance: DatabaseManager = None

    @classmethod
    async def get_instance(cls, request: Request) -> DatabaseManager:
        if cls._instance is None:
            settings = get_settings()
            cls._instance = DatabaseManager(settings.database.dsn)
            await cls._instance.connect()
        
        return cls._instance

    @classmethod
    @asynccontextmanager
    async def get_db_context(cls, request: Request) -> AsyncGenerator[DatabaseManager, None]:
        db = await cls.get_instance(request)
        try:
            yield db
        except Exception:
            await db.disconnect()
            raise


async def get_db_session(request: Request) -> DatabaseManager:
    return await DatabaseManagerSingleton.get_instance(request)


DatabaseDependency = Annotated[DatabaseManager, Depends(get_db_session)]