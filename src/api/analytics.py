"""
Service d'analytics et de métriques pour SentinelIQ
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio

from ..database import db_manager
from ..models import Article, Source, CrawlJob, SystemMetrics


@dataclass
class AnalyticsMetrics:
    """Structure des métriques analytics"""
    total_articles: int
    articles_today: int
    articles_this_week: int
    articles_this_month: int
    avg_quality_score: float
    top_categories: List[Dict[str, Any]]
    top_sources: List[Dict[str, Any]]
    crawl_success_rate: float
    system_health: Dict[str, Any]


class AnalyticsService:
    """
    Service d'analytics pour fournir des insights sur le système
    """
    
    def __init__(self):
        pass
        
    async def get_dashboard_metrics(self) -> AnalyticsMetrics:
        """
        Récupère les métriques principales pour le dashboard
        
        Returns:
            AnalyticsMetrics: Métriques complètes du système
        """
        async with db_manager.get_session() as session:
            # Calcul des périodes
            now = datetime.now()
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)
            
            # Total d'articles
            total_result = await session.execute(
                "SELECT COUNT(*) FROM articles"
            )
            total_articles = total_result.scalar()
            
            # Articles aujourd'hui
            today_result = await session.execute(
                "SELECT COUNT(*) FROM articles WHERE crawled_at >= %s",
                (today,)
            )
            articles_today = today_result.scalar()
            
            # Articles cette semaine
            week_result = await session.execute(
                "SELECT COUNT(*) FROM articles WHERE crawled_at >= %s",
                (week_ago,)
            )
            articles_this_week = week_result.scalar()
            
            # Articles ce mois
            month_result = await session.execute(
                "SELECT COUNT(*) FROM articles WHERE crawled_at >= %s",
                (month_ago,)
            )
            articles_this_month = month_result.scalar()
            
            # Score qualité moyen
            quality_result = await session.execute(
                "SELECT AVG(quality_score) FROM articles WHERE quality_score IS NOT NULL"
            )
            avg_quality_score = quality_result.scalar() or 0.0
            
            # Top catégories
            top_categories = await self._get_top_categories(session, limit=10)
            
            # Top sources
            top_sources = await self._get_top_sources(session, limit=10)
            
            # Taux de succès du crawling
            crawl_success_rate = await self._get_crawl_success_rate(session)
            
            # Santé du système
            system_health = await self._get_system_health(session)
            
            return AnalyticsMetrics(
                total_articles=total_articles,
                articles_today=articles_today,
                articles_this_week=articles_this_week,
                articles_this_month=articles_this_month,
                avg_quality_score=round(avg_quality_score, 2),
                top_categories=top_categories,
                top_sources=top_sources,
                crawl_success_rate=crawl_success_rate,
                system_health=system_health
            )
            
    async def _get_top_categories(self, session, limit: int = 10) -> List[Dict[str, Any]]:
        """Récupère les top catégories par nombre d'articles"""
        result = await session.execute("""
            SELECT 
                category,
                COUNT(*) as article_count,
                AVG(quality_score) as avg_quality,
                COUNT(CASE WHEN crawled_at >= NOW() - INTERVAL '7 days' THEN 1 END) as recent_count
            FROM articles 
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY article_count DESC
            LIMIT %s
        """, (str(limit),))
        
        categories = []
        for row in result.fetchall():
            categories.append({
                "category": row[0],
                "article_count": row[1],
                "avg_quality": round(row[2] or 0, 2),
                "recent_count": row[3],
                "growth_rate": self._calculate_growth_rate(row[1], row[3])
            })
            
        return categories
        
    async def _get_top_sources(self, session, limit: int = 10) -> List[Dict[str, Any]]:
        """Récupère les top sources par nombre d'articles"""
        result = await session.execute("""
            SELECT 
                s.name,
                s.base_url,
                COUNT(a.id) as article_count,
                AVG(a.quality_score) as avg_quality,
                s.trust_score,
                s.is_active,
                COUNT(CASE WHEN a.crawled_at >= NOW() - INTERVAL '7 days' THEN 1 END) as recent_count
            FROM sources s
            LEFT JOIN articles a ON s.id = a.source_id
            GROUP BY s.id, s.name, s.base_url, s.trust_score, s.is_active
            ORDER BY article_count DESC
            LIMIT %s
        """, (str(limit),))
        
        sources = []
        for row in result.fetchall():
            sources.append({
                "name": row[0],
                "base_url": row[1],
                "article_count": row[2],
                "avg_quality": round(row[3] or 0, 2),
                "trust_score": round(row[4] or 0, 2),
                "is_active": row[5],
                "recent_count": row[6],
                "growth_rate": self._calculate_growth_rate(row[2], row[6])
            })
            
        return sources
        
    async def _get_crawl_success_rate(self, session) -> float:
        """Calcule le taux de succès du crawling"""
        result = await session.execute("""
            SELECT 
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful,
                COUNT(*) as total
            FROM crawl_jobs
            WHERE started_at >= NOW() - INTERVAL '24 hours'
        """)
        
        row = result.fetchone()
        if row and row[1] > 0:
            return round((row[0] / row[1]) * 100, 2)
        return 0.0
        
    async def _get_system_health(self, session) -> Dict[str, Any]:
        """Évalue la santé du système"""
        # Métriques de performance récentes
        metrics_result = await session.execute("""
            SELECT 
                AVG(cpu_usage),
                AVG(memory_usage),
                AVG(disk_usage),
                COUNT(*)
            FROM system_metrics
            WHERE recorded_at >= NOW() - INTERVAL '1 hour'
        """)
        
        metrics_row = metrics_result.fetchone()
        
        # Sources actives
        active_sources_result = await session.execute(
            "SELECT COUNT(*) FROM sources WHERE is_active = true"
        )
        active_sources = active_sources_result.scalar()
        
        # Jobs en cours
        running_jobs_result = await session.execute(
            "SELECT COUNT(*) FROM crawl_jobs WHERE status = 'running'"
        )
        running_jobs = running_jobs_result.scalar()
        
        # Calcul du score de santé
        health_score = 100
        
        if metrics_row and metrics_row[3] > 0:  # Si on a des métriques
            cpu_avg = metrics_row[0] or 0
            memory_avg = metrics_row[1] or 0
            disk_avg = metrics_row[2] or 0
            
            # Pénalités basées sur l'utilisation des ressources
            if cpu_avg > 80:
                health_score -= 20
            elif cpu_avg > 60:
                health_score -= 10
                
            if memory_avg > 90:
                health_score -= 20
            elif memory_avg > 70:
                health_score -= 10
                
            if disk_avg > 90:
                health_score -= 30
            elif disk_avg > 80:
                health_score -= 15
        else:
            # Pas de métriques récentes
            health_score -= 10
            
        return {
            "health_score": max(0, health_score),
            "status": self._get_health_status(health_score),
            "active_sources": active_sources,
            "running_jobs": running_jobs,
            "cpu_usage": round(metrics_row[0] or 0, 1) if metrics_row else None,
            "memory_usage": round(metrics_row[1] or 0, 1) if metrics_row else None,
            "disk_usage": round(metrics_row[2] or 0, 1) if metrics_row else None
        }
        
    def _calculate_growth_rate(self, total: int, recent: int) -> float:
        """Calcule le taux de croissance approximatif"""
        if total == 0:
            return 0.0
        # Approximation simple : (articles récents / total) * 100
        return round((recent / max(total, 1)) * 100, 1)
        
    def _get_health_status(self, score: int) -> str:
        """Détermine le statut de santé basé sur le score"""
        if score >= 90:
            return "excellent"
        elif score >= 70:
            return "good"
        elif score >= 50:
            return "warning"
        else:
            return "critical"
            
    async def get_content_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        Analyse détaillée du contenu sur une période donnée
        
        Args:
            days: Nombre de jours à analyser
            
        Returns:
            Analyse complète du contenu
        """
        async with db_manager.get_session() as session:
            start_date = datetime.now() - timedelta(days=days)
            
            # Distribution de qualité
            quality_dist_result = await session.execute("""
                SELECT 
                    CASE 
                        WHEN quality_score >= 0.8 THEN 'high'
                        WHEN quality_score >= 0.6 THEN 'medium'
                        WHEN quality_score >= 0.4 THEN 'low'
                        ELSE 'very_low'
                    END as quality_bucket,
                    COUNT(*) as count
                FROM articles
                WHERE crawled_at >= %s AND quality_score IS NOT NULL
                GROUP BY quality_bucket
                ORDER BY quality_bucket
            """, (start_date,))
            
            quality_distribution = {}
            for row in quality_dist_result.fetchall():
                quality_distribution[row[0]] = row[1]
                
            # Tendances temporelles
            temporal_result = await session.execute("""
                SELECT 
                    DATE(crawled_at) as date,
                    COUNT(*) as article_count,
                    AVG(quality_score) as avg_quality
                FROM articles
                WHERE crawled_at >= %s
                GROUP BY DATE(crawled_at)
                ORDER BY date
            """, (start_date,))
            
            temporal_trends = []
            for row in temporal_result.fetchall():
                temporal_trends.append({
                    "date": row[0].isoformat(),
                    "article_count": row[1],
                    "avg_quality": round(row[2] or 0, 2)
                })
                
            # Top mots-clés
            keywords_result = await session.execute("""
                SELECT 
                    unnest(tags) as tag,
                    COUNT(*) as frequency
                FROM articles
                WHERE crawled_at >= %s AND tags IS NOT NULL
                GROUP BY tag
                ORDER BY frequency DESC
                LIMIT 20
            """, (start_date,))
            
            top_keywords = []
            for row in keywords_result.fetchall():
                top_keywords.append({
                    "keyword": row[0],
                    "frequency": row[1]
                })
                
            # Analyse de duplication
            duplication_result = await session.execute("""
                SELECT 
                    COUNT(*) as total_articles,
                    COUNT(DISTINCT content_hash) as unique_content,
                    COUNT(*) - COUNT(DISTINCT content_hash) as duplicates
                FROM articles
                WHERE crawled_at >= %s
            """, (start_date,))
            
            dup_row = duplication_result.fetchone()
            duplication_stats = {
                "total_articles": dup_row[0],
                "unique_content": dup_row[1],
                "duplicates": dup_row[2],
                "duplication_rate": round((dup_row[2] / max(dup_row[0], 1)) * 100, 2)
            }
            
            return {
                "period_days": days,
                "quality_distribution": quality_distribution,
                "temporal_trends": temporal_trends,
                "top_keywords": top_keywords,
                "duplication_stats": duplication_stats
            }
            
    async def get_source_performance(self, source_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyse de performance des sources
        
        Args:
            source_id: ID de source spécifique (optionnel)
            
        Returns:
            Analyse de performance des sources
        """
        async with db_manager.get_session() as session:
            base_query = """
                SELECT 
                    s.id,
                    s.name,
                    s.base_url,
                    s.trust_score,
                    COUNT(a.id) as total_articles,
                    AVG(a.quality_score) as avg_quality,
                    COUNT(CASE WHEN a.crawled_at >= NOW() - INTERVAL '7 days' THEN 1 END) as recent_articles,
                    COUNT(CASE WHEN a.crawled_at >= NOW() - INTERVAL '24 hours' THEN 1 END) as today_articles,
                    MAX(a.crawled_at) as last_crawl,
                    COUNT(DISTINCT a.category) as category_diversity
                FROM sources s
                LEFT JOIN articles a ON s.id = a.source_id
            """
            
            params = []
            if source_id:
                base_query += " WHERE s.id = %s"
                params.append(source_id)
                
            base_query += """
                GROUP BY s.id, s.name, s.base_url, s.trust_score
                ORDER BY total_articles DESC
            """
            
            result = await session.execute(base_query, params)
            
            sources_performance = []
            for row in result.fetchall():
                # Calcul de score de performance
                performance_score = self._calculate_performance_score(
                    total_articles=row[4],
                    avg_quality=row[5] or 0,
                    recent_activity=row[6],
                    trust_score=row[3] or 0
                )
                
                sources_performance.append({
                    "source_id": row[0],
                    "name": row[1],
                    "base_url": row[2],
                    "trust_score": round(row[3] or 0, 2),
                    "total_articles": row[4],
                    "avg_quality": round(row[5] or 0, 2),
                    "recent_articles": row[6],
                    "today_articles": row[7],
                    "last_crawl": row[8].isoformat() if row[8] else None,
                    "category_diversity": row[9],
                    "performance_score": performance_score
                })
                
            # Si demande pour une source spécifique, ajouter plus de détails
            if source_id and sources_performance:
                source_details = await self._get_source_detailed_stats(session, source_id)
                sources_performance[0].update(source_details)
                
            return {
                "sources": sources_performance,
                "total_sources": len(sources_performance)
            }
            
    def _calculate_performance_score(self, total_articles: int, avg_quality: float, 
                                   recent_activity: int, trust_score: float) -> float:
        """Calcule un score de performance pour une source"""
        score = 0
        
        # Volume de contenu (30%)
        if total_articles > 100:
            score += 30
        elif total_articles > 50:
            score += 20
        elif total_articles > 10:
            score += 10
            
        # Qualité moyenne (40%)
        score += avg_quality * 40
        
        # Activité récente (20%)
        if recent_activity > 10:
            score += 20
        elif recent_activity > 5:
            score += 15
        elif recent_activity > 0:
            score += 10
            
        # Score de confiance (10%)
        score += trust_score * 10
        
        return round(min(100, score), 1)
        
    async def _get_source_detailed_stats(self, session, source_id: str) -> Dict[str, Any]:
        """Récupère des statistiques détaillées pour une source spécifique"""
        # Distribution temporelle
        temporal_result = await session.execute("""
            SELECT 
                DATE(crawled_at) as date,
                COUNT(*) as count
            FROM articles
            WHERE source_id = %s AND crawled_at >= NOW() - INTERVAL '30 days'
            GROUP BY DATE(crawled_at)
            ORDER BY date
        """, (source_id,))
        
        temporal_distribution = []
        for row in temporal_result.fetchall():
            temporal_distribution.append({
                "date": row[0].isoformat(),
                "article_count": row[1]
            })
            
        # Distribution des catégories
        category_result = await session.execute("""
            SELECT 
                category,
                COUNT(*) as count,
                AVG(quality_score) as avg_quality
            FROM articles
            WHERE source_id = %s AND category IS NOT NULL
            GROUP BY category
            ORDER BY count DESC
        """, (source_id,))
        
        category_distribution = []
        for row in category_result.fetchall():
            category_distribution.append({
                "category": row[0],
                "article_count": row[1],
                "avg_quality": round(row[2] or 0, 2)
            })
            
        return {
            "temporal_distribution": temporal_distribution,
            "category_distribution": category_distribution
        }
        
    async def generate_insights(self) -> List[Dict[str, Any]]:
        """
        Génère des insights automatiques basés sur les données
        
        Returns:
            Liste d'insights avec recommandations
        """
        insights = []
        
        async with db_manager.get_session() as session:
            # Insight 1: Sources sous-performantes
            underperforming_result = await session.execute("""
                SELECT 
                    s.name,
                    COUNT(a.id) as article_count,
                    AVG(a.quality_score) as avg_quality
                FROM sources s
                LEFT JOIN articles a ON s.id = a.source_id
                WHERE s.is_active = true
                GROUP BY s.id, s.name
                HAVING COUNT(a.id) < 10 OR AVG(a.quality_score) < 0.4
                ORDER BY avg_quality ASC
            """)
            
            underperforming = underperforming_result.fetchall()
            if underperforming:
                insights.append({
                    "type": "warning",
                    "title": "Sources sous-performantes détectées",
                    "description": f"{len(underperforming)} sources produisent peu de contenu ou du contenu de faible qualité",
                    "recommendation": "Considérer la désactivation ou l'optimisation de ces sources",
                    "data": [{"name": row[0], "articles": row[1], "quality": round(row[2] or 0, 2)} for row in underperforming[:5]]
                })
                
            # Insight 2: Catégories émergentes
            emerging_result = await session.execute("""
                SELECT 
                    category,
                    COUNT(CASE WHEN crawled_at >= NOW() - INTERVAL '7 days' THEN 1 END) as recent_count,
                    COUNT(CASE WHEN crawled_at >= NOW() - INTERVAL '30 days' AND crawled_at < NOW() - INTERVAL '7 days' THEN 1 END) as previous_count
                FROM articles
                WHERE category IS NOT NULL
                GROUP BY category
                HAVING COUNT(CASE WHEN crawled_at >= NOW() - INTERVAL '7 days' THEN 1 END) > 5
                ORDER BY recent_count DESC
            """)
            
            emerging_categories = []
            for row in emerging_result.fetchall():
                if row[2] > 0:  # Évite division par zéro
                    growth = ((row[1] - row[2]) / row[2]) * 100
                    if growth > 50:  # Croissance de plus de 50%
                        emerging_categories.append({
                            "category": row[0],
                            "recent_count": row[1],
                            "growth_rate": round(growth, 1)
                        })
                        
            if emerging_categories:
                insights.append({
                    "type": "info",
                    "title": "Catégories en forte croissance",
                    "description": f"{len(emerging_categories)} catégories montrent une forte activité récente",
                    "recommendation": "Considérer l'ajout de sources spécialisées dans ces domaines",
                    "data": emerging_categories[:3]
                })
                
            # Insight 3: Efficacité du crawling
            crawl_efficiency_result = await session.execute("""
                SELECT 
                    AVG(CASE WHEN status = 'completed' THEN 1.0 ELSE 0.0 END) as success_rate,
                    COUNT(*) as total_jobs
                FROM crawl_jobs
                WHERE started_at >= NOW() - INTERVAL '24 hours'
            """)
            
            efficiency_row = crawl_efficiency_result.fetchone()
            if efficiency_row and efficiency_row[1] > 0:
                success_rate = efficiency_row[0] * 100
                if success_rate < 80:
                    insights.append({
                        "type": "error",
                        "title": "Efficacité de crawling réduite",
                        "description": f"Taux de succès de {success_rate:.1f}% sur les dernières 24h",
                        "recommendation": "Vérifier la configuration des sources et les erreurs de crawling",
                        "data": {"success_rate": round(success_rate, 1), "total_jobs": efficiency_row[1]}
                    })
                    
        return insights
