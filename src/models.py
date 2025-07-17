"""
Database Models pour SentinelIQ Harvester
"""
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, 
    Float, JSON, Index, ForeignKey, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid

Base = declarative_base()


class Source(Base):
    """Modèle pour les sources de contenu"""
    __tablename__ = "sources"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    url = Column(String(2048), nullable=False, unique=True)
    domain = Column(String(255), nullable=False, index=True)
    
    # Métadonnées de la source
    source_type = Column(String(50), nullable=False)  # blog, news, docs, forum
    category = Column(String(100), nullable=False, index=True)
    language = Column(String(10), nullable=False, default="en")
    
    # Configuration de crawling
    crawl_frequency = Column(Integer, nullable=False, default=3600)  # secondes
    respect_robots_txt = Column(Boolean, nullable=False, default=True)
    max_depth = Column(Integer, nullable=False, default=3)
    
    # Métriques de qualité
    quality_score = Column(Float, nullable=False, default=0.0)
    relevance_score = Column(Float, nullable=False, default=0.0)
    freshness_score = Column(Float, nullable=False, default=0.0)
    
    # Statut et suivi
    is_active = Column(Boolean, nullable=False, default=True)
    last_crawled_at = Column(DateTime(timezone=True))
    last_updated_at = Column(DateTime(timezone=True))
    crawl_count = Column(Integer, nullable=False, default=0)
    error_count = Column(Integer, nullable=False, default=0)
    
    # Métadonnées techniques
    robots_txt_url = Column(String(2048))
    sitemap_url = Column(String(2048))
    rss_feed_url = Column(String(2048))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_sources_domain_active', 'domain', 'is_active'),
        Index('idx_sources_category_quality', 'category', 'quality_score'),
    )


class Article(Base):
    """Modèle pour les articles crawlés"""
    __tablename__ = "articles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey('sources.id'), nullable=False)
    
    # Métadonnées de base
    title = Column(String(1000), nullable=False)
    url = Column(String(2048), nullable=False, unique=True)
    content_hash = Column(String(64), nullable=False, index=True)
    
    # Contenu
    content = Column(Text, nullable=False)
    summary = Column(Text)
    
    # Métadonnées extractives
    author = Column(String(255))
    published_at = Column(DateTime(timezone=True))
    language = Column(String(10), nullable=False)
    word_count = Column(Integer, nullable=False, default=0)
    
    # Classification automatique
    category = Column(String(100), nullable=False, index=True)
    tags = Column(ARRAY(String(50)), default=[])
    tech_stack = Column(ARRAY(String(50)), default=[])
    
    # Scores et métriques
    quality_score = Column(Float, nullable=False, default=0.0)
    relevance_score = Column(Float, nullable=False, default=0.0)
    sentiment_score = Column(Float, nullable=False, default=0.0)
    difficulty_level = Column(String(20), default="intermediate")  # beginner, intermediate, advanced
    
    # Embeddings pour recherche vectorielle
    content_embedding = Column(Vector(1536))  # OpenAI ada-002 dimensions
    title_embedding = Column(Vector(1536))
    
    # Métadonnées techniques
    http_status = Column(Integer, nullable=False, default=200)
    content_type = Column(String(100))
    last_modified = Column(DateTime(timezone=True))
    etag = Column(String(255))
    
    # Statut de traitement
    is_processed = Column(Boolean, nullable=False, default=False)
    is_duplicate = Column(Boolean, nullable=False, default=False)
    processing_errors = Column(JSON)
    
    # Timestamps
    crawled_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_articles_source_crawled', 'source_id', 'crawled_at'),
        Index('idx_articles_category_quality', 'category', 'quality_score'),
        Index('idx_articles_content_hash', 'content_hash'),
        Index('idx_articles_published', 'published_at'),
        # Index pour recherche vectorielle
        Index('idx_articles_content_embedding', 'content_embedding', postgresql_using='ivfflat'),
    )


class CrawlJob(Base):
    """Modèle pour le suivi des tâches de crawling"""
    __tablename__ = "crawl_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey('sources.id'), nullable=False)
    
    # Configuration du job
    job_type = Column(String(50), nullable=False)  # discovery, full_crawl, update_check
    priority = Column(Integer, nullable=False, default=1)
    max_pages = Column(Integer, default=100)
    
    # Statut d'exécution
    status = Column(String(20), nullable=False, default="pending")  # pending, running, completed, failed
    progress = Column(Float, nullable=False, default=0.0)
    
    # Métriques de performance
    pages_crawled = Column(Integer, nullable=False, default=0)
    pages_processed = Column(Integer, nullable=False, default=0)
    pages_failed = Column(Integer, nullable=False, default=0)
    new_articles_found = Column(Integer, nullable=False, default=0)
    
    # Timestamps et durée
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Float)
    
    # Erreurs et logs
    error_message = Column(Text)
    error_details = Column(JSON)
    worker_id = Column(String(100))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_crawl_jobs_status_priority', 'status', 'priority'),
        Index('idx_crawl_jobs_source_created', 'source_id', 'created_at'),
    )


class DiscoveryResult(Base):
    """Modèle pour les résultats de découverte de nouvelles sources"""
    __tablename__ = "discovery_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Informations de découverte
    search_query = Column(String(255), nullable=False)
    search_engine = Column(String(50), nullable=False)
    discovered_url = Column(String(2048), nullable=False)
    domain = Column(String(255), nullable=False, index=True)
    
    # Scores d'évaluation
    relevance_score = Column(Float, nullable=False, default=0.0)
    quality_score = Column(Float, nullable=False, default=0.0)
    tech_relevance_score = Column(Float, nullable=False, default=0.0)
    
    # Métadonnées extraites
    title = Column(String(1000))
    description = Column(Text)
    detected_language = Column(String(10))
    detected_category = Column(String(100))
    
    # Statut de validation
    is_validated = Column(Boolean, nullable=False, default=False)
    is_tech_relevant = Column(Boolean, nullable=False, default=False)
    is_duplicate = Column(Boolean, nullable=False, default=False)
    became_source = Column(Boolean, nullable=False, default=False)
    
    # Référence à la source créée (si applicable)
    source_id = Column(UUID(as_uuid=True), ForeignKey('sources.id'))
    
    # Timestamps
    discovered_at = Column(DateTime(timezone=True), server_default=func.now())
    validated_at = Column(DateTime(timezone=True))
    
    __table_args__ = (
        Index('idx_discovery_domain_validated', 'domain', 'is_validated'),
        Index('idx_discovery_relevance_score', 'tech_relevance_score'),
        UniqueConstraint('search_query', 'discovered_url', name='uq_discovery_query_url'),
    )


class ContentHash(Base):
    """Modèle pour la déduplication de contenu"""
    __tablename__ = "content_hashes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Hash du contenu
    content_hash = Column(String(64), nullable=False, unique=True, index=True)
    url_hash = Column(String(64), nullable=False, index=True)
    
    # Métadonnées du contenu
    content_length = Column(Integer, nullable=False)
    title_hash = Column(String(64))
    
    # Références
    first_article_id = Column(UUID(as_uuid=True), ForeignKey('articles.id'), nullable=False)
    duplicate_count = Column(Integer, nullable=False, default=0)
    
    # Timestamps
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_content_hash_url', 'url_hash'),
    )


class SystemMetrics(Base):
    """Modèle pour les métriques système"""
    __tablename__ = "system_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Type de métrique
    metric_type = Column(String(50), nullable=False)  # crawler_performance, discovery_stats, etc.
    metric_name = Column(String(100), nullable=False)
    
    # Valeurs
    value = Column(Float, nullable=False)
    unit = Column(String(20))
    
    # Contexte
    component = Column(String(50))  # crawler, discovery, processor, api
    worker_id = Column(String(100))
    metric_metadata = Column(JSON)  # Renommé pour éviter le conflit avec metadata de SQLAlchemy
    
    # Timestamp
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_metrics_type_recorded', 'metric_type', 'recorded_at'),
        Index('idx_metrics_component_name', 'component', 'metric_name'),
    )
