"""
SentinelIQ Harvester - Configuration et Settings
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Configuration principale de l'application"""
    
    # Environment
    environment: str = "development"
    debug: bool = False
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    secret_key: str = "change-me-in-production"
    
    # Supabase
    supabase_url: str = "http://localhost:54321"
    supabase_key: str = "test-key"
    supabase_service_role_key: str = "test-service-key"
    
    # Database
    database_url: str = "sqlite:///./test.db"
    database_pool_size: int = 20
    database_max_overflow: int = 30
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 20
    
    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_worker_concurrency: int = 4
    
    # Crawler
    crawler_max_workers: int = 50
    crawler_request_timeout: int = 30
    crawler_max_retries: int = 3
    crawler_delay_min: float = 1.0
    crawler_delay_max: float = 3.0
    crawler_user_agents: List[str] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    ]
    
    # Search Engines
    google_search_api_key: Optional[str] = None
    google_search_cx: Optional[str] = None
    bing_search_api_key: Optional[str] = None
    
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "text-embedding-3-small"
    
    # Content Processing
    content_min_length: int = 100
    content_max_length: int = 50000
    supported_languages: List[str] = ["en", "fr", "es", "de", "it"]
    default_language: str = "en"
    
    # Anti-duplication
    hash_algorithm: str = "sha256"
    content_similarity_threshold: float = 0.85
    update_check_interval: int = 3600
    
    # Discovery
    discovery_interval: int = 3600
    discovery_search_queries: List[str] = [
        "python", "javascript", "ai", "machine learning", 
        "web development", "devops", "kubernetes", "docker"
    ]
    discovery_max_results_per_query: int = 100
    discovery_relevance_threshold: float = 0.7
    
    # Monitoring
    prometheus_port: int = 9090
    log_level: str = "INFO"
    log_format: str = "json"
    metrics_enabled: bool = True
    
    # Rate Limiting
    rate_limit_per_domain: str = "10/minute"
    rate_limit_global: str = "1000/minute"
    respect_robots_txt: bool = True
    
    # Scaling
    auto_scale_enabled: bool = True
    min_workers: int = 2
    max_workers: int = 50
    scale_up_threshold: int = 80
    scale_down_threshold: int = 20
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore les champs supplémentaires
        case_sensitive = False


# Instance globale des settings
settings = Settings()
