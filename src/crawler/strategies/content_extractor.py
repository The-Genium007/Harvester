"""
Extracteur de contenu intelligent pour différents types de pages
"""
import asyncio
import re
from typing import Dict, Optional, Any
from datetime import datetime
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import json


class ContentExtractor:
    """
    Extracteur de contenu qui s'adapte au type de page :
    - Articles de blog
    - Documentation technique
    - Pages de forum
    - Tutoriels
    """
    
    def __init__(self):
        self.extractors = {
            'article': self._extract_article_content,
            'documentation': self._extract_documentation_content,
            'forum': self._extract_forum_content,
            'tutorial': self._extract_tutorial_content,
            'general': self._extract_general_content
        }
        
    async def initialize(self):
        """Initialise l'extracteur"""
        pass
        
    async def close(self):
        """Ferme les ressources"""
        pass
        
    async def extract_content(self, html_content: str, url: str) -> Dict[str, Any]:
        """
        Extrait le contenu structuré d'une page HTML
        
        Args:
            html_content: Contenu HTML de la page
            url: URL de la page
            
        Returns:
            Dictionnaire avec le contenu extrait
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Détecte le type de contenu
        content_type = self._detect_content_type(soup, url)
        
        # Utilise l'extracteur approprié
        extractor = self.extractors.get(content_type, self.extractors['general'])
        extracted = await extractor(soup, url)
        
        # Ajoute des métadonnées communes
        extracted.update({
            'content_type': content_type,
            'url': url,
            'domain': urlparse(url).netloc,
            'extraction_timestamp': datetime.now()
        })
        
        return extracted
        
    def _detect_content_type(self, soup: BeautifulSoup, url: str) -> str:
        """Détecte le type de contenu de la page"""
        
        # Vérifie les métadonnées OpenGraph/schema.org
        og_type = soup.find('meta', property='og:type')
        if og_type and og_type.get('content') == 'article':
            return 'article'
            
        # Vérifie les structures schema.org
        schema_scripts = soup.find_all('script', type='application/ld+json')
        for script in schema_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    schema_type = data.get('@type', '').lower()
                    if 'article' in schema_type:
                        return 'article'
                    elif 'documentation' in schema_type:
                        return 'documentation'
            except Exception:
                continue
                
        # Détection basée sur l'URL
        url_lower = url.lower()
        if any(pattern in url_lower for pattern in ['blog', 'article', 'post']):
            return 'article'
        elif any(pattern in url_lower for pattern in ['docs', 'documentation', 'manual']):
            return 'documentation'
        elif any(pattern in url_lower for pattern in ['forum', 'discussion', 'thread']):
            return 'forum'
        elif any(pattern in url_lower for pattern in ['tutorial', 'guide', 'howto']):
            return 'tutorial'
            
        # Détection basée sur la structure HTML
        if soup.find('article') or soup.find(class_=re.compile(r'article|post')):
            return 'article'
        elif soup.find(class_=re.compile(r'documentation|docs')):
            return 'documentation'
        elif soup.find(class_=re.compile(r'forum|thread')):
            return 'forum'
            
        return 'general'
        
    async def _extract_article_content(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extrait le contenu d'un article de blog"""
        result = {
            'title': '',
            'content': '',
            'author': '',
            'published_at': None,
            'tags': [],
            'category': ''
        }
        
        # Extraction du titre
        title_selectors = [
            'h1',
            '.post-title',
            '.article-title',
            '[property="og:title"]',
            'title'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                if selector == '[property="og:title"]':
                    result['title'] = title_elem.get('content', '')
                else:
                    result['title'] = title_elem.get_text(strip=True)
                if result['title']:
                    break
                    
        # Extraction du contenu principal
        content_selectors = [
            'article',
            '.post-content',
            '.article-content',
            '.entry-content',
            '.content',
            'main'
        ]
        
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                # Nettoie le contenu
                self._clean_content_element(content_elem)
                result['content'] = content_elem.get_text(strip=True, separator=' ')
                if len(result['content']) > 200:  # Contenu substantiel
                    break
                    
        # Extraction de l'auteur
        author_selectors = [
            '.author',
            '.byline',
            '[rel="author"]',
            '[property="article:author"]',
            '.post-author'
        ]
        
        for selector in author_selectors:
            author_elem = soup.select_one(selector)
            if author_elem:
                if 'property' in selector:
                    result['author'] = author_elem.get('content', '')
                else:
                    result['author'] = author_elem.get_text(strip=True)
                if result['author']:
                    break
                    
        # Extraction de la date
        date_selectors = [
            'time[datetime]',
            '.published',
            '.post-date',
            '[property="article:published_time"]'
        ]
        
        for selector in date_selectors:
            date_elem = soup.select_one(selector)
            if date_elem:
                date_str = ''
                if 'datetime' in date_elem.attrs:
                    date_str = date_elem['datetime']
                elif 'property' in selector:
                    date_str = date_elem.get('content', '')
                else:
                    date_str = date_elem.get_text(strip=True)
                    
                result['published_at'] = self._parse_date(date_str)
                if result['published_at']:
                    break
                    
        # Extraction des tags
        tag_selectors = [
            '.tags a',
            '.post-tags a',
            '.categories a'
        ]
        
        for selector in tag_selectors:
            tag_elems = soup.select(selector)
            if tag_elems:
                result['tags'] = [tag.get_text(strip=True) for tag in tag_elems]
                break
                
        return result
        
    async def _extract_documentation_content(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extrait le contenu de documentation technique"""
        result = {
            'title': '',
            'content': '',
            'author': '',
            'published_at': None,
            'tags': [],
            'category': 'documentation'
        }
        
        # Pour la documentation, se concentre sur le contenu technique
        title_elem = soup.find('h1')
        if title_elem:
            result['title'] = title_elem.get_text(strip=True)
            
        # Recherche le contenu principal
        main_content = soup.find('main') or soup.find('.content') or soup.find('article')
        if main_content:
            self._clean_content_element(main_content)
            result['content'] = main_content.get_text(strip=True, separator=' ')
            
        # Extrait les exemples de code
        code_blocks = soup.find_all(['code', 'pre'])
        code_content = []
        for block in code_blocks:
            code_text = block.get_text(strip=True)
            if len(code_text) > 10:  # Ignore les petits snippets
                code_content.append(code_text)
                
        if code_content:
            result['content'] += '\\n\\nCode Examples:\\n' + '\\n'.join(code_content)
            
        return result
        
    async def _extract_forum_content(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extrait le contenu de forum/discussion"""
        result = {
            'title': '',
            'content': '',
            'author': '',
            'published_at': None,
            'tags': [],
            'category': 'forum'
        }
        
        # Titre du thread
        title_elem = soup.find('h1') or soup.find('.thread-title')
        if title_elem:
            result['title'] = title_elem.get_text(strip=True)
            
        # Contenu du premier post
        post_selectors = [
            '.post-content',
            '.message-content',
            '.thread-content'
        ]
        
        for selector in post_selectors:
            post_elem = soup.select_one(selector)
            if post_elem:
                self._clean_content_element(post_elem)
                result['content'] = post_elem.get_text(strip=True, separator=' ')
                break
                
        # Auteur du post original
        author_elem = soup.select_one('.post-author, .username, .author')
        if author_elem:
            result['author'] = author_elem.get_text(strip=True)
            
        return result
        
    async def _extract_tutorial_content(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extrait le contenu de tutoriel"""
        result = {
            'title': '',
            'content': '',
            'author': '',
            'published_at': None,
            'tags': [],
            'category': 'tutorial'
        }
        
        # Similaire à l'extraction d'article mais avec focus sur les étapes
        title_elem = soup.find('h1')
        if title_elem:
            result['title'] = title_elem.get_text(strip=True)
            
        # Recherche le contenu structuré
        content_elem = soup.find('article') or soup.find('.tutorial-content') or soup.find('main')
        if content_elem:
            self._clean_content_element(content_elem)
            result['content'] = content_elem.get_text(strip=True, separator=' ')
            
        # Extrait les étapes du tutoriel
        steps = soup.find_all(['h2', 'h3', 'h4'])
        if steps:
            step_content = []
            for step in steps:
                step_title = step.get_text(strip=True)
                if any(word in step_title.lower() for word in ['step', 'étape', 'phase']):
                    step_content.append(step_title)
                    
            if step_content:
                result['content'] += '\\n\\nTutorial Steps:\\n' + '\\n'.join(step_content)
                
        return result
        
    async def _extract_general_content(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extraction générique pour les pages non spécialisées"""
        result = {
            'title': '',
            'content': '',
            'author': '',
            'published_at': None,
            'tags': [],
            'category': 'general'
        }
        
        # Titre de la page
        title_elem = soup.find('title')
        if title_elem:
            result['title'] = title_elem.get_text(strip=True)
            
        # Contenu principal - essaie plusieurs stratégies
        main_elem = (soup.find('main') or 
                    soup.find('article') or 
                    soup.find('.content') or
                    soup.find('#content'))
                    
        if main_elem:
            self._clean_content_element(main_elem)
            result['content'] = main_elem.get_text(strip=True, separator=' ')
        else:
            # Fallback : extrait tout le texte du body
            body = soup.find('body')
            if body:
                self._clean_content_element(body)
                result['content'] = body.get_text(strip=True, separator=' ')
                
        return result
        
    def _clean_content_element(self, element):
        """Nettoie un élément HTML en supprimant les éléments indésirables"""
        # Supprime les scripts, styles, et autres éléments non pertinents
        for tag in element(['script', 'style', 'nav', 'header', 'footer', 
                           'aside', 'advertisement', '.ad']):
            tag.decompose()
            
        # Supprime les attributs inutiles
        for tag in element.find_all(True):
            tag.attrs = {}
            
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse une chaîne de date en objet datetime"""
        if not date_str:
            return None
            
        # Formats de date communs
        date_formats = [
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%m/%d/%Y'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
                
        return None
        
    def get_content_quality_score(self, extracted_content: Dict[str, Any]) -> float:
        """Calcule un score de qualité pour le contenu extrait"""
        score = 0.0
        
        # Vérifie la présence des éléments clés
        if extracted_content.get('title'):
            score += 0.2
            
        if extracted_content.get('content') and len(extracted_content['content']) > 500:
            score += 0.3
            
        if extracted_content.get('author'):
            score += 0.1
            
        if extracted_content.get('published_at'):
            score += 0.1
            
        if extracted_content.get('tags'):
            score += 0.1
            
        # Qualité du contenu
        content = extracted_content.get('content', '')
        if content:
            # Vérifie la présence de mots techniques
            tech_keywords = ['function', 'class', 'method', 'algorithm', 'code', 'example']
            tech_count = sum(1 for keyword in tech_keywords if keyword in content.lower())
            score += min(tech_count * 0.05, 0.2)
            
        return min(score, 1.0)
