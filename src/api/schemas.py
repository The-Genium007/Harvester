"""
Schémas Pydantic pour l'API
"""
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime
from enum import Enum


class SourceType(str, Enum):
    """Types de sources disponibles"""
    blog = "blog"
    news = "news"
    docs = "docs"
    forum = "forum"
    website = "website"


class CreateSourceRequest(BaseModel):
    """Requête de création de source"""
    name: str = Field(..., min_length=1, max_length=255, description="Nom de la source")
    url: HttpUrl = Field(..., description="URL de la source")
    source_type: SourceType = Field(..., description="Type de source")
    category: str = Field(..., min_length=1, max_length=100, description="Catégorie")
    crawl_frequency: Optional[int] = Field(3600, ge=300, le=86400, description="Fréquence de crawl en secondes")
    respect_robots_txt: bool = Field(True, description="Respecter le robots.txt")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Real Python",
                "url": "https://realpython.com",
                "source_type": "blog",
                "category": "python",
                "crawl_frequency": 3600,
                "respect_robots_txt": True
            }
        }


class SourceResponse(BaseModel):
    """Réponse pour une source"""
    id: str
    name: str
    url: str
    domain: str
    source_type: str
    category: str
    language: str
    crawl_frequency: int
    quality_score: float
    relevance_score: float
    freshness_score: float
    is_active: bool
    last_crawled_at: Optional[datetime]
    crawl_count: int
    error_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ArticleResponse(BaseModel):
    """Réponse pour un article"""
    id: str
    source_id: str
    title: str
    url: str
    content_hash: str
    author: Optional[str]
    published_at: Optional[datetime]
    language: str
    word_count: int
    category: str
    tags: List[str] = []
    tech_stack: List[str] = []
    quality_score: float
    relevance_score: float
    sentiment_score: float
    difficulty_level: str
    is_processed: bool
    is_duplicate: bool
    crawled_at: datetime
    processed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ArticleSummaryResponse(BaseModel):
    """Réponse résumée pour un article"""
    id: str
    title: str
    url: str
    author: Optional[str]
    published_at: Optional[datetime]
    category: str
    quality_score: float
    crawled_at: datetime
    
    class Config:
        from_attributes = True


class SearchRequest(BaseModel):
    """Requête de recherche"""
    query: str = Field(..., min_length=1, max_length=500, description="Requête de recherche")
    limit: int = Field(10, ge=1, le=100, description="Nombre de résultats")
    threshold: float = Field(0.7, ge=0, le=1, description="Seuil de similarité")
    category: Optional[str] = Field(None, description="Filtrer par catégorie")
    language: Optional[str] = Field(None, description="Filtrer par langue")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "python machine learning tutorial",
                "limit": 10,
                "threshold": 0.7,
                "category": "python"
            }
        }


class SearchResult(BaseModel):
    """Résultat de recherche"""
    article_id: str
    title: str
    url: str
    content_preview: str = Field(..., max_length=500, description="Aperçu du contenu")
    similarity_score: float
    quality_score: float
    published_at: Optional[datetime]
    category: str
    tags: List[str] = []


class SearchResponse(BaseModel):
    """Réponse de recherche"""
    query: str
    results: List[SearchResult]
    total: int
    threshold: float
    processing_time: float


class CrawlRequest(BaseModel):
    """Requête de crawling"""
    max_pages: int = Field(100, ge=1, le=1000, description="Nombre maximum de pages à crawler")
    force_recrawl: bool = Field(False, description="Forcer le re-crawling même si pas de changement")
    
    class Config:
        schema_extra = {
            "example": {
                "max_pages": 50,
                "force_recrawl": False
            }
        }


class CrawlJobResponse(BaseModel):
    """Réponse pour un job de crawling"""
    id: str
    source_id: str
    job_type: str
    status: str
    progress: float
    pages_crawled: int
    pages_processed: int
    pages_failed: int
    new_articles_found: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


class DiscoveryResultResponse(BaseModel):
    """Réponse pour un résultat de découverte"""
    id: str
    search_query: str
    search_engine: str
    discovered_url: str
    domain: str
    relevance_score: float
    quality_score: float
    tech_relevance_score: float
    title: Optional[str]
    description: Optional[str]
    detected_language: Optional[str]
    detected_category: Optional[str]
    is_validated: bool
    is_tech_relevant: bool
    is_duplicate: bool
    became_source: bool
    discovered_at: datetime
    
    class Config:
        from_attributes = True


class SourceStatsResponse(BaseModel):
    """Statistiques des sources"""
    total_sources: int
    active_sources: int
    recently_crawled: int
    avg_quality_score: float
    categories_count: int
    categories: List[dict]


class ArticleStatsResponse(BaseModel):
    """Statistiques des articles"""
    total_articles: int
    today_articles: int
    week_articles: int
    avg_quality_score: float
    languages_count: int
    languages: List[dict]


class SystemHealthResponse(BaseModel):
    """État de santé du système"""
    status: str  # healthy, degraded, unhealthy
    timestamp: str
    components: dict
    uptime: Optional[float]
    version: str = "1.0.0"


class ErrorResponse(BaseModel):
    """Réponse d'erreur standardisée"""
    error: str
    detail: str
    status_code: int
    timestamp: str


class PaginationInfo(BaseModel):
    """Informations de pagination"""
    page: int
    limit: int
    total: int
    has_next: bool
    has_previous: bool


class PaginatedResponse(BaseModel):
    """Réponse paginée générique"""
    data: List[dict]
    pagination: PaginationInfo


class MetricsResponse(BaseModel):
    """Métriques du système"""
    discovery_stats: dict
    crawling_stats: dict
    processing_stats: dict
    api_stats: dict
    system_resources: dict


class ConfigurationResponse(BaseModel):
    """Configuration du système"""
    discovery_enabled: bool
    crawling_enabled: bool
    max_concurrent_crawls: int
    supported_languages: List[str]
    rate_limits: dict
    quality_thresholds: dict


# Modèles pour les webhooks et notifications
class WebhookEvent(BaseModel):
    """Événement webhook"""
    event_type: str
    timestamp: datetime
    data: dict
    source: str = "sentineliq-harvester"


class NotificationSettings(BaseModel):
    """Paramètres de notification"""
    webhook_url: Optional[HttpUrl]
    email_notifications: bool = False
    slack_webhook: Optional[HttpUrl]
    notification_events: List[str] = ["discovery_completed", "crawl_completed", "error_occurred"]


# Modèles pour l'administration
class AdminSourceUpdate(BaseModel):
    """Mise à jour administrative d'une source"""
    name: Optional[str] = None
    is_active: Optional[bool] = None
    crawl_frequency: Optional[int] = None
    quality_score: Optional[float] = None
    category: Optional[str] = None


class AdminSystemControl(BaseModel):
    """Contrôles administrateur du système"""
    action: str  # start, stop, restart, pause
    component: str  # discovery, crawler, all
    force: bool = False


class BulkActionRequest(BaseModel):
    """Requête d'action en masse"""
    action: str  # activate, deactivate, delete, recrawl
    source_ids: List[str]
    filters: Optional[dict] = None


class ExportRequest(BaseModel):
    """Requête d'export de données"""
    export_type: str  # articles, sources, stats
    format: str = "json"  # json, csv, xlsx
    date_range: Optional[dict] = None
    filters: Optional[dict] = None
