"""
Configuration et gestion des tâches Celery pour SentinelIQ
"""
from celery import Celery
from datetime import timedelta
import os

from .config import settings

# Configuration Celery
celery_app = Celery(
    "sentineliq-harvester",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "src.tasks.discovery_tasks",
        "src.tasks.crawler_tasks", 
        "src.tasks.indexing_tasks",
        "src.tasks.maintenance_tasks"
    ]
)

# Configuration avancée
celery_app.conf.update(
    # Sérialisation
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Optimisations
    task_compression="gzip",
    result_compression="gzip",
    
    # Gestion des tâches
    task_track_started=True,
    task_time_limit=3600,  # 1 heure max par tâche
    task_soft_time_limit=3300,  # 55 minutes soft limit
    
    # Préfetch et concurrence
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    
    # Retry policy
    task_default_retry_delay=60,
    task_max_retries=3,
    
    # Routes
    task_routes={
        "src.tasks.discovery_tasks.*": {"queue": "discovery"},
        "src.tasks.crawler_tasks.*": {"queue": "crawler"},
        "src.tasks.indexing_tasks.*": {"queue": "indexing"},
        "src.tasks.maintenance_tasks.*": {"queue": "maintenance"},
    },
    
    # Scheduling périodique
    beat_schedule={
        # Découverte automatique toutes les 6 heures
        "auto-discovery": {
            "task": "src.tasks.discovery_tasks.run_auto_discovery",
            "schedule": timedelta(hours=6),
            "options": {"queue": "discovery"}
        },
        
        # Crawling des sources actives toutes les 2 heures
        "scheduled-crawling": {
            "task": "src.tasks.crawler_tasks.crawl_active_sources",
            "schedule": timedelta(hours=2),
            "options": {"queue": "crawler"}
        },
        
        # Indexation sémantique toutes les heures
        "semantic-indexing": {
            "task": "src.tasks.indexing_tasks.index_new_articles",
            "schedule": timedelta(hours=1),
            "options": {"queue": "indexing"}
        },
        
        # Nettoyage quotidien
        "daily-cleanup": {
            "task": "src.tasks.maintenance_tasks.daily_cleanup",
            "schedule": timedelta(days=1),
            "options": {"queue": "maintenance"}
        },
        
        # Métriques système toutes les 15 minutes
        "system-metrics": {
            "task": "src.tasks.maintenance_tasks.collect_system_metrics",
            "schedule": timedelta(minutes=15),
            "options": {"queue": "maintenance"}
        },
        
        # Sauvegarde hebdomadaire
        "weekly-backup": {
            "task": "src.tasks.maintenance_tasks.weekly_backup",
            "schedule": timedelta(days=7),
            "options": {"queue": "maintenance"}
        }
    }
)

# Configuration des queues avec priorités
celery_app.conf.task_default_queue = "default"
celery_app.conf.task_queues = {
    "discovery": {
        "routing_key": "discovery",
        "priority": 8
    },
    "crawler": {
        "routing_key": "crawler", 
        "priority": 6
    },
    "indexing": {
        "routing_key": "indexing",
        "priority": 4
    },
    "maintenance": {
        "routing_key": "maintenance",
        "priority": 2
    },
    "default": {
        "routing_key": "default",
        "priority": 1
    }
}

# Hooks Celery
@celery_app.task(bind=True)
def debug_task(self):
    """Tâche de debug pour tester Celery"""
    print(f"Request: {self.request!r}")
    return {"status": "success", "worker_id": self.request.id}


# Configuration du monitoring
if settings.enable_monitoring:
    # Configuration Flower pour le monitoring des tâches
    celery_app.conf.update(
        flower_basic_auth=f"{settings.flower_user}:{settings.flower_password}",
        flower_address="0.0.0.0",
        flower_port=5555
    )


# Gestionnaire d'événements pour les métriques
@celery_app.task(bind=True)
def task_failure_handler(self, task_id, error, einfo):
    """Gestionnaire d'échec de tâche pour les métriques"""
    from .models import SystemMetrics
    from .database import db_manager
    import asyncio
    
    async def log_failure():
        async with db_manager.get_session() as session:
            # Log l'échec pour les métriques
            print(f"Task {task_id} failed: {error}")
            # Ici on pourrait enregistrer en base les échecs
            
    asyncio.run(log_failure())


@celery_app.task(bind=True)
def task_success_handler(self, task_id, result):
    """Gestionnaire de succès de tâche pour les métriques"""
    # Log le succès si nécessaire
    pass


# Fonction d'initialisation pour les workers
def init_worker(**kwargs):
    """Initialise les workers Celery"""
    print("Initializing Celery worker...")
    
    # Configuration logging
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Autres initialisations si nécessaires
    print("Worker initialized successfully")


# Enregistrement des hooks
celery_app.signals.worker_init.connect(init_worker)


# Fonction utilitaire pour démarrer un worker
def start_worker(queues=None, concurrency=None):
    """
    Démarre un worker Celery avec configuration
    
    Args:
        queues: Liste des queues à traiter
        concurrency: Niveau de concurrence
    """
    if queues is None:
        queues = ["default", "discovery", "crawler", "indexing", "maintenance"]
        
    if concurrency is None:
        concurrency = os.cpu_count() or 4
        
    celery_app.worker_main([
        "worker",
        f"--queues={','.join(queues)}",
        f"--concurrency={concurrency}",
        "--loglevel=info",
        "--optimization=fair"
    ])


# Export de l'instance Celery
__all__ = ["celery_app", "start_worker", "debug_task"]
