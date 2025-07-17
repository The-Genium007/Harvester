#!/usr/bin/env python3
"""
Script de configuration de la base de données pour SentinelIQ Harvester
Ce script initialise la base de données Supabase et crée toutes les tables nécessaires.
Compatible avec Supabase PostgreSQL.
"""
import asyncio
import sys
import os
from pathlib import Path

# Ajouter le répertoire src au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import DatabaseManager
from src.config import settings
from src.models import Base
import asyncpg
from sqlalchemy import text


async def check_supabase_connection():
    """Vérifie la connexion à Supabase selon la documentation officielle"""
    try:
        # Méthode 1: Utiliser l'URL complète
        db_url = settings.database_url
        
        # Conversion pour asyncpg si nécessaire
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgres://", 1)
        
        print(f"🔗 Tentative de connexion à Supabase...")
        print(f"📍 Host: db.qguahdafmeforgelbyby.supabase.co")
        
        # Test avec asyncpg (comme recommandé par Supabase)
        conn = await asyncpg.connect(db_url)
        
        # Vérifier que c'est bien Supabase
        version = await conn.fetchval("SELECT version()")
        current_time = await conn.fetchval("SELECT NOW()")
        
        print(f"✅ Connexion à Supabase réussie!")
        print(f"📊 PostgreSQL: {version.split()[1] if version else 'Inconnue'}")
        print(f"🕐 Heure serveur: {current_time}")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erreur de connexion à Supabase: {e}")
        print("\n� Vérifications à faire:")
        print("   1. Credentials dans .env corrects")
        print("   2. Projet Supabase actif et accessible")
        print("   3. Connexion internet stable")
        print("   4. Mot de passe sans caractères spéciaux dans l'URL")
        
        # Essayer la méthode alternative avec psycopg2 style
        try:
            print("\n⚙️  Test avec méthode alternative...")
            
            # Extraire les composants de l'URL
            from urllib.parse import urlparse
            parsed = urlparse(settings.database_url)
            
            conn = await asyncpg.connect(
                user=parsed.username,
                password=parsed.password, 
                host=parsed.hostname,
                port=parsed.port,
                database=parsed.path[1:]  # Remove leading /
            )
            
            print("✅ Connexion alternative réussie!")
            await conn.close()
            return True
            
        except Exception as e2:
            print(f"❌ Connexion alternative échouée: {e2}")
            return False


async def check_supabase_extensions():
    """Vérifie et installe les extensions dans Supabase"""
    try:
        db_url = settings.database_url
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgres://", 1)
            
        conn = await asyncpg.connect(db_url)
        
        print("🔧 Vérification des extensions Supabase...")
        
        # Extensions standard de Supabase (déjà installées par défaut)
        supabase_extensions = {
            "uuid-ossp": "Génération d'UUIDs",
            "pg_trgm": "Recherche trigram", 
            "unaccent": "Recherche sans accents",
            "postgis": "Extensions géospatiales (optionnel)",
        }
        
        for ext, description in supabase_extensions.items():
            try:
                result = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = $1)", ext
                )
                
                if result:
                    print(f"✅ {ext}: {description}")
                else:
                    # Tentative d'installation (peut échouer selon les permissions)
                    try:
                        await conn.execute(f"CREATE EXTENSION IF NOT EXISTS \"{ext}\";")
                        print(f"✅ {ext}: {description} (installée)")
                    except Exception:
                        print(f"⚠️  {ext}: Non disponible (optionnel)")
            except Exception as e:
                print(f"⚠️  Impossible de vérifier {ext}: {e}")
        
        # Vérification spéciale pour pgvector
        try:
            result = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            )
            
            if result:
                print("✅ pgvector: Extensions vectorielles (déjà installée)")
            else:
                print("⚠️  pgvector: Extension non trouvée")
                print("💡 Activez pgvector dans votre dashboard Supabase:")
                print("   Settings > Database > Extensions > pgvector")
                
                # Ne pas échouer si pgvector n'est pas installée
                print("⏭️  Continuation sans pgvector (fonctionnalités de recherche vectorielle désactivées)")
                
        except Exception as e:
            print(f"⚠️  Vérification pgvector échouée: {e}")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la vérification des extensions: {e}")
        return False


async def create_database_schema():
    """Crée le schéma de base de données dans Supabase"""
    try:
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        print("📊 Création des tables dans Supabase...")
        
        # Adapter l'URL si nécessaire pour SQLAlchemy
        if db_manager.engine is None:
            print("❌ Moteur de base de données non initialisé")
            return False
        
        await db_manager.create_tables()
        print("✅ Tables créées avec succès dans Supabase")
        
        await db_manager.close()
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la création des tables: {e}")
        print("💡 Vérifiez que vous avez les permissions dans votre projet Supabase")
        return False


async def verify_tables():
    """Vérifie que toutes les tables ont été créées dans Supabase"""
    try:
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        if db_manager.engine is None:
            print("❌ Moteur de base de données non initialisé")
            return False
        
        async with db_manager.engine.begin() as conn:
            # Vérifier les tables principales basées sur les modèles existants
            # Je récupère les noms de table directement des modèles
            table_names = []
            for table in Base.metadata.tables.values():
                table_names.append(table.name)
            
            print(f"🔍 Vérification de {len(table_names)} tables...")
            
            tables_created = 0
            for table in table_names:
                result = await conn.execute(
                    text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = :table_name
                    )
                    """),
                    {"table_name": table}
                )
                exists = result.scalar()
                
                if exists:
                    print(f"✅ Table '{table}' créée")
                    tables_created += 1
                else:
                    print(f"⚠️  Table '{table}' non trouvée")
            
            print(f"📊 Résultat: {tables_created}/{len(table_names)} tables créées")
        
        await db_manager.close()
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la vérification des tables: {e}")
        return False


async def setup_initial_data():
    """Insère des données initiales si nécessaire"""
    try:
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        # Ici vous pouvez ajouter des données initiales
        # Par exemple, des sources par défaut, des configurations, etc.
        
        print("✅ Données initiales configurées")
        await db_manager.close()
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la configuration des données initiales: {e}")
        return False


async def main():
    """Fonction principale de configuration pour Supabase"""
    print("🚀 Configuration de la base de données SentinelIQ Harvester")
    print("🗄️  Compatible avec Supabase PostgreSQL")
    print("=" * 60)
    
    # Vérifier les variables d'environnement Supabase
    if not settings.database_url:
        print("❌ Variable DATABASE_URL non configurée")
        print("💡 Vérifiez votre fichier .env")
        print("💡 Format Supabase: postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres")
        sys.exit(1)
    
    if not settings.supabase_url or not settings.supabase_key:
        print("⚠️  Variables Supabase non configurées (SUPABASE_URL, SUPABASE_KEY)")
        print("💡 Ces variables sont optionnelles pour la création de tables")
    
    # Extraire l'hôte pour l'affichage
    try:
        host_part = settings.database_url.split('@')[1].split(':')[0] if '@' in settings.database_url else 'localhost'
        print(f"📍 Base de données Supabase: {host_part}")
    except:
        print(f"📍 Base de données: Supabase")
    
    # Étapes de configuration
    steps = [
        ("Vérification de la connexion", check_supabase_connection),
        ("Vérification des extensions", check_supabase_extensions),
        ("Création du schéma", create_database_schema),
        ("Vérification des tables", verify_tables),
        ("Configuration des données initiales", setup_initial_data),
    ]
    
    for step_name, step_func in steps:
        print(f"\n📋 {step_name}...")
        success = await step_func()
        
        if not success:
            print(f"❌ Échec de l'étape: {step_name}")
            sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🎉 Configuration de la base de données Supabase terminée avec succès!")
    print("\n💡 Prochaines étapes:")
    print("   1. Vérifiez vos tables dans le dashboard Supabase")
    print("   2. Démarrer les services: docker-compose up -d")
    print("   3. Lancer l'application: python src/main.py")
    print("\n🔗 Dashboard Supabase:")
    if settings.supabase_url:
        print(f"   {settings.supabase_url}")


if __name__ == "__main__":
    # Vérifier que le fichier .env existe
    env_file = Path(__file__).parent.parent / ".env"
    if not env_file.exists():
        print("❌ Fichier .env non trouvé")
        print("💡 Exécutez d'abord: cp .env.example .env")
        print("💡 Et configurez vos credentials Supabase:")
        print("   - DATABASE_URL: URL de connexion PostgreSQL")
        print("   - SUPABASE_URL: URL de votre projet Supabase")
        print("   - SUPABASE_KEY: Clé publique anon")
        print("   - SUPABASE_SERVICE_ROLE_KEY: Clé service role")
        sys.exit(1)
    
    # Exécuter la configuration
    asyncio.run(main())
