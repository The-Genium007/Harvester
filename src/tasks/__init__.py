"""
Module d'initialisation pour les tâches Celery
"""

# Import nécessaire pour l'auto-découverte des tâches
from . import discovery_tasks
from . import crawler_tasks 
from . import indexing_tasks
from . import maintenance_tasks

__all__ = [
    "discovery_tasks",
    "crawler_tasks", 
    "indexing_tasks",
    "maintenance_tasks"
]
