"""
Crawler intelligent avec détection de changements et anti-duplication
"""
import asyncio
import aiohttp
import hashlib
import time
from typing import List, Dict, Optional, Set, Tuple, Any
from urllib.parse import urlparse, urljoin, quote_plus
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import re
from bs4 import BeautifulSoup
import robotparser
from fake_useragent import UserAgent

from ..config import settings
from ..models import Article, Source, ContentHash, CrawlJob
from ..database import db_manager
from .strategies.content_extractor import ContentExtractor
from .strategies.anti_duplication import AntiDuplicationEngine
from .utils.rate_limiter import RateLimiter


@dataclass
class CrawlResult:
    """Résultat d'un crawl individuel"""
    url: str
    success: bool
    status_code: int = 0
    content: str = ""
    title: str = ""
    author: str = ""
    published_at: Optional[datetime] = None
    content_hash: str = ""
    is_duplicate: bool = False
    error_message: str = ""
    processing_time: float = 0.0


class SmartCrawler:
    """
    Crawler intelligent qui :
    1. Respecte les robots.txt et rate limits
    2. Détecte les changements de contenu
    3. Évite les duplicatas intelligemment
    4. S'adapte selon le type de contenu
    5. Gère les sites JS avec Playwright si nécessaire
    """
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.content_extractor = ContentExtractor()
        self.anti_dup_engine = AntiDuplicationEngine()
        self.rate_limiter = RateLimiter()
        self.user_agent = UserAgent()
        self.robots_cache: Dict[str, robotparser.RobotFileParser] = {}
        
    async def initialize(self):
        """Initialise le crawler"""
        # Configuration avancée de la session HTTP
        connector = aiohttp.TCPConnector(
            limit=settings.crawler_max_workers,
            limit_per_host=10,
            ttl_dns_cache=300,
            use_dns_cache=True,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(
            total=settings.crawler_request_timeout,
            connect=10,
            sock_read=20
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': self.user_agent.random,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
        )
        
        await self.content_extractor.initialize()
        await self.anti_dup_engine.initialize()
        
    async def close(self):
        """Ferme les ressources"""
        if self.session:
            await self.session.close()
        await self.content_extractor.close()
        await self.anti_dup_engine.close()
        
    async def crawl_source(self, source_id: str, max_pages: int = 100) -> Dict[str, Any]:
        """
        Crawle une source complète de manière intelligente
        
        Args:
            source_id: ID de la source à crawler
            max_pages: Nombre maximum de pages à crawler
            
        Returns:
            Statistiques du crawl
        """
        start_time = time.time()
        stats = {
            'pages_crawled': 0,
            'pages_processed': 0,
            'pages_failed': 0,
            'new_articles': 0,
            'updated_articles': 0,
            'duplicates_found': 0,
            'errors': []
        }
        
        try:
            # Récupère les informations de la source
            async with db_manager.get_session() as session:
                source = await session.get(Source, source_id)
                if not source:
                    raise ValueError(f"Source {source_id} non trouvée")
                    
            # Vérifie robots.txt
            if source.respect_robots_txt:
                robots_allowed = await self._check_robots_txt(source.domain, source.url)
                if not robots_allowed:
                    stats['errors'].append("Bloqué par robots.txt")
                    return stats
                    
            # Découvre les URLs à crawler
            urls_to_crawl = await self._discover_urls(source, max_pages)
            
            # Crawl parallèle avec contrôle de débit
            semaphore = asyncio.Semaphore(min(10, settings.crawler_max_workers))
            tasks = []
            
            for url in urls_to_crawl:
                task = self._crawl_single_url_with_semaphore(semaphore, url, source)
                tasks.append(task)
                
            # Exécute les tâches par batch pour éviter la surcharge
            batch_size = 20
            for i in range(0, len(tasks), batch_size):
                batch = tasks[i:i + batch_size]
                results = await asyncio.gather(*batch, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, CrawlResult):
                        stats['pages_crawled'] += 1
                        
                        if result.success:
                            if result.is_duplicate:
                                stats['duplicates_found'] += 1
                            else:
                                # Traite le contenu nouveau/mis à jour
                                article_created = await self._process_crawl_result(result, source)
                                if article_created:
                                    stats['new_articles'] += 1
                                    stats['pages_processed'] += 1
                        else:
                            stats['pages_failed'] += 1
                            stats['errors'].append(f"{result.url}: {result.error_message}")
                    elif isinstance(result, Exception):
                        stats['pages_failed'] += 1
                        stats['errors'].append(str(result))
                        
                # Pause entre les batches
                await asyncio.sleep(1)
                
            # Met à jour les statistiques de la source
            await self._update_source_stats(source, stats)
            
        except Exception as e:
            stats['errors'].append(f"Erreur générale: {str(e)}")
            
        stats['duration'] = time.time() - start_time
        return stats
        
    async def _check_robots_txt(self, domain: str, url: str) -> bool:
        """Vérifie si le crawling est autorisé par robots.txt"""
        if domain in self.robots_cache:
            robots = self.robots_cache[domain]
        else:
            robots = robotparser.RobotFileParser()
            robots_url = f"https://{domain}/robots.txt"
            
            try:
                async with self.session.get(robots_url) as response:
                    if response.status == 200:
                        robots_content = await response.text()
                        robots.set_url(robots_url)
                        robots.feed(robots_content)
                        
                self.robots_cache[domain] = robots
            except Exception:
                # Si robots.txt n'est pas accessible, on autorise par défaut
                return True
                
        user_agent = self.session.headers.get('User-Agent', '*')
        return robots.can_fetch(user_agent, url)
        
    async def _discover_urls(self, source: Source, max_pages: int) -> List[str]:
        """
        Découvre les URLs à crawler pour une source
        """
        urls = set()
        
        # Ajoute l'URL principale
        urls.add(source.url)
        
        # Tente de découvrir via sitemap
        sitemap_urls = await self._discover_from_sitemap(source)
        urls.update(sitemap_urls[:max_pages // 2])
        
        # Tente de découvrir via RSS feed
        rss_urls = await self._discover_from_rss(source)
        urls.update(rss_urls[:max_pages // 4])
        
        # Découverte via crawling de liens (si nécessaire)
        if len(urls) < max_pages:
            link_urls = await self._discover_from_links(source.url, max_pages - len(urls))
            urls.update(link_urls)
            
        return list(urls)[:max_pages]
        
    async def _discover_from_sitemap(self, source: Source) -> List[str]:
        """Découvre les URLs via le sitemap"""
        sitemap_urls = []
        
        # URLs de sitemap communes
        possible_sitemaps = [
            f"https://{source.domain}/sitemap.xml",
            f"https://{source.domain}/sitemap_index.xml",
            f"https://{source.domain}/sitemaps.xml",
            source.sitemap_url
        ]
        
        for sitemap_url in possible_sitemaps:
            if sitemap_url:
                try:
                    async with self.session.get(sitemap_url) as response:
                        if response.status == 200:
                            content = await response.text()
                            urls = self._parse_sitemap(content)
                            sitemap_urls.extend(urls)
                            break  # Prend le premier sitemap trouvé
                except Exception:
                    continue
                    
        return sitemap_urls
        
    def _parse_sitemap(self, sitemap_content: str) -> List[str]:
        """Parse un sitemap XML"""
        urls = []
        
        try:
            from xml.etree import ElementTree as ET
            root = ET.fromstring(sitemap_content)
            
            # Cherche les URLs dans le sitemap
            for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                loc_elem = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                if loc_elem is not None and loc_elem.text:
                    urls.append(loc_elem.text)
                    
        except Exception as e:
            print(f"Erreur lors du parsing du sitemap: {e}")
            
        return urls
        
    async def _discover_from_rss(self, source: Source) -> List[str]:
        """Découvre les URLs via le flux RSS"""
        rss_urls = []
        
        # URLs de RSS communes
        possible_feeds = [
            f"https://{source.domain}/feed",
            f"https://{source.domain}/rss",
            f"https://{source.domain}/feed.xml",
            f"https://{source.domain}/rss.xml",
            source.rss_feed_url
        ]
        
        for feed_url in possible_feeds:
            if feed_url:
                try:
                    async with self.session.get(feed_url) as response:
                        if response.status == 200:
                            content = await response.text()
                            urls = self._parse_rss_feed(content)
                            rss_urls.extend(urls)
                            break  # Prend le premier feed trouvé
                except Exception:
                    continue
                    
        return rss_urls
        
    def _parse_rss_feed(self, feed_content: str) -> List[str]:
        """Parse un flux RSS/Atom"""
        urls = []
        
        try:
            import feedparser
            feed = feedparser.parse(feed_content)
            
            for entry in feed.entries:
                if hasattr(entry, 'link'):
                    urls.append(entry.link)
                    
        except Exception as e:
            print(f"Erreur lors du parsing du feed RSS: {e}")
            
        return urls
        
    async def _discover_from_links(self, base_url: str, max_urls: int) -> List[str]:
        """Découvre les URLs en suivant les liens depuis la page principale"""
        discovered_urls = set()
        
        try:
            async with self.session.get(base_url) as response:
                if response.status == 200:
                    content = await response.text()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    base_domain = urlparse(base_url).netloc
                    
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        absolute_url = urljoin(base_url, href)
                        
                        # Filtre les liens du même domaine
                        if urlparse(absolute_url).netloc == base_domain:
                            discovered_urls.add(absolute_url)
                            
                        if len(discovered_urls) >= max_urls:
                            break
                            
        except Exception as e:
            print(f"Erreur lors de la découverte de liens: {e}")
            
        return list(discovered_urls)
        
    async def _crawl_single_url_with_semaphore(self, semaphore: asyncio.Semaphore, 
                                             url: str, source: Source) -> CrawlResult:
        """Crawle une URL avec contrôle de concurrence"""
        async with semaphore:
            # Applique le rate limiting
            await self.rate_limiter.wait_if_needed(source.domain)
            
            return await self._crawl_single_url(url, source)
            
    async def _crawl_single_url(self, url: str, source: Source) -> CrawlResult:
        """Crawle une URL individuelle"""
        start_time = time.time()
        result = CrawlResult(url=url, success=False)
        
        try:
            # Vérifie d'abord si on a besoin de crawler (vérification ETag/Last-Modified)
            should_crawl = await self._should_crawl_url(url)
            if not should_crawl:
                result.success = True
                result.is_duplicate = True
                return result
                
            # Change le User-Agent pour chaque requête
            headers = {
                'User-Agent': self.user_agent.random,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
            
            async with self.session.get(url, headers=headers) as response:
                result.status_code = response.status
                
                if response.status == 200:
                    content = await response.text()
                    
                    # Extrait le contenu structuré
                    extracted = await self.content_extractor.extract_content(content, url)
                    
                    if extracted['content']:
                        result.content = extracted['content']
                        result.title = extracted['title']
                        result.author = extracted['author']
                        result.published_at = extracted['published_at']
                        
                        # Calcule le hash pour la détection de doublons
                        result.content_hash = self._calculate_content_hash(result.content)
                        
                        # Vérifie si c'est un doublon
                        result.is_duplicate = await self.anti_dup_engine.is_duplicate(
                            result.content_hash, url
                        )
                        
                        result.success = True
                    else:
                        result.error_message = "Impossible d'extraire le contenu"
                else:
                    result.error_message = f"HTTP {response.status}"
                    
        except asyncio.TimeoutError:
            result.error_message = "Timeout"
        except Exception as e:
            result.error_message = str(e)
            
        result.processing_time = time.time() - start_time
        return result
        
    async def _should_crawl_url(self, url: str) -> bool:
        """
        Détermine si une URL doit être crawlée basé sur les métadonnées
        (ETag, Last-Modified, etc.)
        """
        try:
            # Fait une requête HEAD pour vérifier les métadonnées
            async with self.session.head(url) as response:
                if response.status != 200:
                    return True  # Tente le crawl complet si HEAD échoue
                    
                # Vérifie les headers de cache
                etag = response.headers.get('ETag')
                last_modified = response.headers.get('Last-Modified')
                
                if etag or last_modified:
                    # Vérifie si on a déjà ces métadonnées en base
                    return await self._check_content_freshness(url, etag, last_modified)
                    
        except Exception:
            pass
            
        # Par défaut, crawle si on ne peut pas déterminer
        return True
        
    async def _check_content_freshness(self, url: str, etag: Optional[str], 
                                     last_modified: Optional[str]) -> bool:
        """Vérifie si le contenu a changé depuis le dernier crawl"""
        async with db_manager.get_session() as session:
            # Requête pour trouver l'article existant
            result = await session.execute("""
                SELECT etag, last_modified FROM articles 
                WHERE url = %s 
                ORDER BY crawled_at DESC 
                LIMIT 1
            """, (url,))
            
            existing = result.fetchone()
            
            if existing:
                stored_etag, stored_last_modified = existing
                
                # Compare les métadonnées
                if etag and stored_etag == etag:
                    return False  # Pas de changement
                    
                if last_modified and stored_last_modified == last_modified:
                    return False  # Pas de changement
                    
        return True  # Nouveau contenu ou pas de métadonnées stockées
        
    def _calculate_content_hash(self, content: str) -> str:
        """Calcule un hash du contenu pour la détection de doublons"""
        # Normalise le contenu avant le hash
        normalized = re.sub(r'\s+', ' ', content.strip().lower())
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
        
    async def _process_crawl_result(self, result: CrawlResult, source: Source) -> bool:
        """
        Traite le résultat d'un crawl et crée/met à jour l'article
        
        Returns:
            True si un nouvel article a été créé, False sinon
        """
        try:
            async with db_manager.get_session() as session:
                # Vérifie si l'article existe déjà
                existing_result = await session.execute("""
                    SELECT id, content_hash FROM articles 
                    WHERE url = %s
                """, (result.url,))
                
                existing = existing_result.fetchone()
                
                if existing:
                    existing_id, existing_hash = existing
                    
                    # Met à jour si le contenu a changé
                    if existing_hash != result.content_hash:
                        await session.execute("""
                            UPDATE articles 
                            SET content = %s, content_hash = %s, 
                                title = %s, author = %s, published_at = %s,
                                updated_at = NOW()
                            WHERE id = %s
                        """, (
                            result.content, result.content_hash,
                            result.title, result.author, result.published_at,
                            existing_id
                        ))
                        return False  # Article mis à jour, pas nouveau
                else:
                    # Crée un nouvel article
                    article = Article(
                        source_id=source.id,
                        title=result.title,
                        url=result.url,
                        content=result.content,
                        content_hash=result.content_hash,
                        author=result.author,
                        published_at=result.published_at,
                        language=self._detect_language(result.content),
                        word_count=len(result.content.split()),
                        quality_score=self._calculate_quality_score(result),
                        http_status=result.status_code
                    )
                    
                    session.add(article)
                    await session.commit()
                    
                    # Enregistre le hash pour la déduplication
                    await self.anti_dup_engine.register_content_hash(
                        result.content_hash, result.url, article.id
                    )
                    
                    return True  # Nouvel article créé
                    
        except Exception as e:
            print(f"Erreur lors du traitement de {result.url}: {e}")
            return False
            
        return False
        
    def _detect_language(self, content: str) -> str:
        """Détecte la langue du contenu"""
        try:
            from langdetect import detect
            detected = detect(content[:1000])  # Analyse les 1000 premiers caractères
            
            if detected in settings.supported_languages:
                return detected
                
        except Exception:
            pass
            
        return settings.default_language
        
    def _calculate_quality_score(self, result: CrawlResult) -> float:
        """Calcule un score de qualité pour l'article"""
        score = 0.5  # Score de base
        
        # Facteurs positifs
        if len(result.content) > 1000:
            score += 0.1
            
        if result.title and len(result.title) > 10:
            score += 0.1
            
        if result.author:
            score += 0.1
            
        if result.published_at:
            score += 0.1
            
        # Facteurs de contenu technique
        tech_indicators = ['code', 'function', 'class', 'algorithm', 'tutorial']
        content_lower = result.content.lower()
        
        for indicator in tech_indicators:
            if indicator in content_lower:
                score += 0.05
                
        return min(score, 1.0)
        
    async def _update_source_stats(self, source: Source, stats: Dict[str, Any]):
        """Met à jour les statistiques de la source"""
        async with db_manager.get_session() as session:
            await session.execute("""
                UPDATE sources 
                SET last_crawled_at = NOW(),
                    crawl_count = crawl_count + 1,
                    error_count = error_count + %s
                WHERE id = %s
            """, (stats['pages_failed'], source.id))
            
            await session.commit()
            
    async def update_check_crawl(self, source_id: str) -> Dict[str, Any]:
        """
        Effectue un crawl de vérification de mises à jour (plus rapide)
        Vérifie seulement les pages récemment modifiées
        """
        stats = {
            'pages_checked': 0,
            'updates_found': 0,
            'errors': []
        }
        
        try:
            async with db_manager.get_session() as session:
                source = await session.get(Source, source_id)
                if not source:
                    raise ValueError(f"Source {source_id} non trouvée")
                    
                # Récupère les articles récents pour vérification
                result = await session.execute("""
                    SELECT url, etag, last_modified 
                    FROM articles 
                    WHERE source_id = %s 
                      AND crawled_at > NOW() - INTERVAL '7 days'
                    ORDER BY crawled_at DESC 
                    LIMIT 50
                """, (source_id,))
                
                recent_articles = result.fetchall()
                
                # Vérifie chaque article pour des mises à jour
                for url, stored_etag, stored_last_modified in recent_articles:
                    stats['pages_checked'] += 1
                    
                    if await self._check_content_freshness(url, stored_etag, stored_last_modified):
                        # Contenu mis à jour, lance un crawl complet de cette page
                        crawl_result = await self._crawl_single_url(url, source)
                        if crawl_result.success and not crawl_result.is_duplicate:
                            await self._process_crawl_result(crawl_result, source)
                            stats['updates_found'] += 1
                            
        except Exception as e:
            stats['errors'].append(str(e))
            
        return stats
