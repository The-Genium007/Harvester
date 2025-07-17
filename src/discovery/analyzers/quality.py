"""
Analyseur de qualité pour évaluer la qualité des domaines et sources
"""
import asyncio
import aiohttp
import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from datetime import datetime, timedelta


class QualityAnalyzer:
    """
    Analyseur de qualité qui évalue :
    - La qualité technique d'un domaine
    - La fiabilité d'une source
    - Les métriques de performance
    """
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.domain_cache: Dict[str, Dict] = {}
        
    async def initialize(self):
        """Initialise l'analyseur"""
        connector = aiohttp.TCPConnector(
            limit=50,
            limit_per_host=5,
            ttl_dns_cache=300
        )
        
        timeout = aiohttp.ClientTimeout(total=15, connect=5)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'SentinelIQ-QualityAnalyzer/1.0'
            }
        )
        
    async def close(self):
        """Ferme les ressources"""
        if self.session:
            await self.session.close()
            
    async def analyze_domain(self, domain: str) -> float:
        """
        Analyse la qualité d'un domaine
        
        Args:
            domain: Nom de domaine à analyser
            
        Returns:
            Score de qualité entre 0 et 1
        """
        # Vérifie le cache
        if domain in self.domain_cache:
            cache_entry = self.domain_cache[domain]
            if datetime.now() - cache_entry['timestamp'] < timedelta(hours=24):
                return cache_entry['score']
                
        try:
            # Analyse multi-facteurs
            scores = await asyncio.gather(
                self._analyze_domain_reputation(domain),
                self._analyze_technical_indicators(domain),
                self._analyze_content_quality(domain),
                return_exceptions=True
            )
            
            # Calcule le score moyen en ignorant les exceptions
            valid_scores = [s for s in scores if isinstance(s, float)]
            if valid_scores:
                final_score = sum(valid_scores) / len(valid_scores)
            else:
                final_score = 0.5  # Score neutre si aucune analyse n'a réussi
                
            # Met en cache le résultat
            self.domain_cache[domain] = {
                'score': final_score,
                'timestamp': datetime.now()
            }
            
            return final_score
            
        except Exception as e:
            print(f"Erreur lors de l'analyse de qualité de {domain}: {e}")
            return 0.5  # Score neutre en cas d'erreur
            
    async def _analyze_domain_reputation(self, domain: str) -> float:
        """Analyse la réputation du domaine"""
        score = 0.5  # Score de base
        
        # Indicateurs de réputation positive
        reputable_indicators = [
            'github.com', 'stackoverflow.com', 'medium.com', 'dev.to',
            'hackernoon.com', 'freecodecamp.org', 'codecademy.com',
            'coursera.org', 'udemy.com', 'pluralsight.com'
        ]
        
        # Domaines académiques et organisationnels
        academic_domains = ['.edu', '.org', '.ac.uk', '.ac.fr']
        
        # Vérification des indicateurs de réputation
        if any(indicator in domain for indicator in reputable_indicators):
            score += 0.3
            
        if any(domain.endswith(suffix) for suffix in academic_domains):
            score += 0.2
            
        # Analyse de la structure du domaine
        if self._is_subdomain_structure_good(domain):
            score += 0.1
            
        # Pénalités pour des indicateurs négatifs
        suspicious_patterns = [
            r'\d{4,}',  # Trop de chiffres
            r'[^a-zA-Z0-9.-]',  # Caractères suspects
            r'\.tk$|\.ml$|\.ga$|\.cf$'  # Domaines gratuits suspects
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, domain):
                score -= 0.1
                
        return max(min(score, 1.0), 0.0)
        
    def _is_subdomain_structure_good(self, domain: str) -> bool:
        """Vérifie si la structure du sous-domaine est bonne"""
        parts = domain.split('.')
        
        # Préfère les domaines simples ou avec des sous-domaines logiques
        if len(parts) <= 2:
            return True
            
        # Sous-domaines techniques acceptables
        good_subdomains = ['blog', 'docs', 'api', 'dev', 'www', 'news', 'tech']
        if parts[0] in good_subdomains:
            return True
            
        return False
        
    async def _analyze_technical_indicators(self, domain: str) -> float:
        """Analyse les indicateurs techniques du domaine"""
        if not self.session:
            await self.initialize()
            
        score = 0.5
        
        try:
            url = f"https://{domain}"
            async with self.session.head(url, allow_redirects=True) as response:
                # Vérification du statut HTTP
                if response.status == 200:
                    score += 0.2
                elif response.status in [301, 302]:
                    score += 0.1  # Redirection acceptable
                else:
                    score -= 0.2
                    
                # Analyse des headers de sécurité
                security_headers = [
                    'strict-transport-security',
                    'x-content-type-options',
                    'x-frame-options',
                    'x-xss-protection'
                ]
                
                security_score = 0
                for header in security_headers:
                    if header in response.headers:
                        security_score += 0.025
                        
                score += security_score
                
                # Vérification du certificat HTTPS
                if response.url.scheme == 'https':
                    score += 0.1
                    
        except Exception:
            # Si HTTPS échoue, essaie HTTP
            try:
                url = f"http://{domain}"
                async with self.session.head(url, allow_redirects=True) as response:
                    if response.status == 200:
                        score += 0.1  # Pénalité pour pas de HTTPS
                    else:
                        score -= 0.3  # Gros malus si rien ne fonctionne
            except Exception:
                score -= 0.4  # Très gros malus si le domaine n'est pas accessible
                
        return max(min(score, 1.0), 0.0)
        
    async def _analyze_content_quality(self, domain: str) -> float:
        """Analyse la qualité du contenu du domaine"""
        if not self.session:
            await self.initialize()
            
        score = 0.5
        
        try:
            url = f"https://{domain}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    score = self._evaluate_content_quality(content, domain)
                    
        except Exception:
            # Essaie HTTP si HTTPS échoue
            try:
                url = f"http://{domain}"
                async with self.session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        score = self._evaluate_content_quality(content, domain) - 0.1
            except Exception:
                score = 0.3  # Score bas si pas de contenu accessible
                
        return max(min(score, 1.0), 0.0)
        
    def _evaluate_content_quality(self, content: str, domain: str) -> float:
        """Évalue la qualité du contenu HTML"""
        score = 0.5
        
        # Indicateurs de qualité positive
        quality_indicators = [
            'documentation', 'tutorial', 'guide', 'example',
            'github', 'source code', 'open source', 'api',
            'best practices', 'learning', 'education'
        ]
        
        content_lower = content.lower()
        
        # Calcule le score basé sur les indicateurs
        for indicator in quality_indicators:
            if indicator in content_lower:
                score += 0.05
                
        # Analyse de la structure HTML
        if '<title>' in content and '</title>' in content:
            score += 0.1
            
        if '<meta name="description"' in content:
            score += 0.1
            
        # Présence de contenu technique
        tech_patterns = [
            r'<code[^>]*>',
            r'<pre[^>]*>',
            r'github\.com',
            r'stackoverflow\.com',
            r'function\s*\(',
            r'class\s+\w+',
            r'import\s+\w+'
        ]
        
        for pattern in tech_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                score += 0.05
                
        # Pénalités pour du contenu de mauvaise qualité
        spam_indicators = [
            'click here', 'buy now', 'limited time',
            'amazing deal', 'secret', 'hack'
        ]
        
        for indicator in spam_indicators:
            if indicator in content_lower:
                score -= 0.05
                
        # Vérification de la longueur du contenu
        if len(content) > 5000:  # Contenu substantiel
            score += 0.1
        elif len(content) < 1000:  # Contenu trop court
            score -= 0.1
            
        return score
        
    async def analyze_source_reliability(self, url: str) -> Dict[str, float]:
        """
        Analyse complète de la fiabilité d'une source
        
        Args:
            url: URL de la source à analyser
            
        Returns:
            Dictionnaire avec différents scores de fiabilité
        """
        domain = urlparse(url).netloc.lower()
        
        # Analyse parallèle de différents aspects
        results = await asyncio.gather(
            self._check_content_freshness(url),
            self._check_author_credibility(url),
            self._check_external_links_quality(url),
            return_exceptions=True
        )
        
        # Traite les résultats
        reliability_scores = {
            'domain_quality': await self.analyze_domain(domain),
            'content_freshness': results[0] if isinstance(results[0], float) else 0.5,
            'author_credibility': results[1] if isinstance(results[1], float) else 0.5,
            'links_quality': results[2] if isinstance(results[2], float) else 0.5
        }
        
        # Score global
        reliability_scores['overall'] = sum(reliability_scores.values()) / len(reliability_scores)
        
        return reliability_scores
        
    async def _check_content_freshness(self, url: str) -> float:
        """Vérifie la fraîcheur du contenu"""
        if not self.session:
            await self.initialize()
            
        try:
            async with self.session.head(url) as response:
                # Vérifie les headers de date
                last_modified = response.headers.get('last-modified')
                if last_modified:
                    # Parse la date et calcule la fraîcheur
                    # Implémentation simplifiée
                    return 0.8  # Score de base pour contenu avec date
                    
                return 0.6  # Score moyen si pas de date
                
        except Exception:
            return 0.5
            
    async def _check_author_credibility(self, url: str) -> float:
        """Vérifie la crédibilité de l'auteur"""
        # Implémentation simplifiée
        # Dans une version complète, on analyserait les informations d'auteur
        return 0.7
        
    async def _check_external_links_quality(self, url: str) -> float:
        """Analyse la qualité des liens externes"""
        if not self.session:
            await self.initialize()
            
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    # Analyse simplifiée des liens
                    if 'github.com' in content or 'stackoverflow.com' in content:
                        return 0.8
                    return 0.6
        except Exception:
            pass
            
        return 0.5
        
    def get_domain_quality_explanation(self, domain: str) -> Dict[str, any]:
        """
        Fournit une explication détaillée de la qualité du domaine
        
        Args:
            domain: Domaine à expliquer
            
        Returns:
            Dictionnaire avec l'explication détaillée
        """
        explanation = {
            'domain': domain,
            'reputation_factors': [],
            'technical_factors': [],
            'content_factors': [],
            'penalties': [],
            'overall_assessment': 'pending'
        }
        
        # Analyse de réputation
        reputable_sites = [
            'github.com', 'stackoverflow.com', 'medium.com'
        ]
        
        if any(site in domain for site in reputable_sites):
            explanation['reputation_factors'].append('Known reputable tech site')
            
        if domain.endswith('.edu') or domain.endswith('.org'):
            explanation['reputation_factors'].append('Academic or organizational domain')
            
        # Cette méthode pourrait être étendue pour fournir plus de détails
        
        return explanation
