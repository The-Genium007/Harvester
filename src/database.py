"""
Database Connection et Session Management
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
from .config import settings
from .models import Base
import asyncpg


class DatabaseManager:
    """Gestionnaire de base de données avec pool de connexions"""
    
    def __init__(self):
        self.engine = None
        self.async_session = None
        
    async def initialize(self):
        """Initialise la connexion à la base de données"""
        # Configuration de l'engine avec pool de connexions
        self.engine = create_async_engine(
            settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=settings.debug
        )
        
        # Configuration de la session factory
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
    async def create_tables(self):
        """Crée toutes les tables si elles n'existent pas"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
    async def close(self):
        """Ferme les connexions"""
        if self.engine:
            await self.engine.dispose()
            
    @asynccontextmanager
    async def get_session(self):
        """Context manager pour obtenir une session de base de données"""
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


# Instance globale du gestionnaire de base de données
db_manager = DatabaseManager()
