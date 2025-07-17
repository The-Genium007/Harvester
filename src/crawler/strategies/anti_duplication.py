"""
Moteur anti-duplication intelligent
"""
import asyncio
import hashlib
from typing import Dict, Optional, Set, List, Tuple
from datetime import datetime, timedelta
import re
from difflib import SequenceMatcher

from ...database import db_manager
from ...models import ContentHash, Article


class AntiDuplicationEngine:
    """
    Moteur anti-duplication qui :
    1. Détecte les contenus identiques via hash
    2. Identifie les contenus similaires
    3. Gère les versions mises à jour
    4. Optimise les performances avec cache
    """
    
    def __init__(self):
        self.hash_cache: Dict[str, bool] = {}  # Cache des hashes connus
        self.similarity_threshold = 0.85
        self.content_cache: Dict[str, str] = {}  # Cache du contenu pour comparaison
        
    async def initialize(self):
        """Initialise le moteur anti-duplication"""
        await self._load_known_hashes()
        
    async def close(self):
        """Ferme les ressources"""
        pass
        
    async def _load_known_hashes(self):
        """Charge les hashes connus en mémoire pour optimiser les performances"""
        async with db_manager.get_session() as session:
            result = await session.execute("""
                SELECT content_hash FROM content_hashes 
                WHERE first_seen_at > NOW() - INTERVAL '30 days'
            """)
            
            known_hashes = result.fetchall()
            self.hash_cache = {row[0]: True for row in known_hashes}
            
    async def is_duplicate(self, content_hash: str, url: str, 
                          content: Optional[str] = None) -> bool:
        """
        Vérifie si un contenu est un duplicata
        
        Args:
            content_hash: Hash du contenu
            url: URL du contenu
            content: Contenu textuel optionnel pour analyse de similarité
            
        Returns:
            True si c'est un duplicata, False sinon
        """
        # Vérification rapide par hash exact
        if content_hash in self.hash_cache:
            return True
            
        # Vérification en base de données
        if await self._check_exact_duplicate(content_hash):
            self.hash_cache[content_hash] = True
            return True
            
        # Vérification de similarité si contenu fourni
        if content and len(content) > 200:
            is_similar = await self._check_content_similarity(content, url)
            if is_similar:
                return True
                
        return False
        
    async def _check_exact_duplicate(self, content_hash: str) -> bool:
        """Vérifie si le hash existe déjà en base"""
        async with db_manager.get_session() as session:
            result = await session.execute("""
                SELECT id FROM content_hashes 
                WHERE content_hash = %s
            """, (content_hash,))
            
            return result.fetchone() is not None
            
    async def _check_content_similarity(self, content: str, url: str) -> bool:
        """
        Vérifie la similarité avec les contenus existants
        en utilisant des techniques de comparaison textuelle
        """
        # Normalise le contenu pour la comparaison
        normalized_content = self._normalize_content(content)
        
        # Crée un hash de structure pour une recherche rapide
        structure_hash = self._create_structure_hash(normalized_content)
        
        # Recherche les contenus avec une structure similaire
        similar_contents = await self._find_similar_structure_contents(structure_hash)
        
        for similar_content in similar_contents:
            similarity = self._calculate_similarity(normalized_content, similar_content)
            if similarity >= self.similarity_threshold:
                return True
                
        return False
        
    def _normalize_content(self, content: str) -> str:
        """Normalise le contenu pour la comparaison"""
        # Supprime les espaces supplémentaires
        normalized = re.sub(r'\\s+', ' ', content)
        
        # Supprime la ponctuation non significative
        normalized = re.sub(r'[.,;:!?()\\[\\]{}"\']', '', normalized)
        
        # Convertit en minuscules
        normalized = normalized.lower().strip()
        
        return normalized
        
    def _create_structure_hash(self, content: str) -> str:
        """Crée un hash basé sur la structure du contenu"""
        # Extrait les mots significatifs (longueur > 3)
        words = [word for word in content.split() if len(word) > 3]
        
        # Prend un échantillon représentatif
        if len(words) > 50:
            # Prend des mots au début, milieu et fin
            sample_words = words[:20] + words[len(words)//2-10:len(words)//2+10] + words[-20:]
        else:
            sample_words = words
            
        # Crée un hash de la structure
        structure_text = ' '.join(sorted(set(sample_words)))
        return hashlib.md5(structure_text.encode('utf-8')).hexdigest()
        
    async def _find_similar_structure_contents(self, structure_hash: str) -> List[str]:
        """Trouve les contenus avec une structure similaire"""
        # Pour l'optimisation, on pourrait stocker les structure_hash en base
        # Pour cette version, on fait une approche simplifiée
        
        async with db_manager.get_session() as session:
            # Récupère les contenus récents pour comparaison
            result = await session.execute("""
                SELECT content FROM articles 
                WHERE crawled_at > NOW() - INTERVAL '7 days'
                  AND LENGTH(content) BETWEEN %s AND %s
                ORDER BY crawled_at DESC 
                LIMIT 100
            """, (len(structure_hash) * 10, len(structure_hash) * 30))
            
            contents = [row[0] for row in result.fetchall()]
            
        return contents
        
    def _calculate_similarity(self, content1: str, content2: str) -> float:
        """Calcule la similarité entre deux contenus"""
        if not content1 or not content2:
            return 0.0
            
        # Utilise SequenceMatcher pour calculer la similarité
        matcher = SequenceMatcher(None, content1, content2)
        return matcher.ratio()
        
    async def register_content_hash(self, content_hash: str, url: str, 
                                  article_id: str) -> bool:
        """
        Enregistre un nouveau hash de contenu
        
        Args:
            content_hash: Hash du contenu
            url: URL source
            article_id: ID de l'article associé
            
        Returns:
            True si enregistré avec succès, False si déjà existant
        """
        async with db_manager.get_session() as session:
            # Vérifie si le hash existe déjà
            existing = await session.execute("""
                SELECT id FROM content_hashes 
                WHERE content_hash = %s
            """, (content_hash,))
            
            if existing.fetchone():
                # Met à jour le compteur de duplicatas
                await session.execute("""
                    UPDATE content_hashes 
                    SET duplicate_count = duplicate_count + 1,
                        last_seen_at = NOW()
                    WHERE content_hash = %s
                """, (content_hash,))
                return False
            else:
                # Crée un nouvel enregistrement
                url_hash = hashlib.sha256(url.encode('utf-8')).hexdigest()
                
                content_hash_record = ContentHash(
                    content_hash=content_hash,
                    url_hash=url_hash,
                    content_length=len(content_hash),  # Approximation
                    first_article_id=article_id
                )
                
                session.add(content_hash_record)
                await session.commit()
                
                # Met à jour le cache
                self.hash_cache[content_hash] = True
                
                return True
                
    async def find_similar_articles(self, content: str, 
                                  threshold: float = None) -> List[Dict[str, any]]:
        """
        Trouve les articles similaires à un contenu donné
        
        Args:
            content: Contenu à comparer
            threshold: Seuil de similarité (par défaut utilise celui de la classe)
            
        Returns:
            Liste des articles similaires avec leurs scores
        """
        if threshold is None:
            threshold = self.similarity_threshold
            
        normalized_content = self._normalize_content(content)
        similar_articles = []
        
        async with db_manager.get_session() as session:
            # Récupère les articles récents pour comparaison
            result = await session.execute("""
                SELECT id, title, url, content, quality_score 
                FROM articles 
                WHERE crawled_at > NOW() - INTERVAL '30 days'
                  AND LENGTH(content) BETWEEN %s AND %s
                ORDER BY quality_score DESC 
                LIMIT 50
            """, (len(content) * 0.7, len(content) * 1.3))
            
            articles = result.fetchall()
            
            for article in articles:
                article_id, title, url, article_content, quality_score = article
                
                normalized_article = self._normalize_content(article_content)
                similarity = self._calculate_similarity(normalized_content, normalized_article)
                
                if similarity >= threshold:
                    similar_articles.append({
                        'id': article_id,
                        'title': title,
                        'url': url,
                        'similarity_score': similarity,
                        'quality_score': quality_score
                    })
                    
        # Trie par similarité décroissante
        similar_articles.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return similar_articles
        
    async def detect_content_update(self, original_content: str, 
                                  new_content: str) -> Dict[str, any]:
        """
        Détecte si un contenu a été mis à jour de manière significative
        
        Args:
            original_content: Contenu original
            new_content: Nouveau contenu
            
        Returns:
            Dictionnaire avec les informations de mise à jour
        """
        original_normalized = self._normalize_content(original_content)
        new_normalized = self._normalize_content(new_content)
        
        similarity = self._calculate_similarity(original_normalized, new_normalized)
        
        # Analyse des changements
        update_info = {
            'is_significant_update': similarity < 0.9,  # Seuil pour update significative
            'similarity_score': similarity,
            'content_length_change': len(new_content) - len(original_content),
            'change_percentage': 1 - similarity,
            'update_type': self._classify_update_type(similarity, original_content, new_content)
        }
        
        return update_info
        
    def _classify_update_type(self, similarity: float, original: str, new: str) -> str:
        """Classifie le type de mise à jour"""
        if similarity > 0.95:
            return 'minor_edit'
        elif similarity > 0.8:
            return 'content_update'
        elif similarity > 0.5:
            return 'major_revision'
        else:
            return 'complete_rewrite'
            
    async def cleanup_old_hashes(self, days_to_keep: int = 90) -> int:
        """
        Nettoie les anciens hashes pour maintenir les performances
        
        Args:
            days_to_keep: Nombre de jours à conserver
            
        Returns:
            Nombre de hashes supprimés
        """
        async with db_manager.get_session() as session:
            result = await session.execute("""
                DELETE FROM content_hashes 
                WHERE first_seen_at < NOW() - INTERVAL '%s days'
                  AND duplicate_count = 0
            """, (days_to_keep,))
            
            deleted_count = result.rowcount
            await session.commit()
            
            # Met à jour le cache
            await self._load_known_hashes()
            
            return deleted_count
            
    async def get_duplication_stats(self) -> Dict[str, any]:
        """Récupère les statistiques de duplication"""
        async with db_manager.get_session() as session:
            # Statistiques générales
            stats_result = await session.execute("""
                SELECT 
                    COUNT(*) as total_hashes,
                    SUM(duplicate_count) as total_duplicates,
                    AVG(duplicate_count) as avg_duplicates_per_hash,
                    COUNT(CASE WHEN duplicate_count > 0 THEN 1 END) as hashes_with_duplicates
                FROM content_hashes
            """)
            
            stats = stats_result.fetchone()
            
            # Top domaines avec duplicatas
            domains_result = await session.execute("""
                SELECT 
                    s.domain,
                    COUNT(ch.id) as hash_count,
                    SUM(ch.duplicate_count) as duplicate_count
                FROM content_hashes ch
                JOIN articles a ON ch.first_article_id = a.id
                JOIN sources s ON a.source_id = s.id
                GROUP BY s.domain
                ORDER BY duplicate_count DESC
                LIMIT 10
            """)
            
            top_domains = domains_result.fetchall()
            
            return {
                'total_hashes': stats[0] if stats else 0,
                'total_duplicates': stats[1] if stats else 0,
                'avg_duplicates_per_hash': float(stats[2]) if stats and stats[2] else 0.0,
                'hashes_with_duplicates': stats[3] if stats else 0,
                'top_duplicate_domains': [
                    {
                        'domain': domain,
                        'hash_count': hash_count,
                        'duplicate_count': duplicate_count
                    }
                    for domain, hash_count, duplicate_count in top_domains
                ],
                'cache_size': len(self.hash_cache)
            }
