"""
Module d'initialisation pour le package src
"""

# Import des modules principaux pour faciliter l'utilisation
from .config import settings
from .database import db_manager

__version__ = "1.0.0"
__author__ = "SentinelIQ Team"
__description__ = "Système de veille technique autonome"

# Configuration du logging global
import logging
import sys

def setup_logging():
    """Configure le logging global"""
    level = logging.INFO if settings.environment == "production" else logging.DEBUG
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("sentineliq.log", encoding="utf-8")
        ]
    )
    
    # Réduit le niveau de certains loggers verbeux
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)

# Initialise le logging au chargement du module
setup_logging()

__all__ = ["settings", "db_manager", "setup_logging"]
