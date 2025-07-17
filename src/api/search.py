"""
Moteur de recherche sémantique avec embeddings
"""
import asyncio
import numpy as np
from typing import List, Dict, Optional, Any
from datetime import datetime
try:
    import openai
except ImportError:
    openai = None

from ..config import settings
from ..database import db_manager
from ..models import Article


class SemanticSearchEngine:
    """
    Moteur de recherche sémantique qui utilise les embeddings
    pour trouver des articles similaires sémantiquement
    """
    
    def __init__(self):
        self.openai_client = None
        self.embedding_model = settings.openai_model
        self.cache: Dict[str, List[float]] = {}
        
    async def initialize(self):
        """Initialise le moteur de recherche"""
        if settings.openai_api_key and openai:
            openai.api_key = settings.openai_api_key
            self.openai_client = openai
            
    async def close(self):
        """Ferme les ressources"""
        pass
        
    async def search(self, query: str, limit: int = 10, 
                    threshold: float = 0.7, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Recherche sémantique dans les articles
        
        Args:
            query: Requête de recherche
            limit: Nombre de résultats à retourner
            threshold: Seuil de similarité minimum
            category: Filtrer par catégorie
            
        Returns:
            Liste des articles trouvés avec leurs scores
        """
        start_time = datetime.now()
        
        # Génère l'embedding de la requête
        query_embedding = await self._get_embedding(query)
        if not query_embedding:
            return []
            
        # Recherche dans la base de données
        results = await self._search_similar_articles(
            query_embedding, limit, threshold, category
        )
        
        # Calcule le temps de traitement
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Formate les résultats
        formatted_results = []
        for result in results:
            formatted_result = {
                "article_id": result["id"],
                "title": result["title"],
                "url": result["url"],
                "content_preview": result["content"][:500] + "..." if len(result["content"]) > 500 else result["content"],
                "similarity_score": result["similarity_score"],
                "quality_score": result["quality_score"],
                "published_at": result["published_at"],
                "category": result["category"],
                "tags": result["tags"] or [],
                "processing_time": processing_time
            }
            formatted_results.append(formatted_result)
            
        return formatted_results
        
    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Génère un embedding pour un texte donné
        
        Args:
            text: Texte à encoder
            
        Returns:
            Vecteur d'embedding ou None si échec
        """
        # Vérifie le cache
        if text in self.cache:
            return self.cache[text]
            
        if not self.openai_client or not settings.openai_api_key:
            # Fallback : utilise un embedding factice pour les tests
            return self._generate_mock_embedding(text)
            
        try:
            if self.openai_client and openai:
                response = openai.embeddings.create(
                    model=self.embedding_model,
                    input=text
                )
                
                embedding = response.data[0].embedding
            else:
                return self._generate_mock_embedding(text)
            
            # Met en cache
            self.cache[text] = embedding
            
            return embedding
            
        except Exception as e:
            print(f"Erreur lors de la génération d'embedding: {e}")
            return self._generate_mock_embedding(text)
            
    def _generate_mock_embedding(self, text: str) -> List[float]:
        """
        Génère un embedding factice pour les tests
        (en production, utiliser un vrai modèle d'embedding)
        """
        # Crée un embedding basique basé sur le hash du texte
        import hashlib
        hash_object = hashlib.md5(text.encode())
        hash_hex = hash_object.hexdigest()
        
        # Convertit en vecteur de dimension 1536 (taille d'OpenAI ada-002)
        embedding = []
        for i in range(0, len(hash_hex), 2):
            val = int(hash_hex[i:i+2], 16) / 255.0 - 0.5  # Normalise entre -0.5 et 0.5
            embedding.append(val)
            
        # Complète ou tronque à 1536 dimensions
        while len(embedding) < 1536:
            embedding.extend(embedding[:min(len(embedding), 1536 - len(embedding))])
            
        return embedding[:1536]
        
    async def _search_similar_articles(self, query_embedding: List[float], 
                                     limit: int, threshold: float,
                                     category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Recherche les articles similaires dans la base de données
        """
        async with db_manager.get_session() as session:
            # Construction de la requête
            query_parts = [
                """
                SELECT 
                    id, title, url, content, quality_score, 
                    published_at, category, tags,
                    (content_embedding <=> %s::vector) as similarity_distance
                FROM articles 
                WHERE content_embedding IS NOT NULL
                """
            ]
            
            params = [str(query_embedding)]
            
            if category:
                query_parts.append("AND category = %s")
                params.append(category)
                
            # Convertit distance en similarité et filtre
            query_parts.append("AND (1 - (content_embedding <=> %s::vector)) >= %s")
            params.extend([str(query_embedding), str(threshold)])
            
            query_parts.append("ORDER BY similarity_distance ASC LIMIT %s")
            params.append(str(limit))
            
            full_query = " ".join(query_parts)
            
            try:
                result = await session.execute(full_query, params)
                rows = result.fetchall()
                
                articles = []
                for row in rows:
                    similarity_score = 1 - row[-1]  # Convertit distance en similarité
                    
                    article = {
                        "id": row[0],
                        "title": row[1],
                        "url": row[2],
                        "content": row[3],
                        "quality_score": row[4],
                        "published_at": row[5],
                        "category": row[6],
                        "tags": row[7],
                        "similarity_score": similarity_score
                    }
                    articles.append(article)
                    
                return articles
                
            except Exception as e:
                print(f"Erreur lors de la recherche vectorielle: {e}")
                # Fallback : recherche textuelle simple
                return await self._fallback_text_search(query_embedding, limit, category)
                
    async def _fallback_text_search(self, query_embedding: List[float], 
                                   limit: int, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Recherche textuelle de fallback si la recherche vectorielle échoue
        """
        # Implémentation simplifiée pour le fallback
        # En production, utiliser un moteur de recherche full-text comme Elasticsearch
        
        async with db_manager.get_session() as session:
            query_parts = [
                """
                SELECT id, title, url, content, quality_score, 
                       published_at, category, tags
                FROM articles 
                WHERE 1=1
                """
            ]
            
            params = []
            
            if category:
                query_parts.append("AND category = %s")
                params.append(str(category))
                
            query_parts.append("ORDER BY quality_score DESC LIMIT %s")
            params.append(str(limit))
            
            full_query = " ".join(query_parts)
            
            result = await session.execute(full_query, params)
            rows = result.fetchall()
            
            articles = []
            for row in rows:
                article = {
                    "id": row[0],
                    "title": row[1],
                    "url": row[2],
                    "content": row[3],
                    "quality_score": row[4],
                    "published_at": row[5],
                    "category": row[6],
                    "tags": row[7],
                    "similarity_score": 0.5  # Score neutre pour le fallback
                }
                articles.append(article)
                
            return articles
            
    async def index_article(self, article: Article) -> bool:
        """
        Indexe un article (génère et stocke ses embeddings)
        
        Args:
            article: Article à indexer
            
        Returns:
            True si indexé avec succès, False sinon
        """
        try:
            # Génère l'embedding du contenu
            content_text = f"{article.title} {article.content}"
            content_embedding = await self._get_embedding(content_text)
            
            # Génère l'embedding du titre
            title_embedding = await self._get_embedding(article.title)
            
            if content_embedding and title_embedding:
                # Met à jour l'article avec les embeddings
                async with db_manager.get_session() as session:
                    await session.execute("""
                        UPDATE articles 
                        SET content_embedding = %s::vector,
                            title_embedding = %s::vector,
                            is_processed = true,
                            processed_at = NOW()
                        WHERE id = %s
                    """, (str(content_embedding), str(title_embedding), article.id))
                    
                    await session.commit()
                    
                return True
                
        except Exception as e:
            print(f"Erreur lors de l'indexation de l'article {article.id}: {e}")
            
        return False
        
    async def reindex_articles(self, batch_size: int = 10) -> Dict[str, int]:
        """
        Réindexe tous les articles non traités
        
        Args:
            batch_size: Taille des batches de traitement
            
        Returns:
            Statistiques de réindexation
        """
        stats = {
            "processed": 0,
            "failed": 0,
            "skipped": 0
        }
        
        async with db_manager.get_session() as session:
            # Récupère les articles non traités
            result = await session.execute("""
                SELECT id, title, content 
                FROM articles 
                WHERE is_processed = false 
                   OR content_embedding IS NULL
                ORDER BY crawled_at DESC
                LIMIT 1000
            """)
            
            articles = result.fetchall()
            
            # Traite par batches
            for i in range(0, len(articles), batch_size):
                batch = articles[i:i + batch_size]
                
                tasks = []
                for article_data in batch:
                    article_id, title, content = article_data
                    
                    # Crée un article pour indexation
                    from ..models import Article as ArticleModel
                    
                    temp_article = ArticleModel(
                        id=article_id,
                        title=title,
                        content=content
                    )
                    
                    task = self.index_article(temp_article)
                    tasks.append(task)
                    
                # Exécute le batch
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, Exception):
                        stats["failed"] += 1
                    elif result:
                        stats["processed"] += 1
                    else:
                        stats["failed"] += 1
                        
                # Pause entre les batches
                await asyncio.sleep(1)
                
        return stats
        
    async def get_similar_articles(self, article_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Trouve les articles similaires à un article donné
        
        Args:
            article_id: ID de l'article de référence
            limit: Nombre d'articles similaires à retourner
            
        Returns:
            Liste des articles similaires
        """
        async with db_manager.get_session() as session:
            # Récupère l'embedding de l'article de référence
            result = await session.execute("""
                SELECT content_embedding, title, category 
                FROM articles 
                WHERE id = %s AND content_embedding IS NOT NULL
            """, (article_id,))
            
            article_data = result.fetchone()
            if not article_data:
                return []
                
            reference_embedding = article_data[0]
            reference_category = article_data[2]
            
            # Trouve les articles similaires
            similar_result = await session.execute("""
                SELECT 
                    id, title, url, category, quality_score,
                    (content_embedding <=> %s::vector) as distance
                FROM articles 
                WHERE id != %s 
                  AND content_embedding IS NOT NULL
                  AND category = %s
                ORDER BY distance ASC 
                LIMIT %s
            """, (str(reference_embedding), article_id, reference_category, limit))
            
            similar_articles = []
            for row in similar_result.fetchall():
                similarity_score = 1 - row[5]  # Convertit distance en similarité
                
                article = {
                    "id": row[0],
                    "title": row[1],
                    "url": row[2],
                    "category": row[3],
                    "quality_score": row[4],
                    "similarity_score": similarity_score
                }
                similar_articles.append(article)
                
            return similar_articles
            
    async def get_search_suggestions(self, partial_query: str, limit: int = 5) -> List[str]:
        """
        Génère des suggestions de recherche basées sur une requête partielle
        
        Args:
            partial_query: Début de requête
            limit: Nombre de suggestions
            
        Returns:
            Liste de suggestions
        """
        async with db_manager.get_session() as session:
            # Recherche dans les titres et tags populaires
            result = await session.execute("""
                SELECT title, tags 
                FROM articles 
                WHERE title ILIKE %s 
                   OR EXISTS (
                       SELECT 1 FROM unnest(tags) as tag 
                       WHERE tag ILIKE %s
                   )
                ORDER BY quality_score DESC 
                LIMIT %s
            """, (f"%{partial_query}%", f"%{partial_query}%", limit * 2))
            
            suggestions = set()
            for row in result.fetchall():
                title = row[0]
                tags = row[1] or []
                
                # Ajoute le titre comme suggestion
                if partial_query.lower() in title.lower():
                    suggestions.add(title)
                    
                # Ajoute les tags pertinents
                for tag in tags:
                    if partial_query.lower() in tag.lower():
                        suggestions.add(tag)
                        
                if len(suggestions) >= limit:
                    break
                    
            return list(suggestions)[:limit]
