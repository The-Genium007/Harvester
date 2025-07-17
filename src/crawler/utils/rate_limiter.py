"""
Rate Limiter pour respecter les limites des sites web
"""
import asyncio
import time
from typing import Dict, Optional
from dataclasses import dataclass
from collections import defaultdict, deque


@dataclass
class RateLimit:
    """Configuration de rate limiting pour un domaine"""
    requests_per_second: float = 1.0
    burst_size: int = 5
    delay_between_requests: float = 1.0


class RateLimiter:
    """
    Rate limiter intelligent qui :
    1. Respecte les limites par domaine
    2. S'adapte selon les réponses du serveur
    3. Gère les bursts de requêtes
    4. Évite de surcharger les serveurs
    """
    
    def __init__(self):
        # Configuration par domaine
        self.domain_limits: Dict[str, RateLimit] = {}
        
        # Historique des requêtes par domaine
        self.request_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Dernière requête par domaine
        self.last_request: Dict[str, float] = {}
        
        # Verrous pour éviter les races conditions
        self.domain_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        
        # Compteurs d'erreurs par domaine
        self.error_counts: Dict[str, int] = defaultdict(int)
        
        # Configuration par défaut
        self.default_limit = RateLimit(
            requests_per_second=1.0,
            burst_size=3,
            delay_between_requests=1.0
        )
        
    def configure_domain(self, domain: str, requests_per_second: float = 1.0,
                        burst_size: int = 3, delay_between_requests: float = 1.0):
        """Configure les limites pour un domaine spécifique"""
        self.domain_limits[domain] = RateLimit(
            requests_per_second=requests_per_second,
            burst_size=burst_size,
            delay_between_requests=delay_between_requests
        )
        
    async def wait_if_needed(self, domain: str) -> float:
        """
        Attendre si nécessaire avant de faire une requête
        
        Args:
            domain: Domaine cible
            
        Returns:
            Temps d'attente effectif en secondes
        """
        async with self.domain_locks[domain]:
            current_time = time.time()
            
            # Récupère ou crée la configuration pour ce domaine
            limit = self.domain_limits.get(domain, self.default_limit)
            
            # Calcule le délai nécessaire
            wait_time = await self._calculate_wait_time(domain, current_time, limit)
            
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                
            # Enregistre cette requête
            self._record_request(domain, current_time + wait_time)
            
            return wait_time
            
    async def _calculate_wait_time(self, domain: str, current_time: float, 
                                 limit: RateLimit) -> float:
        """Calcule le temps d'attente nécessaire"""
        # Vérifie la dernière requête
        last_time = self.last_request.get(domain, 0)
        time_since_last = current_time - last_time
        
        # Délai minimum entre requêtes
        min_delay = limit.delay_between_requests
        if time_since_last < min_delay:
            return min_delay - time_since_last
            
        # Vérifie le rate limiting basé sur l'historique
        history = self.request_history[domain]
        
        # Nettoie l'historique ancien (plus d'une minute)
        while history and current_time - history[0] > 60:
            history.popleft()
            
        # Calcule les requêtes dans la dernière seconde
        recent_requests = sum(1 for req_time in history 
                            if current_time - req_time <= 1.0)
        
        # Vérifie si on dépasse la limite
        if recent_requests >= limit.requests_per_second:
            # Trouve la requête la plus ancienne dans la fenêtre
            oldest_in_window = None
            for req_time in history:
                if current_time - req_time <= 1.0:
                    oldest_in_window = req_time
                    break
                    
            if oldest_in_window:
                return 1.0 - (current_time - oldest_in_window)
                
        # Vérifie le burst
        if len(history) >= limit.burst_size:
            burst_window = 10.0  # 10 secondes pour le burst
            burst_requests = sum(1 for req_time in history 
                               if current_time - req_time <= burst_window)
            
            if burst_requests >= limit.burst_size:
                # Attendre avant le prochain burst
                return burst_window / limit.burst_size
                
        return 0.0
        
    def _record_request(self, domain: str, request_time: float):
        """Enregistre une requête dans l'historique"""
        self.last_request[domain] = request_time
        self.request_history[domain].append(request_time)
        
    async def handle_response(self, domain: str, status_code: int, 
                            response_time: float):
        """
        Traite la réponse d'une requête pour ajuster le rate limiting
        
        Args:
            domain: Domaine de la requête
            status_code: Code de statut HTTP
            response_time: Temps de réponse en secondes
        """
        async with self.domain_locks[domain]:
            if status_code == 429:  # Too Many Requests
                await self._handle_rate_limit_exceeded(domain)
            elif status_code >= 500:  # Erreur serveur
                await self._handle_server_error(domain)
            elif status_code == 200:
                await self._handle_successful_request(domain, response_time)
                
    async def _handle_rate_limit_exceeded(self, domain: str):
        """Gère le cas où le serveur retourne 429"""
        current_limit = self.domain_limits.get(domain, self.default_limit)
        
        # Réduit drastiquement le taux de requêtes
        new_limit = RateLimit(
            requests_per_second=max(current_limit.requests_per_second * 0.5, 0.1),
            burst_size=max(current_limit.burst_size - 1, 1),
            delay_between_requests=min(current_limit.delay_between_requests * 2, 10.0)
        )
        
        self.domain_limits[domain] = new_limit
        self.error_counts[domain] += 1
        
        print(f"Rate limit exceeded for {domain}, reducing to {new_limit.requests_per_second} req/s")
        
    async def _handle_server_error(self, domain: str):
        """Gère les erreurs serveur"""
        self.error_counts[domain] += 1
        
        # Si trop d'erreurs, réduit le taux
        if self.error_counts[domain] > 5:
            current_limit = self.domain_limits.get(domain, self.default_limit)
            
            new_limit = RateLimit(
                requests_per_second=max(current_limit.requests_per_second * 0.8, 0.2),
                burst_size=current_limit.burst_size,
                delay_between_requests=min(current_limit.delay_between_requests * 1.5, 5.0)
            )
            
            self.domain_limits[domain] = new_limit
            
    async def _handle_successful_request(self, domain: str, response_time: float):
        """Gère une requête réussie"""
        # Réinitialise le compteur d'erreurs
        if domain in self.error_counts:
            self.error_counts[domain] = max(0, self.error_counts[domain] - 1)
            
        # Si le serveur répond rapidement, on peut augmenter légèrement le taux
        if response_time < 1.0 and self.error_counts[domain] == 0:
            current_limit = self.domain_limits.get(domain, self.default_limit)
            
            # Augmentation très conservative
            if current_limit.requests_per_second < 2.0:
                new_limit = RateLimit(
                    requests_per_second=min(current_limit.requests_per_second * 1.1, 2.0),
                    burst_size=min(current_limit.burst_size + 1, 10),
                    delay_between_requests=max(current_limit.delay_between_requests * 0.95, 0.5)
                )
                
                self.domain_limits[domain] = new_limit
                
    def get_domain_stats(self, domain: str) -> Dict[str, any]:
        """Récupère les statistiques pour un domaine"""
        limit = self.domain_limits.get(domain, self.default_limit)
        history = self.request_history[domain]
        
        current_time = time.time()
        recent_requests = sum(1 for req_time in history 
                            if current_time - req_time <= 60.0)
        
        return {
            'domain': domain,
            'requests_per_second': limit.requests_per_second,
            'burst_size': limit.burst_size,
            'delay_between_requests': limit.delay_between_requests,
            'recent_requests_count': recent_requests,
            'error_count': self.error_counts[domain],
            'last_request_ago': current_time - self.last_request.get(domain, 0),
            'total_requests': len(history)
        }
        
    def get_all_stats(self) -> Dict[str, any]:
        """Récupère les statistiques globales"""
        domains_with_limits = list(self.domain_limits.keys())
        domains_with_history = list(self.request_history.keys())
        all_domains = set(domains_with_limits + domains_with_history)
        
        stats = {
            'total_domains': len(all_domains),
            'domains_with_custom_limits': len(domains_with_limits),
            'total_requests': sum(len(history) for history in self.request_history.values()),
            'domains': {}
        }
        
        for domain in all_domains:
            stats['domains'][domain] = self.get_domain_stats(domain)
            
        return stats
        
    async def reset_domain_limits(self, domain: str):
        """Remet à zéro les limites d'un domaine"""
        async with self.domain_locks[domain]:
            if domain in self.domain_limits:
                del self.domain_limits[domain]
            if domain in self.error_counts:
                del self.error_counts[domain]
            if domain in self.request_history:
                self.request_history[domain].clear()
            if domain in self.last_request:
                del self.last_request[domain]
                
    def configure_politeness_rules(self):
        """Configure des règles de politesse pour des domaines connus"""
        # Règles conservatrices pour des sites populaires
        conservative_domains = [
            'stackoverflow.com', 'github.com', 'medium.com',
            'reddit.com', 'hackernews.com'
        ]
        
        for domain in conservative_domains:
            self.configure_domain(
                domain=domain,
                requests_per_second=0.5,  # Très conservateur
                burst_size=2,
                delay_between_requests=2.0
            )
            
        # Règles pour la documentation (généralement plus permissive)
        docs_domains = [
            'docs.python.org', 'developer.mozilla.org',
            'kubernetes.io', 'docker.com'
        ]
        
        for domain in docs_domains:
            self.configure_domain(
                domain=domain,
                requests_per_second=1.5,
                burst_size=5,
                delay_between_requests=0.7
            )
