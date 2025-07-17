"""
Script de démarrage principal pour SentinelIQ Harvester
"""
import asyncio
import uvicorn
from src.api.main import app
from src.config import settings

def main():
    """Point d'entrée principal de l'application"""
    print("🚀 Démarrage de SentinelIQ Harvester")
    print(f"🌐 Mode: {settings.environment}")
    print(f"🔧 API sur: http://localhost:{settings.api_port}")
    
    # Configuration d'Uvicorn
    config = uvicorn.Config(
        app=app,
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development",
        log_level="info" if settings.environment == "production" else "debug",
        access_log=True
    )
    
    server = uvicorn.Server(config)
    
    # Démarrage du serveur
    asyncio.run(server.serve())

if __name__ == "__main__":
    main()
