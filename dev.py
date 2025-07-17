#!/usr/bin/env python3
"""
Script de développement pour SentinelIQ Harvester
Facilite le développement et les tests
"""
import os
import sys
import asyncio
import subprocess
from pathlib import Path
from typing import List, Optional

# Ajoute le répertoire racine au PYTHONPATH
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

from src.config import settings
from src.database import db_manager


class DevManager:
    """Gestionnaire pour le développement"""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent
        
    async def init_database(self):
        """Initialise la base de données"""
        print("🗄️ Initialisation de la base de données...")
        
        try:
            # Teste la connexion
            await db_manager.initialize()
            print("✅ Connexion à la base de données établie")
            
            # Crée les tables si nécessaire
            from src.models import Base
            
            async with db_manager.get_session() as session:
                # Active l'extension pgvector si disponible
                try:
                    await session.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    print("✅ Extension pgvector activée")
                except Exception as e:
                    print(f"⚠️ Pgvector non disponible: {e}")
                    
                await session.commit()
                
            print("✅ Base de données initialisée")
            
        except Exception as e:
            print(f"❌ Erreur d'initialisation de la base: {e}")
            return False
            
        finally:
            await db_manager.close()
            
        return True
        
    async def test_discovery(self, categories: Optional[List[str]] = None):
        """Teste le moteur de découverte"""
        print("🔍 Test du moteur de découverte...")
        
        try:
            from src.tasks.discovery_tasks import run_discovery_without_celery
            
            if not categories:
                categories = ["machine learning", "fastapi"]
                
            result = await run_discovery_without_celery(categories, max_sources=5)
            
            print("📊 Résultats de découverte:")
            print(f"  - Sources découvertes: {result.get('sources_discovered', 0)}")
            print(f"  - Sources ajoutées: {result.get('sources_added', 0)}")
            
            if result.get('errors'):
                print("⚠️ Erreurs:")
                for error in result['errors']:
                    print(f"  - {error}")
                    
        except Exception as e:
            print(f"❌ Erreur test découverte: {e}")
            
    async def test_crawler(self, url: str = "https://fastapi.tiangolo.com"):
        """Teste le crawler"""
        print(f"🕷️ Test du crawler sur: {url}")
        
        try:
            from src.crawler.core.smart_crawler import SmartCrawler
            
            crawler = SmartCrawler()
            await crawler.initialize()
            
            result = await crawler.crawl_url(url)
            
            if result:
                print("✅ Crawling réussi:")
                print(f"  - Titre: {result.get('title', 'N/A')[:100]}")
                print(f"  - Contenu: {len(result.get('content', ''))} caractères")
                print(f"  - Qualité: {result.get('quality_score', 0):.2f}")
            else:
                print("❌ Échec du crawling")
                
            await crawler.close()
            
        except Exception as e:
            print(f"❌ Erreur test crawler: {e}")
            
    async def test_search(self, query: str = "machine learning"):
        """Teste la recherche sémantique"""
        print(f"🔎 Test de recherche: '{query}'")
        
        try:
            from src.api.search import SemanticSearchEngine
            
            search_engine = SemanticSearchEngine()
            await search_engine.initialize()
            
            results = await search_engine.search(query, limit=3)
            
            print(f"📊 {len(results)} résultats trouvés:")
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result.get('title', 'N/A')[:80]}")
                print(f"     Score: {result.get('similarity_score', 0):.2f}")
                
            await search_engine.close()
            
        except Exception as e:
            print(f"❌ Erreur test recherche: {e}")
            
    def start_dev_server(self):
        """Démarre le serveur de développement"""
        print("🚀 Démarrage du serveur de développement...")
        
        os.environ["ENVIRONMENT"] = "development"
        
        cmd = [
            "uvicorn",
            "src.api.main:app",
            "--host", "localhost",
            "--port", "8000",
            "--reload",
            "--log-level", "debug"
        ]
        
        subprocess.run(cmd)
        
    async def generate_test_data(self):
        """Génère des données de test"""
        print("📝 Génération de données de test...")
        
        try:
            await db_manager.initialize()
            
            from src.models import Source, Article
            
            async with db_manager.get_session() as session:
                # Crée quelques sources de test
                test_sources = [
                    {
                        "name": "FastAPI Documentation",
                        "base_url": "https://fastapi.tiangolo.com",
                        "category": "web-framework",
                        "description": "Documentation officielle de FastAPI"
                    },
                    {
                        "name": "Python.org",
                        "base_url": "https://www.python.org",
                        "category": "programming-language", 
                        "description": "Site officiel de Python"
                    }
                ]
                
                sources_added = 0
                for source_data in test_sources:
                    # Vérifie si existe déjà
                    existing = await session.execute(
                        "SELECT id FROM sources WHERE base_url = %s",
                        (source_data["base_url"],)
                    )
                    
                    if not existing.fetchone():
                        source = Source(**source_data)
                        session.add(source)
                        sources_added += 1
                        
                await session.commit()
                print(f"✅ {sources_added} sources de test ajoutées")
                
        except Exception as e:
            print(f"❌ Erreur génération données: {e}")
        finally:
            await db_manager.close()
            
    def show_status(self):
        """Affiche le statut du système"""
        print("📊 Statut du système SentinelIQ")
        print("=" * 40)
        
        # Configuration
        print(f"🔧 Environnement: {settings.environment}")
        print(f"🗄️ Base de données: {settings.supabase_url or 'Non configurée'}")
        print(f"📊 Redis: {settings.redis_url}")
        print(f"🤖 OpenAI: {'✅' if settings.openai_api_key else '❌'}")
        
        # Vérification des dépendances
        print("\n📦 Dépendances:")
        
        deps_to_check = [
            ("FastAPI", "fastapi"),
            ("SQLAlchemy", "sqlalchemy"), 
            ("Celery", "celery"),
            ("Redis", "redis"),
            ("OpenAI", "openai"),
            ("BeautifulSoup", "bs4"),
            ("aiohttp", "aiohttp")
        ]
        
        for name, import_name in deps_to_check:
            try:
                __import__(import_name)
                print(f"  ✅ {name}")
            except ImportError:
                print(f"  ❌ {name} (manquant)")
                
    def run_tests(self):
        """Lance les tests"""
        print("🧪 Lancement des tests...")
        
        test_files = list(self.root_dir.glob("tests/**/*.py"))
        
        if not test_files:
            print("⚠️ Aucun fichier de test trouvé")
            return
            
        cmd = ["python", "-m", "pytest", "-v"] + [str(f) for f in test_files]
        subprocess.run(cmd)


def main():
    """Point d'entrée principal"""
    if len(sys.argv) < 2:
        print("🛠️ SentinelIQ Harvester - Outils de développement")
        print()
        print("Commandes disponibles:")
        print("  init-db           Initialise la base de données")
        print("  test-discovery    Teste le moteur de découverte")
        print("  test-crawler      Teste le crawler")
        print("  test-search       Teste la recherche sémantique")
        print("  generate-data     Génère des données de test")
        print("  dev-server        Démarre le serveur de développement")
        print("  status            Affiche le statut du système")
        print("  tests             Lance les tests")
        print()
        print("Exemples:")
        print("  python dev.py init-db")
        print("  python dev.py test-discovery")
        print("  python dev.py test-crawler https://example.com")
        print("  python dev.py test-search 'machine learning'")
        return
        
    command = sys.argv[1]
    dev_manager = DevManager()
    
    if command == "init-db":
        asyncio.run(dev_manager.init_database())
        
    elif command == "test-discovery":
        categories = sys.argv[2:] if len(sys.argv) > 2 else None
        asyncio.run(dev_manager.test_discovery(categories))
        
    elif command == "test-crawler":
        url = sys.argv[2] if len(sys.argv) > 2 else "https://fastapi.tiangolo.com"
        asyncio.run(dev_manager.test_crawler(url))
        
    elif command == "test-search":
        query = sys.argv[2] if len(sys.argv) > 2 else "machine learning"
        asyncio.run(dev_manager.test_search(query))
        
    elif command == "generate-data":
        asyncio.run(dev_manager.generate_test_data())
        
    elif command == "dev-server":
        dev_manager.start_dev_server()
        
    elif command == "status":
        dev_manager.show_status()
        
    elif command == "tests":
        dev_manager.run_tests()
        
    else:
        print(f"❌ Commande inconnue: {command}")
        print("Utilisez 'python dev.py' pour voir les commandes disponibles")


if __name__ == "__main__":
    main()
