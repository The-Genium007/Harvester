"""
Tâches de découverte automatique avec Celery
"""
from typing import List, Dict, Any
import asyncio
from datetime import datetime

try:
    from celery import Task
    from ..celery_app import celery_app
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    
from ..config import settings
from ..discovery.engine import DiscoveryEngine
from ..database import db_manager
from ..models import Source, DiscoveryResult


class AsyncTask(Task):
    """Classe de base pour les tâches asynchrones"""
    
    def __call__(self, *args, **kwargs):
        """Wrapper pour exécuter les tâches async"""
        return asyncio.run(self.run_async(*args, **kwargs))
        
    async def run_async(self, *args, **kwargs):
        """Méthode à override pour les tâches async"""
        raise NotImplementedError


@celery_app.task(bind=True, base=AsyncTask, name="src.tasks.discovery_tasks.run_auto_discovery")
async def run_auto_discovery(self, categories: List[str] = None, max_sources: int = 50) -> Dict[str, Any]:
    """
    Lance la découverte automatique de nouvelles sources
    
    Args:
        categories: Catégories à explorer (optionnel)
        max_sources: Nombre maximum de sources à découvrir
        
    Returns:
        Résultats de la découverte
    """
    print(f"🔍 Démarrage de la découverte automatique (tâche {self.request.id})")
    
    try:
        engine = DiscoveryEngine()
        await engine.initialize()
        
        # Utilise les catégories par défaut si non spécifiées
        if not categories:
            categories = [
                "machine learning", "artificial intelligence", "cloud computing",
                "cybersecurity", "blockchain", "devops", "web development",
                "mobile development", "data science", "kubernetes"
            ]
        
        results = {
            "task_id": self.request.id,
            "started_at": datetime.now().isoformat(),
            "categories_explored": categories,
            "sources_discovered": 0,
            "sources_added": 0,
            "total_urls": 0,
            "errors": []
        }
        
        all_discovered_sources = []
        
        # Découverte par catégorie
        for category in categories:
            try:
                print(f"🔍 Exploration de la catégorie: {category}")
                
                category_sources = await engine.discover_sources(
                    topics=[category],
                    max_sources=max_sources // len(categories)
                )
                
                all_discovered_sources.extend(category_sources)
                results["total_urls"] += len(category_sources)
                
                # Petite pause entre catégories
                await asyncio.sleep(2)
                
            except Exception as e:
                error_msg = f"Erreur lors de l'exploration de {category}: {str(e)}"
                print(f"❌ {error_msg}")
                results["errors"].append(error_msg)
                
        # Sauvegarde des sources découvertes
        sources_added = 0
        async with db_manager.get_session() as session:
            for source_data in all_discovered_sources:
                try:
                    # Vérifie si la source existe déjà
                    existing = await session.execute(
                        "SELECT id FROM sources WHERE base_url = %s",
                        (source_data["base_url"],)
                    )
                    
                    if existing.fetchone():
                        continue  # Source déjà présente
                        
                    # Crée la nouvelle source
                    source = Source(
                        name=source_data["name"],
                        base_url=source_data["base_url"],
                        description=source_data.get("description", ""),
                        category=source_data.get("category", "general"),
                        trust_score=source_data.get("trust_score", 0.5),
                        crawl_frequency=3600,  # 1 heure par défaut
                        is_active=True
                    )
                    
                    session.add(source)
                    sources_added += 1
                    
                    # Sauvegarde le résultat de découverte
                    discovery_result = DiscoveryResult(
                        search_query=source_data.get("search_query", category),
                        discovered_url=source_data["base_url"],
                        relevance_score=source_data.get("relevance_score", 0.5),
                        quality_score=source_data.get("quality_score", 0.5),
                        category=source_data.get("category", "general"),
                        metadata=source_data.get("metadata", {}),
                        is_processed=True
                    )
                    
                    session.add(discovery_result)
                    
                except Exception as e:
                    error_msg = f"Erreur lors de la sauvegarde de {source_data['base_url']}: {str(e)}"
                    print(f"❌ {error_msg}")
                    results["errors"].append(error_msg)
                    
            try:
                await session.commit()
                print(f"✅ {sources_added} nouvelles sources ajoutées")
            except Exception as e:
                await session.rollback()
                error_msg = f"Erreur lors de la sauvegarde: {str(e)}"
                print(f"❌ {error_msg}")
                results["errors"].append(error_msg)
                
        results.update({
            "sources_discovered": len(all_discovered_sources),
            "sources_added": sources_added,
            "completed_at": datetime.now().isoformat(),
            "status": "completed" if not results["errors"] else "completed_with_errors"
        })
        
        await engine.close()
        
        print(f"🎉 Découverte terminée: {sources_added} sources ajoutées")
        return results
        
    except Exception as e:
        error_msg = f"Erreur critique dans la découverte: {str(e)}"
        print(f"💥 {error_msg}")
        
        return {
            "task_id": self.request.id,
            "status": "failed",
            "error": error_msg,
            "completed_at": datetime.now().isoformat()
        }


@celery_app.task(bind=True, base=AsyncTask, name="src.tasks.discovery_tasks.discover_category_sources")
async def discover_category_sources(self, category: str, max_sources: int = 20) -> Dict[str, Any]:
    """
    Découvre des sources pour une catégorie spécifique
    
    Args:
        category: Catégorie à explorer
        max_sources: Nombre maximum de sources
        
    Returns:
        Résultats de la découverte pour cette catégorie
    """
    print(f"🎯 Découverte ciblée pour la catégorie: {category}")
    
    try:
        engine = DiscoveryEngine()
        await engine.initialize()
        
        sources = await engine.discover_sources(
            topics=[category],
            max_sources=max_sources
        )
        
        # Sauvegarde des résultats
        sources_added = 0
        async with db_manager.get_session() as session:
            for source_data in sources:
                try:
                    # Vérifie l'existence
                    existing = await session.execute(
                        "SELECT id FROM sources WHERE base_url = %s",
                        (source_data["base_url"],)
                    )
                    
                    if not existing.fetchone():
                        source = Source(
                            name=source_data["name"],
                            base_url=source_data["base_url"],
                            description=source_data.get("description", ""),
                            category=category,
                            trust_score=source_data.get("trust_score", 0.5),
                            crawl_frequency=3600,
                            is_active=True
                        )
                        
                        session.add(source)
                        sources_added += 1
                        
                except Exception as e:
                    print(f"❌ Erreur source {source_data['base_url']}: {e}")
                    
            await session.commit()
            
        await engine.close()
        
        result = {
            "task_id": self.request.id,
            "category": category,
            "sources_discovered": len(sources),
            "sources_added": sources_added,
            "status": "completed",
            "completed_at": datetime.now().isoformat()
        }
        
        print(f"✅ Catégorie {category}: {sources_added} sources ajoutées")
        return result
        
    except Exception as e:
        error_msg = f"Erreur découverte catégorie {category}: {str(e)}"
        print(f"❌ {error_msg}")
        
        return {
            "task_id": self.request.id,
            "category": category,
            "status": "failed",
            "error": error_msg,
            "completed_at": datetime.now().isoformat()
        }


@celery_app.task(bind=True, base=AsyncTask, name="src.tasks.discovery_tasks.validate_discovered_sources")
async def validate_discovered_sources(self, source_ids: List[str] = None) -> Dict[str, Any]:
    """
    Valide les sources découvertes (vérifie leur accessibilité)
    
    Args:
        source_ids: IDs des sources à valider (toutes si None)
        
    Returns:
        Résultats de validation
    """
    print(f"🔍 Validation des sources découvertes")
    
    try:
        from ..crawler.core.smart_crawler import SmartCrawler
        
        crawler = SmartCrawler()
        await crawler.initialize()
        
        results = {
            "task_id": self.request.id,
            "sources_validated": 0,
            "sources_active": 0,
            "sources_inactive": 0,
            "errors": []
        }
        
        async with db_manager.get_session() as session:
            # Récupère les sources à valider
            if source_ids:
                query = "SELECT id, name, base_url FROM sources WHERE id = ANY(%s)"
                params = (source_ids,)
            else:
                # Valide les sources récemment découvertes non validées
                query = """
                    SELECT id, name, base_url 
                    FROM sources 
                    WHERE created_at >= NOW() - INTERVAL '24 hours'
                      AND last_crawl_attempt IS NULL
                    LIMIT 50
                """
                params = ()
                
            result = await session.execute(query, params)
            sources = result.fetchall()
            
            for source_row in sources:
                source_id, name, base_url = source_row
                
                try:
                    # Test d'accessibilité simple
                    is_accessible = await crawler._test_url_accessibility(base_url)
                    
                    if is_accessible:
                        # Marque comme active
                        await session.execute(
                            "UPDATE sources SET is_active = true, last_crawl_attempt = NOW() WHERE id = %s",
                            (source_id,)
                        )
                        results["sources_active"] += 1
                        print(f"✅ Source accessible: {name}")
                    else:
                        # Marque comme inactive
                        await session.execute(
                            "UPDATE sources SET is_active = false, last_crawl_attempt = NOW() WHERE id = %s",
                            (source_id,)
                        )
                        results["sources_inactive"] += 1
                        print(f"❌ Source inaccessible: {name}")
                        
                    results["sources_validated"] += 1
                    
                    # Pause entre validations
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    error_msg = f"Erreur validation {name}: {str(e)}"
                    print(f"⚠️ {error_msg}")
                    results["errors"].append(error_msg)
                    
            await session.commit()
            
        await crawler.close()
        
        results.update({
            "status": "completed",
            "completed_at": datetime.now().isoformat()
        })
        
        print(f"🎉 Validation terminée: {results['sources_active']} actives, {results['sources_inactive']} inactives")
        return results
        
    except Exception as e:
        error_msg = f"Erreur critique validation: {str(e)}"
        print(f"💥 {error_msg}")
        
        return {
            "task_id": self.request.id,
            "status": "failed",
            "error": error_msg,
            "completed_at": datetime.now().isoformat()
        }


@celery_app.task(bind=True, base=AsyncTask, name="src.tasks.discovery_tasks.cleanup_duplicate_sources")
async def cleanup_duplicate_sources(self) -> Dict[str, Any]:
    """
    Nettoie les sources en double basées sur l'URL de base
    
    Returns:
        Résultats du nettoyage
    """
    print("🧹 Nettoyage des sources dupliquées")
    
    try:
        results = {
            "task_id": self.request.id,
            "duplicates_found": 0,
            "duplicates_removed": 0,
            "errors": []
        }
        
        async with db_manager.get_session() as session:
            # Trouve les doublons
            duplicate_query = """
                SELECT base_url, array_agg(id ORDER BY created_at) as ids
                FROM sources
                GROUP BY base_url
                HAVING COUNT(*) > 1
            """
            
            duplicate_result = await session.execute(duplicate_query)
            duplicates = duplicate_result.fetchall()
            
            for row in duplicates:
                base_url, ids = row
                results["duplicates_found"] += len(ids) - 1  # -1 car on garde le premier
                
                # Garde le plus ancien, supprime les autres
                ids_to_remove = ids[1:]  # Tous sauf le premier
                
                try:
                    # Supprime les articles des sources dupliquées
                    await session.execute(
                        "DELETE FROM articles WHERE source_id = ANY(%s)",
                        (ids_to_remove,)
                    )
                    
                    # Supprime les sources dupliquées
                    await session.execute(
                        "DELETE FROM sources WHERE id = ANY(%s)",
                        (ids_to_remove,)
                    )
                    
                    results["duplicates_removed"] += len(ids_to_remove)
                    print(f"🗑️ Supprimé {len(ids_to_remove)} doublons de {base_url}")
                    
                except Exception as e:
                    error_msg = f"Erreur suppression doublons {base_url}: {str(e)}"
                    print(f"❌ {error_msg}")
                    results["errors"].append(error_msg)
                    
            await session.commit()
            
        results.update({
            "status": "completed",
            "completed_at": datetime.now().isoformat()
        })
        
        print(f"🎉 Nettoyage terminé: {results['duplicates_removed']} doublons supprimés")
        return results
        
    except Exception as e:
        error_msg = f"Erreur critique nettoyage: {str(e)}"
        print(f"💥 {error_msg}")
        
        return {
            "task_id": self.request.id,
            "status": "failed", 
            "error": error_msg,
            "completed_at": datetime.now().isoformat()
        }


# Fonction utilitaire sans Celery
async def run_discovery_without_celery(categories: List[str] = None, max_sources: int = 50):
    """Version sans Celery pour les tests"""
    if not CELERY_AVAILABLE:
        print("⚠️ Celery non disponible, exécution directe")
        
        # Simulation de l'exécution de tâche
        task_mock = type('MockTask', (), {
            'request': type('MockRequest', (), {'id': 'direct-exec'})()
        })()
        
        return await run_auto_discovery.run_async(task_mock, categories, max_sources)
