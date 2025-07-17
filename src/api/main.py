"""
API REST FastAPI pour SentinelIQ Harvester
"""
from fastapi import FastAPI, HTTPException, Depends, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio

from ..config import settings
from ..database import db_manager
from ..models import Source, Article, DiscoveryResult, CrawlJob
from ..discovery.engine import AutonomousDiscovery
from ..crawler.core.smart_crawler import SmartCrawler
from .schemas import (
    ArticleResponse, SourceResponse, SearchRequest, 
    CreateSourceRequest, CrawlRequest
)
from .dependencies import get_db_session
from .search import SemanticSearchEngine


# Initialisation de l'application FastAPI
app = FastAPI(
    title="SentinelIQ Harvester API",
    description="API for autonomous technical content discovery and crawling",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifier les domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instances globales
discovery_engine: Optional[AutonomousDiscovery] = None
crawler: Optional[SmartCrawler] = None
search_engine: Optional[SemanticSearchEngine] = None


@app.on_event("startup")
async def startup_event():
    """Initialise les composants au démarrage"""
    global discovery_engine, crawler, search_engine
    
    # Initialise la base de données
    await db_manager.initialize()
    await db_manager.create_tables()
    
    # Initialise les moteurs
    discovery_engine = AutonomousDiscovery()
    await discovery_engine.initialize()
    
    crawler = SmartCrawler()
    await crawler.initialize()
    
    search_engine = SemanticSearchEngine()
    await search_engine.initialize()
    
    print("SentinelIQ Harvester API démarrée avec succès")


@app.on_event("shutdown")
async def shutdown_event():
    """Nettoie les ressources à l'arrêt"""
    if discovery_engine:
        await discovery_engine.close()
    if crawler:
        await crawler.close()
    if search_engine:
        await search_engine.close()
    await db_manager.close()


# ==== ENDPOINTS ARTICLES ====

@app.get("/api/v1/articles", response_model=List[ArticleResponse])
async def get_articles(
    page: int = Query(1, ge=1, description="Numéro de page"),
    limit: int = Query(20, ge=1, le=100, description="Nombre d'articles par page"),
    category: Optional[str] = Query(None, description="Filtrer par catégorie"),
    language: Optional[str] = Query(None, description="Filtrer par langue"),
    source_id: Optional[str] = Query(None, description="Filtrer par source"),
    min_quality: Optional[float] = Query(None, ge=0, le=1, description="Score de qualité minimum"),
    search: Optional[str] = Query(None, description="Recherche textuelle"),
    session=Depends(get_db_session)
):
    """Récupère la liste des articles avec pagination et filtres"""
    
    offset = (page - 1) * limit
    
    # Construction de la requête avec filtres
    query = "SELECT * FROM articles WHERE 1=1"
    params = []
    
    if category:
        query += " AND category = %s"
        params.append(category)
        
    if language:
        query += " AND language = %s"
        params.append(language)
        
    if source_id:
        query += " AND source_id = %s"
        params.append(source_id)
        
    if min_quality is not None:
        query += " AND quality_score >= %s"
        params.append(min_quality)
        
    if search:
        query += " AND (title ILIKE %s OR content ILIKE %s)"
        search_pattern = f"%{search}%"
        params.extend([search_pattern, search_pattern])
    
    query += " ORDER BY crawled_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    result = await session.execute(query, params)
    articles = result.fetchall()
    
    return [ArticleResponse.from_orm(article) for article in articles]


@app.get("/api/v1/articles/{article_id}", response_model=ArticleResponse)
async def get_article(article_id: str, session=Depends(get_db_session)):
    """Récupère un article spécifique"""
    result = await session.execute(
        "SELECT * FROM articles WHERE id = %s", (article_id,)
    )
    article = result.fetchone()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article non trouvé")
        
    return ArticleResponse.from_orm(article)


@app.get("/api/v1/search/semantic")
async def semantic_search(
    query: str = Query(..., description="Requête de recherche"),
    limit: int = Query(10, ge=1, le=50, description="Nombre de résultats"),
    threshold: float = Query(0.7, ge=0, le=1, description="Seuil de similarité"),
    category: Optional[str] = Query(None, description="Filtrer par catégorie")
):
    """Recherche sémantique dans les articles"""
    if not search_engine:
        raise HTTPException(status_code=503, detail="Moteur de recherche non disponible")
        
    results = await search_engine.search(
        query=query,
        limit=limit,
        threshold=threshold,
        category=category
    )
    
    return {
        "query": query,
        "results": results,
        "total": len(results)
    }


# ==== ENDPOINTS SOURCES ====

@app.get("/api/v1/sources", response_model=List[SourceResponse])
async def get_sources(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    active_only: bool = Query(True, description="Uniquement les sources actives"),
    category: Optional[str] = Query(None),
    session=Depends(get_db_session)
):
    """Récupère la liste des sources"""
    offset = (page - 1) * limit
    
    query = "SELECT * FROM sources WHERE 1=1"
    params = []
    
    if active_only:
        query += " AND is_active = true"
        
    if category:
        query += " AND category = %s"
        params.append(category)
        
    query += " ORDER BY quality_score DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    result = await session.execute(query, params)
    sources = result.fetchall()
    
    return [SourceResponse.from_orm(source) for source in sources]


@app.post("/api/v1/sources", response_model=SourceResponse)
async def create_source(
    source_request: CreateSourceRequest,
    session=Depends(get_db_session)
):
    """Crée une nouvelle source"""
    from urllib.parse import urlparse
    
    # Valide l'URL
    parsed_url = urlparse(source_request.url)
    if not parsed_url.scheme or not parsed_url.netloc:
        raise HTTPException(status_code=400, detail="URL invalide")
        
    # Vérifie si la source existe déjà
    existing = await session.execute(
        "SELECT id FROM sources WHERE url = %s", (source_request.url,)
    )
    
    if existing.fetchone():
        raise HTTPException(status_code=409, detail="Source déjà existante")
        
    # Crée la nouvelle source
    source = Source(
        name=source_request.name,
        url=source_request.url,
        domain=parsed_url.netloc,
        source_type=source_request.source_type,
        category=source_request.category,
        crawl_frequency=source_request.crawl_frequency or 3600,
        respect_robots_txt=source_request.respect_robots_txt
    )
    
    session.add(source)
    await session.commit()
    
    return SourceResponse.from_orm(source)


@app.get("/api/v1/sources/{source_id}", response_model=SourceResponse)
async def get_source(source_id: str, session=Depends(get_db_session)):
    """Récupère une source spécifique"""
    source = await session.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source non trouvée")
        
    return SourceResponse.from_orm(source)


@app.put("/api/v1/sources/{source_id}/toggle")
async def toggle_source(source_id: str, session=Depends(get_db_session)):
    """Active/désactive une source"""
    result = await session.execute(
        "UPDATE sources SET is_active = NOT is_active WHERE id = %s RETURNING is_active",
        (source_id,)
    )
    
    updated = result.fetchone()
    if not updated:
        raise HTTPException(status_code=404, detail="Source non trouvée")
        
    await session.commit()
    
    return {"source_id": source_id, "is_active": updated[0]}


# ==== ENDPOINTS CRAWLING ====

@app.post("/api/v1/crawl/source/{source_id}")
async def crawl_source(
    source_id: str,
    background_tasks: BackgroundTasks,
    crawl_request: Optional[CrawlRequest] = None,
    session=Depends(get_db_session)
):
    """Lance le crawling d'une source"""
    if not crawler:
        raise HTTPException(status_code=503, detail="Crawler non disponible")
        
    # Vérifie que la source existe
    source = await session.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source non trouvée")
        
    max_pages = crawl_request.max_pages if crawl_request else 100
    
    # Lance le crawl en arrière-plan
    background_tasks.add_task(
        _run_crawl_task,
        source_id,
        max_pages
    )
    
    return {
        "message": "Crawl lancé en arrière-plan",
        "source_id": source_id,
        "max_pages": max_pages
    }


async def _run_crawl_task(source_id: str, max_pages: int):
    """Tâche de crawl exécutée en arrière-plan"""
    try:
        stats = await crawler.crawl_source(source_id, max_pages)
        print(f"Crawl terminé pour {source_id}: {stats}")
    except Exception as e:
        print(f"Erreur lors du crawl de {source_id}: {e}")


@app.post("/api/v1/crawl/update-check/{source_id}")
async def update_check_source(
    source_id: str,
    background_tasks: BackgroundTasks,
    session=Depends(get_db_session)
):
    """Lance une vérification de mise à jour pour une source"""
    if not crawler:
        raise HTTPException(status_code=503, detail="Crawler non disponible")
        
    source = await session.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source non trouvée")
        
    background_tasks.add_task(_run_update_check_task, source_id)
    
    return {
        "message": "Vérification de mise à jour lancée",
        "source_id": source_id
    }


async def _run_update_check_task(source_id: str):
    """Tâche de vérification de mise à jour"""
    try:
        stats = await crawler.update_check_crawl(source_id)
        print(f"Update check terminé pour {source_id}: {stats}")
    except Exception as e:
        print(f"Erreur lors de l'update check de {source_id}: {e}")


# ==== ENDPOINTS DISCOVERY ====

@app.post("/api/v1/discovery/start")
async def start_discovery(
    background_tasks: BackgroundTasks,
    max_results: int = Query(100, ge=10, le=500, description="Nombre max de résultats")
):
    """Lance la découverte autonome de nouvelles sources"""
    if not discovery_engine:
        raise HTTPException(status_code=503, detail="Moteur de découverte non disponible")
        
    background_tasks.add_task(_run_discovery_task, max_results)
    
    return {
        "message": "Découverte lancée en arrière-plan",
        "max_results": max_results
    }


async def _run_discovery_task(max_results: int):
    """Tâche de découverte exécutée en arrière-plan"""
    try:
        candidates = await discovery_engine.discover_new_sources(max_results)
        print(f"Découverte terminée: {len(candidates)} candidats trouvés")
        
        # Crée automatiquement les meilleures sources
        created_sources = await discovery_engine.create_sources_from_discoveries(min_tech_score=0.7)
        print(f"Nouvelles sources créées: {len(created_sources)}")
        
    except Exception as e:
        print(f"Erreur lors de la découverte: {e}")


@app.get("/api/v1/discovery/results")
async def get_discovery_results(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    min_relevance: float = Query(0.5, ge=0, le=1),
    session=Depends(get_db_session)
):
    """Récupère les résultats de découverte"""
    offset = (page - 1) * limit
    
    result = await session.execute("""
        SELECT * FROM discovery_results 
        WHERE tech_relevance_score >= %s
        ORDER BY tech_relevance_score DESC 
        LIMIT %s OFFSET %s
    """, (min_relevance, limit, offset))
    
    discoveries = result.fetchall()
    
    return {
        "discoveries": [
            {
                "id": d[0],
                "search_query": d[1],
                "discovered_url": d[3],
                "domain": d[4],
                "relevance_score": d[5],
                "tech_relevance_score": d[7],
                "title": d[8],
                "is_tech_relevant": d[11],
                "discovered_at": d[14]
            }
            for d in discoveries
        ],
        "page": page,
        "limit": limit
    }


# ==== ENDPOINTS STATISTICS ====

@app.get("/api/v1/stats/sources")
async def get_sources_stats(session=Depends(get_db_session)):
    """Statistiques des sources"""
    result = await session.execute("""
        SELECT 
            COUNT(*) as total_sources,
            COUNT(CASE WHEN is_active = true THEN 1 END) as active_sources,
            COUNT(CASE WHEN last_crawled_at > NOW() - INTERVAL '24 hours' THEN 1 END) as recently_crawled,
            AVG(quality_score) as avg_quality_score,
            COUNT(DISTINCT category) as categories_count
        FROM sources
    """)
    
    stats = result.fetchone()
    
    # Statistiques par catégorie
    category_result = await session.execute("""
        SELECT category, COUNT(*) as count, AVG(quality_score) as avg_quality
        FROM sources 
        WHERE is_active = true
        GROUP BY category 
        ORDER BY count DESC
    """)
    
    categories = category_result.fetchall()
    
    return {
        "total_sources": stats[0],
        "active_sources": stats[1],
        "recently_crawled": stats[2],
        "avg_quality_score": float(stats[3]) if stats[3] else 0.0,
        "categories_count": stats[4],
        "categories": [
            {
                "name": cat[0],
                "count": cat[1],
                "avg_quality": float(cat[2])
            }
            for cat in categories
        ]
    }


@app.get("/api/v1/stats/articles")
async def get_articles_stats(session=Depends(get_db_session)):
    """Statistiques des articles"""
    result = await session.execute("""
        SELECT 
            COUNT(*) as total_articles,
            COUNT(CASE WHEN crawled_at > NOW() - INTERVAL '24 hours' THEN 1 END) as today_articles,
            COUNT(CASE WHEN crawled_at > NOW() - INTERVAL '7 days' THEN 1 END) as week_articles,
            AVG(quality_score) as avg_quality_score,
            COUNT(DISTINCT language) as languages_count
        FROM articles
    """)
    
    stats = result.fetchone()
    
    # Articles par langue
    lang_result = await session.execute("""
        SELECT language, COUNT(*) as count
        FROM articles 
        GROUP BY language 
        ORDER BY count DESC
        LIMIT 10
    """)
    
    languages = lang_result.fetchall()
    
    return {
        "total_articles": stats[0],
        "today_articles": stats[1],
        "week_articles": stats[2],
        "avg_quality_score": float(stats[3]) if stats[3] else 0.0,
        "languages_count": stats[4],
        "languages": [
            {
                "language": lang[0],
                "count": lang[1]
            }
            for lang in languages
        ]
    }


@app.get("/api/v1/system/health")
async def health_check():
    """Vérification de l'état du système"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "database": "unknown",
            "discovery_engine": "unknown",
            "crawler": "unknown",
            "search_engine": "unknown"
        }
    }
    
    # Vérifie la base de données
    try:
        async with db_manager.get_session() as session:
            await session.execute("SELECT 1")
        health_status["components"]["database"] = "healthy"
    except Exception:
        health_status["components"]["database"] = "unhealthy"
        health_status["status"] = "degraded"
        
    # Vérifie les autres composants
    health_status["components"]["discovery_engine"] = "healthy" if discovery_engine else "unavailable"
    health_status["components"]["crawler"] = "healthy" if crawler else "unavailable"
    health_status["components"]["search_engine"] = "healthy" if search_engine else "unavailable"
    
    if any(status == "unavailable" for status in health_status["components"].values()):
        health_status["status"] = "degraded"
        
    return health_status


# ==== GESTION DES ERREURS ====

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Gestionnaire global d'exceptions"""
    print(f"Erreur non gérée: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Erreur interne du serveur",
            "detail": str(exc) if settings.debug else "Une erreur est survenue"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
