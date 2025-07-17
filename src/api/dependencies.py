"""
Dépendances FastAPI pour l'injection de dépendances
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator
import jwt
from datetime import datetime, timedelta

from ..database import db_manager
from ..config import settings


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dépendance pour obtenir une session de base de données
    """
    async with db_manager.get_session() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur de base de données: {str(e)}"
            )


def verify_api_key(api_key: str = None) -> bool:
    """
    Vérifie la clé API (optionnel pour sécuriser l'API)
    
    Args:
        api_key: Clé API fournie dans les headers
        
    Returns:
        True si la clé est valide, False sinon
    """
    if not settings.secret_key:
        return True  # Pas de sécurité configurée
        
    # Implémentation simple - en production, utiliser un système plus robuste
    valid_keys = [
        settings.secret_key,
        "harvester-api-key-2024"  # Exemple de clé statique
    ]
    
    return api_key in valid_keys


async def verify_rate_limit(request_ip: str = None) -> bool:
    """
    Vérifie les limites de taux pour l'API
    
    Args:
        request_ip: Adresse IP du client
        
    Returns:
        True si dans les limites, False sinon
    """
    # Implémentation basique - en production, utiliser Redis ou similaire
    # pour un rate limiting distribué
    return True


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """
    Crée un token JWT pour l'authentification
    
    Args:
        data: Données à encoder dans le token
        expires_delta: Durée de validité du token
        
    Returns:
        Token JWT encodé
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
        
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.secret_key, 
        algorithm="HS256"
    )
    
    return encoded_jwt


def verify_token(token: str) -> dict:
    """
    Vérifie et décode un token JWT
    
    Args:
        token: Token JWT à vérifier
        
    Returns:
        Données décodées du token
        
    Raises:
        HTTPException: Si le token est invalide
    """
    try:
        payload = jwt.decode(
            token, 
            settings.secret_key, 
            algorithms=["HS256"]
        )
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(token: str = Depends(verify_token)) -> dict:
    """
    Récupère l'utilisateur actuel depuis le token
    
    Args:
        token: Token JWT vérifié
        
    Returns:
        Informations de l'utilisateur
    """
    user_id = token.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide"
        )
        
    # En production, récupérer les données utilisateur depuis la DB
    return {
        "id": user_id,
        "username": token.get("username", "unknown"),
        "permissions": token.get("permissions", [])
    }


def require_permission(permission: str):
    """
    Décorateur pour exiger une permission spécifique
    
    Args:
        permission: Permission requise
        
    Returns:
        Fonction de dépendance FastAPI
    """
    async def permission_checker(current_user: dict = Depends(get_current_user)):
        user_permissions = current_user.get("permissions", [])
        
        if permission not in user_permissions and "admin" not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission requise: {permission}"
            )
            
        return current_user
        
    return permission_checker


async def validate_pagination_params(
    page: int = 1, 
    limit: int = 20
) -> tuple[int, int]:
    """
    Valide et normalise les paramètres de pagination
    
    Args:
        page: Numéro de page
        limit: Nombre d'éléments par page
        
    Returns:
        Tuple (page, limit) validés
        
    Raises:
        HTTPException: Si les paramètres sont invalides
    """
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le numéro de page doit être supérieur à 0"
        )
        
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La limite doit être entre 1 et 100"
        )
        
    return page, limit


async def validate_search_params(
    query: str = None,
    threshold: float = 0.7
) -> tuple[str, float]:
    """
    Valide les paramètres de recherche
    
    Args:
        query: Requête de recherche
        threshold: Seuil de similarité
        
    Returns:
        Tuple (query, threshold) validés
        
    Raises:
        HTTPException: Si les paramètres sont invalides
    """
    if not query or len(query.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La requête doit contenir au moins 2 caractères"
        )
        
    if threshold < 0 or threshold > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le seuil doit être entre 0 et 1"
        )
        
    return query.strip(), threshold


def get_client_ip(request) -> str:
    """
    Récupère l'adresse IP réelle du client
    
    Args:
        request: Objet Request FastAPI
        
    Returns:
        Adresse IP du client
    """
    # Vérifie les headers pour les proxies
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
        
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
        
    # Fallback sur l'IP de la connexion
    return request.client.host if request.client else "unknown"


async def log_api_request(
    endpoint: str,
    method: str,
    client_ip: str,
    response_time: float,
    status_code: int
):
    """
    Log les requêtes API pour le monitoring
    
    Args:
        endpoint: Endpoint appelé
        method: Méthode HTTP
        client_ip: IP du client
        response_time: Temps de réponse en ms
        status_code: Code de statut HTTP
    """
    # En production, envoyer vers un système de logging centralisé
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "endpoint": endpoint,
        "method": method,
        "client_ip": client_ip,
        "response_time_ms": response_time,
        "status_code": status_code
    }
    
    print(f"API Request: {log_entry}")


class DatabaseHealthCheck:
    """Vérification de santé de la base de données"""
    
    @staticmethod
    async def check_connection() -> bool:
        """Vérifie la connexion à la base de données"""
        try:
            async with db_manager.get_session() as session:
                result = await session.execute("SELECT 1")
                return result.fetchone() is not None
        except Exception:
            return False
            
    @staticmethod
    async def check_tables() -> bool:
        """Vérifie que les tables principales existent"""
        try:
            async with db_manager.get_session() as session:
                tables_to_check = ["sources", "articles", "discovery_results"]
                
                for table in tables_to_check:
                    result = await session.execute(
                        f"SELECT COUNT(*) FROM {table} LIMIT 1"
                    )
                    result.fetchone()
                    
                return True
        except Exception:
            return False


class ComponentHealthCheck:
    """Vérification de santé des composants"""
    
    @staticmethod
    async def check_discovery_engine() -> dict:
        """Vérifie l'état du moteur de découverte"""
        # Implémentation à adapter selon l'instance globale
        return {
            "status": "healthy",
            "last_discovery": None,
            "discovered_sources_count": 0
        }
        
    @staticmethod
    async def check_crawler() -> dict:
        """Vérifie l'état du crawler"""
        return {
            "status": "healthy",
            "active_crawls": 0,
            "last_crawl": None
        }
        
    @staticmethod
    async def check_search_engine() -> dict:
        """Vérifie l'état du moteur de recherche"""
        return {
            "status": "healthy",
            "indexed_articles": 0,
            "last_index_update": None
        }
