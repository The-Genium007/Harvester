"""
Discovery Engine - Moteur de découverte autonome de sources
"""
import asyncio
import aiohttp
import hashlib
import time
from typing import List, Dict, Optional, Set, Tuple
from urllib.parse import urlparse, urljoin, quote_plus
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import re

from ..config import settings
from ..models import DiscoveryResult, Source
from ..database import db_manager
from .analyzers.relevance import RelevanceAnalyzer
from .analyzers.quality import QualityAnalyzer
from .search_engines import SearchEngineFactory


@dataclass
class DiscoveryCandidate:
    """Candidat découvert pour évaluation"""
    url: str
    title: str
    description: str
    source_engine: str
    search_query: str
    domain: str
    relevance_score: float = 0.0
    quality_score: float = 0.0
    tech_relevance_score: float = 0.0


class AutonomousDiscovery:
    """
    Moteur de découverte autonome qui :
    1. Génère des requêtes de recherche intelligentes
    2. Utilise plusieurs moteurs de recherche
    3. Évalue la pertinence technique des résultats
    4. Découvre de nouvelles sources via analyse de liens
    5. Apprend et s'améliore continuellement
    """
    
    def __init__(self):
        self.search_factory = SearchEngineFactory()
        self.relevance_analyzer = RelevanceAnalyzer()
        self.quality_analyzer = QualityAnalyzer()
        self.discovered_domains: Set[str] = set()
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def initialize(self):
        """Initialise le moteur de découverte"""
        await self._load_existing_domains()
        
        # Configuration de la session HTTP
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=10,
            ttl_dns_cache=300,
            use_dns_cache=True
        )
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'SentinelIQ-Harvester/1.0 (+https://sentineliq.tech/bot)'
            }
        )
        
    async def close(self):
        """Ferme les ressources"""
        if self.session:
            await self.session.close()
            
    async def _load_existing_domains(self):
        """Charge les domaines déjà connus"""
        async with db_manager.get_session() as session:
            # Requête pour obtenir tous les domaines existants
            result = await session.execute(
                "SELECT DISTINCT domain FROM sources WHERE is_active = true"
            )
            self.discovered_domains = {row[0] for row in result.fetchall()}
            
    async def discover_new_sources(self, max_results: int = 100) -> List[DiscoveryCandidate]:
        """
        Lance une session de découverte complète
        """
        candidates = []
        
        # 1. Génération de requêtes intelligentes
        search_queries = await self._generate_smart_queries()
        
        # 2. Recherche multi-moteurs
        for query in search_queries[:10]:  # Limite pour éviter les abus
            engine_results = await self._search_multiple_engines(query)
            candidates.extend(engine_results)
            
            # Pause entre les requêtes
            await asyncio.sleep(2)
            
        # 3. Découverte via liens externes
        link_candidates = await self._discover_via_links(candidates[:50])
        candidates.extend(link_candidates)
        
        # 4. Filtrage et déduplication
        candidates = await self._filter_and_deduplicate(candidates)
        
        # 5. Évaluation de la pertinence
        evaluated_candidates = await self._evaluate_candidates(candidates)
        
        # 6. Sauvegarde des résultats
        await self._save_discovery_results(evaluated_candidates)
        
        return evaluated_candidates[:max_results]
        
    async def _generate_smart_queries(self) -> List[str]:
        """
        Génère des requêtes de recherche intelligentes basées sur :
        - Les tendances tech actuelles
        - Les sujets qui ont donné de bons résultats
        - L'analyse des sources existantes
        """
        base_queries = settings.discovery_search_queries.copy()
        
        # Requêtes basées sur les tendances actuelles
        trending_queries = await self._get_trending_tech_topics()
        
        # Requêtes combinées intelligentes
        combined_queries = self._generate_combined_queries(base_queries)
        
        # Requêtes basées sur les succès passés
        successful_queries = await self._get_successful_queries()
        
        all_queries = base_queries + trending_queries + combined_queries + successful_queries
        
        # Randomisation et limitation
        import random
        random.shuffle(all_queries)
        
        return list(set(all_queries))[:20]  # Déduplication et limite
        
    async def _get_trending_tech_topics(self) -> List[str]:
        """Découvre les sujets tech tendance"""
        trending_topics = [
            "AI tools 2024", "machine learning frameworks", 
            "web3 development", "kubernetes best practices",
            "python libraries 2024", "javascript frameworks 2024",
            "devops automation", "cloud native development",
            "microservices architecture", "API design patterns"
        ]
        
        # Ajouter la date actuelle pour des résultats frais
        current_year = datetime.now().year
        dated_topics = [f"{topic} {current_year}" for topic in trending_topics[:5]]
        
        return trending_topics + dated_topics
        
    def _generate_combined_queries(self, base_queries: List[str]) -> List[str]:
        """Génère des requêtes combinées intelligentes"""
        combinations = []
        tech_modifiers = ["tutorial", "guide", "best practices", "tips", "2024"]
        
        for query in base_queries[:5]:
            for modifier in tech_modifiers:
                combinations.append(f"{query} {modifier}")
                
        return combinations
        
    async def _get_successful_queries(self) -> List[str]:
        """Récupère les requêtes qui ont donné de bons résultats par le passé"""
        async with db_manager.get_session() as session:
            # Requête pour obtenir les meilleures requêtes des 30 derniers jours
            result = await session.execute("""
                SELECT search_query, AVG(tech_relevance_score) as avg_score
                FROM discovery_results 
                WHERE discovered_at > NOW() - INTERVAL '30 days'
                  AND is_tech_relevant = true
                GROUP BY search_query
                HAVING COUNT(*) >= 3
                ORDER BY avg_score DESC
                LIMIT 10
            """)
            
            return [row[0] for row in result.fetchall()]
            
    async def _search_multiple_engines(self, query: str) -> List[DiscoveryCandidate]:
        """Recherche sur plusieurs moteurs de recherche"""
        candidates = []
        
        # Configuration des moteurs de recherche
        engines = ['google', 'bing', 'duckduckgo']
        
        # Recherche parallèle sur tous les moteurs
        tasks = []
        for engine_name in engines:
            if engine := self.search_factory.get_engine(engine_name):
                task = self._search_single_engine(engine, query, engine_name)
                tasks.append(task)
                
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    candidates.extend(result)
                    
        return candidates
        
    async def _search_single_engine(self, engine, query: str, engine_name: str) -> List[DiscoveryCandidate]:
        """Recherche sur un moteur spécifique"""
        try:
            results = await engine.search(
                query, 
                num_results=settings.discovery_max_results_per_query // 3
            )
            
            candidates = []
            for result in results:
                domain = urlparse(result['url']).netloc.lower()
                
                # Évite les domaines déjà connus
                if domain not in self.discovered_domains:
                    candidate = DiscoveryCandidate(
                        url=result['url'],
                        title=result.get('title', ''),
                        description=result.get('description', ''),
                        source_engine=engine_name,
                        search_query=query,
                        domain=domain
                    )
                    candidates.append(candidate)
                    
            return candidates
            
        except Exception as e:
            # Log l'erreur mais continue avec les autres moteurs
            print(f"Erreur lors de la recherche {engine_name}: {e}")
            return []
            
    async def _discover_via_links(self, candidates: List[DiscoveryCandidate]) -> List[DiscoveryCandidate]:
        """
        Découvre de nouvelles sources en analysant les liens externes
        des candidats prometteurs
        """
        link_candidates = []
        
        # Sélectionne les meilleurs candidats pour l'analyse de liens
        promising_candidates = [c for c in candidates if c.tech_relevance_score > 0.6][:10]
        
        for candidate in promising_candidates:
            try:
                external_links = await self._extract_external_links(candidate.url)
                
                for link_info in external_links:
                    domain = urlparse(link_info['url']).netloc.lower()
                    
                    if (domain not in self.discovered_domains and 
                        self._is_likely_tech_domain(domain)):
                        
                        link_candidate = DiscoveryCandidate(
                            url=link_info['url'],
                            title=link_info.get('title', ''),
                            description=link_info.get('description', ''),
                            source_engine='link_discovery',
                            search_query=f"via:{candidate.domain}",
                            domain=domain
                        )
                        link_candidates.append(link_candidate)
                        
            except Exception as e:
                print(f"Erreur lors de l'extraction de liens de {candidate.url}: {e}")
                continue
                
        return link_candidates
        
    async def _extract_external_links(self, url: str) -> List[Dict[str, str]]:
        """Extrait les liens externes d'une page"""
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    return self._parse_external_links(content, url)
        except Exception:
            pass
            
        return []
        
    def _parse_external_links(self, html_content: str, base_url: str) -> List[Dict[str, str]]:
        """Parse les liens externes depuis le contenu HTML"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html_content, 'html.parser')
        base_domain = urlparse(base_url).netloc.lower()
        
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            absolute_url = urljoin(base_url, href)
            link_domain = urlparse(absolute_url).netloc.lower()
            
            # Filtre les liens externes
            if (link_domain != base_domain and 
                link_domain and 
                not link_domain.startswith('www.') and
                len(links) < 20):  # Limite le nombre de liens
                
                link_info = {
                    'url': absolute_url,
                    'title': link.get_text(strip=True)[:100],
                    'description': ''
                }
                links.append(link_info)
                
        return links
        
    def _is_likely_tech_domain(self, domain: str) -> bool:
        """Détermine si un domaine est probablement technique"""
        tech_indicators = [
            'dev', 'tech', 'code', 'github', 'gitlab', 'stackoverflow',
            'medium', 'blog', 'docs', 'api', 'tutorial', 'guide',
            'programming', 'software', 'engineering', 'data'
        ]
        
        domain_lower = domain.lower()
        return any(indicator in domain_lower for indicator in tech_indicators)
        
    async def _filter_and_deduplicate(self, candidates: List[DiscoveryCandidate]) -> List[DiscoveryCandidate]:
        """Filtre et déduplique les candidats"""
        # Déduplication par domaine
        seen_domains = set()
        unique_candidates = []
        
        for candidate in candidates:
            if candidate.domain not in seen_domains:
                seen_domains.add(candidate.domain)
                unique_candidates.append(candidate)
                
        # Filtrage basique
        filtered_candidates = []
        for candidate in unique_candidates:
            if self._is_valid_candidate(candidate):
                filtered_candidates.append(candidate)
                
        return filtered_candidates
        
    def _is_valid_candidate(self, candidate: DiscoveryCandidate) -> bool:
        """Valide qu'un candidat mérite une évaluation"""
        # Filtre les domaines non pertinents
        excluded_domains = {
            'facebook.com', 'twitter.com', 'linkedin.com', 'instagram.com',
            'youtube.com', 'amazon.com', 'ebay.com', 'wikipedia.org'
        }
        
        if candidate.domain in excluded_domains:
            return False
            
        # Vérifie que l'URL est valide
        parsed = urlparse(candidate.url)
        if not parsed.scheme or not parsed.netloc:
            return False
            
        # Vérifie que le titre ou la description contient du contenu technique
        text_content = f"{candidate.title} {candidate.description}".lower()
        tech_keywords = [
            'programming', 'development', 'code', 'software', 'tech',
            'tutorial', 'guide', 'api', 'framework', 'library'
        ]
        
        return any(keyword in text_content for keyword in tech_keywords)
        
    async def _evaluate_candidates(self, candidates: List[DiscoveryCandidate]) -> List[DiscoveryCandidate]:
        """Évalue la pertinence et la qualité des candidats"""
        evaluated_candidates = []
        
        # Traitement par batch pour éviter la surcharge
        batch_size = 10
        for i in range(0, len(candidates), batch_size):
            batch = candidates[i:i + batch_size]
            
            # Évaluation parallèle du batch
            tasks = [self._evaluate_single_candidate(candidate) for candidate in batch]
            evaluated_batch = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in evaluated_batch:
                if isinstance(result, DiscoveryCandidate):
                    evaluated_candidates.append(result)
                    
            # Pause entre les batches
            await asyncio.sleep(1)
            
        # Tri par score de pertinence technique
        evaluated_candidates.sort(key=lambda x: x.tech_relevance_score, reverse=True)
        
        return evaluated_candidates
        
    async def _evaluate_single_candidate(self, candidate: DiscoveryCandidate) -> DiscoveryCandidate:
        """Évalue un candidat individuel"""
        try:
            # Analyse de la pertinence basée sur le contenu disponible
            candidate.relevance_score = await self.relevance_analyzer.analyze_text(
                f"{candidate.title} {candidate.description}"
            )
            
            # Évaluation technique spécifique
            candidate.tech_relevance_score = await self._evaluate_tech_relevance(candidate)
            
            # Évaluation de la qualité du domaine
            candidate.quality_score = await self.quality_analyzer.analyze_domain(candidate.domain)
            
            return candidate
            
        except Exception as e:
            print(f"Erreur lors de l'évaluation de {candidate.url}: {e}")
            return candidate
            
    async def _evaluate_tech_relevance(self, candidate: DiscoveryCandidate) -> float:
        """Évalue spécifiquement la pertinence technique"""
        text_content = f"{candidate.title} {candidate.description}".lower()
        
        # Mots-clés techniques avec poids
        tech_keywords = {
            # Langages de programmation
            'python': 1.0, 'javascript': 1.0, 'java': 1.0, 'typescript': 1.0,
            'go': 1.0, 'rust': 1.0, 'php': 1.0, 'ruby': 1.0, 'c++': 1.0,
            
            # Frameworks et librairies
            'react': 0.9, 'vue': 0.9, 'angular': 0.9, 'django': 0.9,
            'flask': 0.9, 'express': 0.9, 'spring': 0.9,
            
            # Technologies
            'api': 0.8, 'database': 0.8, 'docker': 0.8, 'kubernetes': 0.8,
            'cloud': 0.7, 'devops': 0.8, 'ai': 0.9, 'machine learning': 1.0,
            
            # Concepts
            'tutorial': 0.7, 'guide': 0.7, 'documentation': 0.8,
            'best practices': 0.8, 'development': 0.7
        }
        
        score = 0.0
        total_weight = 0.0
        
        for keyword, weight in tech_keywords.items():
            if keyword in text_content:
                score += weight
                total_weight += weight
                
        # Normalisation
        if total_weight > 0:
            score = min(score / total_weight, 1.0)
            
        # Bonus pour les domaines techniques connus
        domain_bonus = self._get_domain_tech_bonus(candidate.domain)
        score = min(score + domain_bonus, 1.0)
        
        return score
        
    def _get_domain_tech_bonus(self, domain: str) -> float:
        """Donne un bonus pour les domaines techniques reconnus"""
        tech_domains = {
            'github.com': 0.3, 'stackoverflow.com': 0.3, 'medium.com': 0.2,
            'dev.to': 0.3, 'hackernoon.com': 0.2, 'codepen.io': 0.2,
            'replit.com': 0.2, 'codesandbox.io': 0.2
        }
        
        return tech_domains.get(domain, 0.0)
        
    async def _save_discovery_results(self, candidates: List[DiscoveryCandidate]):
        """Sauvegarde les résultats de découverte en base"""
        async with db_manager.get_session() as session:
            for candidate in candidates:
                # Vérifie si ce résultat existe déjà
                existing = await session.execute("""
                    SELECT id FROM discovery_results 
                    WHERE search_query = %s AND discovered_url = %s
                """, (candidate.search_query, candidate.url))
                
                if not existing.fetchone():
                    # Crée un nouveau résultat de découverte
                    discovery_result = DiscoveryResult(
                        search_query=candidate.search_query,
                        search_engine=candidate.source_engine,
                        discovered_url=candidate.url,
                        domain=candidate.domain,
                        relevance_score=candidate.relevance_score,
                        quality_score=candidate.quality_score,
                        tech_relevance_score=candidate.tech_relevance_score,
                        title=candidate.title,
                        description=candidate.description,
                        is_tech_relevant=candidate.tech_relevance_score >= settings.discovery_relevance_threshold
                    )
                    
                    session.add(discovery_result)
                    
            await session.commit()
            
    async def create_sources_from_discoveries(self, min_tech_score: float = 0.7) -> List[str]:
        """
        Crée de nouvelles sources à partir des meilleures découvertes
        """
        created_sources = []
        
        async with db_manager.get_session() as session:
            # Récupère les meilleures découvertes non encore converties
            result = await session.execute("""
                SELECT * FROM discovery_results 
                WHERE tech_relevance_score >= %s 
                  AND became_source = false
                  AND is_tech_relevant = true
                ORDER BY tech_relevance_score DESC
                LIMIT 50
            """, (min_tech_score,))
            
            discoveries = result.fetchall()
            
            for discovery in discoveries:
                try:
                    # Crée une nouvelle source
                    source = Source(
                        name=discovery.title or discovery.domain,
                        url=discovery.discovered_url,
                        domain=discovery.domain,
                        source_type=self._detect_source_type(discovery.discovered_url),
                        category=self._detect_category(discovery.title, discovery.description),
                        quality_score=discovery.quality_score,
                        relevance_score=discovery.tech_relevance_score
                    )
                    
                    session.add(source)
                    
                    # Met à jour la découverte
                    await session.execute("""
                        UPDATE discovery_results 
                        SET became_source = true, source_id = %s
                        WHERE id = %s
                    """, (source.id, discovery.id))
                    
                    created_sources.append(discovery.domain)
                    
                except Exception as e:
                    print(f"Erreur lors de la création de source pour {discovery.domain}: {e}")
                    continue
                    
            await session.commit()
            
        return created_sources
        
    def _detect_source_type(self, url: str) -> str:
        """Détecte le type de source basé sur l'URL"""
        domain = urlparse(url).netloc.lower()
        
        if 'blog' in domain or 'medium' in domain:
            return 'blog'
        elif 'docs' in domain or 'documentation' in domain:
            return 'docs'
        elif 'news' in domain:
            return 'news'
        elif 'forum' in domain or 'stackoverflow' in domain:
            return 'forum'
        else:
            return 'website'
            
    def _detect_category(self, title: str, description: str) -> str:
        """Détecte la catégorie basée sur le contenu"""
        text = f"{title} {description}".lower()
        
        categories = {
            'web_development': ['web', 'frontend', 'backend', 'javascript', 'react', 'vue'],
            'mobile_development': ['mobile', 'android', 'ios', 'flutter', 'react native'],
            'data_science': ['data', 'machine learning', 'ai', 'analytics', 'python'],
            'devops': ['devops', 'docker', 'kubernetes', 'ci/cd', 'deployment'],
            'cloud': ['cloud', 'aws', 'azure', 'gcp', 'serverless'],
            'security': ['security', 'cybersecurity', 'encryption', 'vulnerability']
        }
        
        for category, keywords in categories.items():
            if any(keyword in text for keyword in keywords):
                return category
                
        return 'general'
