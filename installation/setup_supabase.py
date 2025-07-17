#!/usr/bin/env python3
"""
Script simplifié de configuration Supabase
"""
import asyncio
import os
from dotenv import load_dotenv
import asyncpg

async def main():
    print("🚀 Configuration Supabase PostgreSQL")
    print("=" * 50)
    
    # Charger les variables d'environnement
    load_dotenv()
    
    # Récupérer l'URL de connexion
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL non trouvée dans .env")
        return
    
    print(f"📍 Connexion à Supabase...")
    
    try:
        # Connexion à la base (avec désactivation du cache pour Transaction Pooler)
        conn = await asyncpg.connect(database_url, statement_cache_size=0)
        print("✅ Connexion réussie!")
        
        # Test basique
        result = await conn.fetchval("SELECT NOW()")
        print(f"🕐 Heure serveur: {result}")
        
        # Vérifier les extensions
        extensions = await conn.fetch("""
            SELECT extname, extversion 
            FROM pg_extension 
            WHERE extname IN ('uuid-ossp', 'pg_trgm', 'unaccent', 'vector')
            ORDER BY extname
        """)
        
        print("\n🔧 Extensions disponibles:")
        for ext in extensions:
            print(f"   ✅ {ext['extname']} (v{ext['extversion']})")
        
        # Créer les tables de base (simplifié)
        print("\n📊 Création des tables de base...")
        
        # Table sources
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(255) NOT NULL,
                url VARCHAR(2048) NOT NULL UNIQUE,
                domain VARCHAR(255) NOT NULL,
                source_type VARCHAR(50) NOT NULL DEFAULT 'blog',
                category VARCHAR(100) NOT NULL DEFAULT 'tech',
                is_active BOOLEAN NOT NULL DEFAULT true,
                quality_score FLOAT DEFAULT 0.0,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        print("   ✅ Table 'sources' créée")
        
        # Table articles
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                source_id UUID REFERENCES sources(id),
                title VARCHAR(1000) NOT NULL,
                url VARCHAR(2048) NOT NULL UNIQUE,
                content_hash VARCHAR(64) NOT NULL,
                content TEXT NOT NULL,
                summary TEXT,
                author VARCHAR(255),
                published_at TIMESTAMPTZ,
                language VARCHAR(10) DEFAULT 'en',
                word_count INTEGER DEFAULT 0,
                category VARCHAR(100) NOT NULL,
                quality_score FLOAT DEFAULT 0.0,
                is_processed BOOLEAN DEFAULT false,
                crawled_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        print("   ✅ Table 'articles' créée")
        
        # Table crawl_jobs
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS crawl_jobs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                source_id UUID REFERENCES sources(id),
                job_type VARCHAR(50) NOT NULL DEFAULT 'discovery',
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                priority INTEGER DEFAULT 1,
                progress FLOAT DEFAULT 0.0,
                pages_crawled INTEGER DEFAULT 0,
                new_articles_found INTEGER DEFAULT 0,
                started_at TIMESTAMPTZ,
                completed_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        print("   ✅ Table 'crawl_jobs' créée")
        
        # Vérifier les tables créées
        tables = await conn.fetch("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename IN ('sources', 'articles', 'crawl_jobs')
            ORDER BY tablename
        """)
        
        print(f"\n📋 Tables créées: {len(tables)}")
        for table in tables:
            print(f"   ✅ {table['tablename']}")
        
        await conn.close()
        
        print("\n" + "=" * 50)
        print("🎉 Configuration terminée avec succès!")
        print("\n💡 Prochaines étapes:")
        print("   1. Vérifiez vos tables dans le dashboard Supabase")
        print("   2. Démarrez l'application: python src/main.py")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    asyncio.run(main())
