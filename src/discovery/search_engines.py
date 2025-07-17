"""
Factory et implémentations pour les moteurs de recherche
"""
import asyncio
import aiohttp
import json
from typing import List, Dict, Optional, Any
from urllib.parse import quote_plus
from abc import ABC, abstractmethod

from ...config import settings


class SearchEngine(ABC):
    """Interface abstraite pour les moteurs de recherche"""
    
    @abstractmethod
    async def search(self, query: str, num_results: int = 10) -> List[Dict[str, str]]:
        """
        Effectue une recherche
        
        Args:
            query: Requête de recherche
            num_results: Nombre de résultats à retourner
            
        Returns:
            Liste de dictionnaires avec 'url', 'title', 'description'
        """
        pass


class GoogleSearchEngine(SearchEngine):
    """Moteur de recherche Google via Custom Search API"""
    
    def __init__(self):
        self.api_key = settings.google_search_api_key
        self.cx = settings.google_search_cx
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def initialize(self):
        """Initialise la session HTTP"""
        if not self.session:
            self.session = aiohttp.ClientSession()
            
    async def close(self):
        """Ferme la session"""
        if self.session:
            await self.session.close()
            
    async def search(self, query: str, num_results: int = 10) -> List[Dict[str, str]]:
        """Recherche via Google Custom Search API"""
        if not self.api_key or not self.cx:
            return []
            
        await self.initialize()
        
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': self.api_key,
                'cx': self.cx,
                'q': query,
                'num': min(num_results, 10)  # Google limite à 10 par requête
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_google_results(data)
                    
        except Exception as e:
            print(f"Erreur Google Search: {e}")
            
        return []
        
    def _parse_google_results(self, data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Parse les résultats de l'API Google"""
        results = []
        
        for item in data.get('items', []):
            result = {
                'url': item.get('link', ''),
                'title': item.get('title', ''),
                'description': item.get('snippet', '')
            }
            results.append(result)
            
        return results


class BingSearchEngine(SearchEngine):
    """Moteur de recherche Bing via Bing Search API"""
    
    def __init__(self):
        self.api_key = settings.bing_search_api_key
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def initialize(self):
        """Initialise la session HTTP"""
        if not self.session:
            self.session = aiohttp.ClientSession()
            
    async def close(self):
        """Ferme la session"""
        if self.session:
            await self.session.close()
            
    async def search(self, query: str, num_results: int = 10) -> List[Dict[str, str]]:
        """Recherche via Bing Search API"""
        if not self.api_key:
            return []
            
        await self.initialize()
        
        try:
            url = "https://api.bing.microsoft.com/v7.0/search"
            headers = {
                'Ocp-Apim-Subscription-Key': self.api_key
            }
            params = {
                'q': query,
                'count': min(num_results, 50),
                'textFormat': 'HTML'
            }
            
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_bing_results(data)
                    
        except Exception as e:
            print(f"Erreur Bing Search: {e}")
            
        return []
        
    def _parse_bing_results(self, data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Parse les résultats de l'API Bing"""
        results = []
        
        web_pages = data.get('webPages', {})
        for item in web_pages.get('value', []):
            result = {
                'url': item.get('url', ''),
                'title': item.get('name', ''),
                'description': item.get('snippet', '')
            }
            results.append(result)
            
        return results


class DuckDuckGoSearchEngine(SearchEngine):
    """Moteur de recherche DuckDuckGo (sans API officielle)"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def initialize(self):
        """Initialise la session HTTP"""
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
            
    async def close(self):
        """Ferme la session"""
        if self.session:
            await self.session.close()
            
    async def search(self, query: str, num_results: int = 10) -> List[Dict[str, str]]:
        """
        Recherche via DuckDuckGo (méthode simplifiée)
        Note: DuckDuckGo n'a pas d'API officielle, cette implémentation
        est basique et pourrait nécessiter des ajustements
        """
        await self.initialize()
        
        try:
            # Utilise l'API instant answer de DuckDuckGo
            url = "https://api.duckduckgo.com/"
            params = {
                'q': query,
                'format': 'json',
                'no_html': '1',
                'skip_disambig': '1'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_ddg_results(data, query)
                    
        except Exception as e:
            print(f"Erreur DuckDuckGo Search: {e}")
            
        return []
        
    def _parse_ddg_results(self, data: Dict[str, Any], query: str) -> List[Dict[str, str]]:
        """Parse les résultats DuckDuckGo"""
        results = []
        
        # DuckDuckGo instant answers
        if data.get('Abstract'):
            result = {
                'url': data.get('AbstractURL', ''),
                'title': data.get('Heading', query),
                'description': data.get('Abstract', '')
            }
            if result['url']:
                results.append(result)
                
        # Related topics
        for topic in data.get('RelatedTopics', []):
            if isinstance(topic, dict) and topic.get('FirstURL'):
                result = {
                    'url': topic.get('FirstURL', ''),
                    'title': topic.get('Text', '').split(' - ')[0] if ' - ' in topic.get('Text', '') else topic.get('Text', ''),
                    'description': topic.get('Text', '')
                }
                results.append(result)
                
        return results[:10]  # Limite à 10 résultats


class MockSearchEngine(SearchEngine):
    """Moteur de recherche mock pour les tests et développement"""
    
    def __init__(self):
        # Données de test avec des sites tech réels
        self.mock_data = {
            'python': [
                {
                    'url': 'https://realpython.com/python-tutorial',
                    'title': 'Python Tutorial - Real Python',
                    'description': 'Learn Python programming with tutorials and examples'
                },
                {
                    'url': 'https://pythonbasics.org',
                    'title': 'Python Basics - Learn Python Programming',
                    'description': 'Python tutorials for beginners and advanced developers'
                }
            ],
            'javascript': [
                {
                    'url': 'https://javascript.info',
                    'title': 'The Modern JavaScript Tutorial',
                    'description': 'Modern JavaScript Tutorial: simple, but detailed explanations'
                },
                {
                    'url': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript',
                    'title': 'JavaScript | MDN',
                    'description': 'JavaScript reference and tutorials from Mozilla'
                }
            ]
        }
        
    async def search(self, query: str, num_results: int = 10) -> List[Dict[str, str]]:
        """Retourne des données mock basées sur la requête"""
        query_lower = query.lower()
        
        # Trouve la meilleure correspondance
        for keyword, results in self.mock_data.items():
            if keyword in query_lower:
                return results[:num_results]
                
        # Résultats génériques si aucune correspondance
        return [
            {
                'url': f'https://example-tech-site.com/search?q={quote_plus(query)}',
                'title': f'Results for: {query}',
                'description': f'Technical content related to {query}'
            }
        ]


class SearchEngineFactory:
    """Factory pour créer les instances de moteurs de recherche"""
    
    def __init__(self):
        self._engines: Dict[str, SearchEngine] = {}
        
    def get_engine(self, engine_name: str) -> Optional[SearchEngine]:
        """
        Récupère une instance de moteur de recherche
        
        Args:
            engine_name: Nom du moteur ('google', 'bing', 'duckduckgo', 'mock')
            
        Returns:
            Instance du moteur de recherche ou None si non disponible
        """
        if engine_name not in self._engines:
            self._engines[engine_name] = self._create_engine(engine_name)
            
        return self._engines[engine_name]
        
    def _create_engine(self, engine_name: str) -> Optional[SearchEngine]:
        """Crée une nouvelle instance de moteur"""
        if engine_name == 'google':
            if settings.google_search_api_key and settings.google_search_cx:
                return GoogleSearchEngine()
        elif engine_name == 'bing':
            if settings.bing_search_api_key:
                return BingSearchEngine()
        elif engine_name == 'duckduckgo':
            return DuckDuckGoSearchEngine()
        elif engine_name == 'mock':
            return MockSearchEngine()
            
        return None
        
    async def close_all(self):
        """Ferme toutes les sessions des moteurs"""
        for engine in self._engines.values():
            if hasattr(engine, 'close'):
                await engine.close()
                
    def get_available_engines(self) -> List[str]:
        """Retourne la liste des moteurs disponibles selon la configuration"""
        available = []
        
        if settings.google_search_api_key and settings.google_search_cx:
            available.append('google')
            
        if settings.bing_search_api_key:
            available.append('bing')
            
        available.extend(['duckduckgo', 'mock'])
        
        return available
