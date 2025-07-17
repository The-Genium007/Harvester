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

import psycopg2
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Fetch variables
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

# Connect to the database
try:
    connection = psycopg2.connect(
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT,
        dbname=DBNAME
    )
    print("Connection successful!")
    
    # Create a cursor to execute SQL queries
    cursor = connection.cursor()
    
    # Example query
    cursor.execute("SELECT NOW();")
    result = cursor.fetchone()
    print("Current Time:", result)

    # Close the cursor and connection
    cursor.close()
    connection.close()
    print("Connection closed.")

except Exception as e:
    print(f"Failed to connect: {e}")