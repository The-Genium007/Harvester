#!/usr/bin/env python3
"""
Test de connexion Supabase pour SentinelIQ Harvester
Ce script teste votre configuration Supabase avant l'installation
"""
import asyncio
import os
from dotenv import load_dotenv
import asyncpg

async def test_connection():
    """Test la connexion à Supabase"""
    print("🔗 Test de connexion Supabase...")
    
    # Charger les variables d'environnement
    load_dotenv()
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL non trouvée dans .env")
        print("💡 Assurez-vous d'avoir configuré votre fichier .env")
        return False
    
    try:
        # Connexion avec désactivation du cache pour Transaction Pooler
        conn = await asyncpg.connect(database_url, statement_cache_size=0)
        
        # Test basique
        result = await conn.fetchval("SELECT NOW()")
        version = await conn.fetchval("SELECT version()")
        
        print("✅ Connexion Supabase réussie!")
        print(f"🕐 Heure serveur: {result}")
        print(f"📊 PostgreSQL: {version.split()[1] if version else 'Inconnue'}")
        
        # Vérifier les extensions essentielles
        extensions = await conn.fetch("""
            SELECT extname, extversion 
            FROM pg_extension 
            WHERE extname IN ('uuid-ossp', 'pg_trgm', 'unaccent', 'vector')
            ORDER BY extname
        """)
        
        print("\n🔧 Extensions PostgreSQL:")
        essential_extensions = {'uuid-ossp', 'pg_trgm', 'unaccent'}
        found_extensions = {ext['extname'] for ext in extensions}
        
        for ext in extensions:
            print(f"   ✅ {ext['extname']} (v{ext['extversion']})")
        
        # Vérifier pgvector spécifiquement
        if 'vector' in found_extensions:
            print("   🎯 pgvector: Recherche vectorielle activée")
        else:
            print("   ⚠️  pgvector: Non activé (fonctionnalités de recherche limitées)")
            print("   💡 Activez-le dans Settings > Database > Extensions > pgvector")
        
        # Vérifier si toutes les extensions essentielles sont présentes
        missing = essential_extensions - found_extensions
        if missing:
            print(f"   ⚠️  Extensions manquantes: {', '.join(missing)}")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        print("\n🔧 Vérifications à faire:")
        print("   1. Projet Supabase actif sur https://supabase.com")
        print("   2. Credentials corrects dans .env")
        print("   3. Connexion internet stable")
        return False

async def main():
    """Fonction principale"""
    print("🚀 Test de Configuration Supabase")
    print("🗄️  SentinelIQ Harvester")
    print("=" * 50)
    
    success = await test_connection()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Configuration Supabase valide!")
        print("\n💡 Prochaines étapes:")
        print("   1. Lancez: python installation/setup_supabase.py")
        print("   2. Puis: python src/main.py")
    else:
        print("❌ Configuration à corriger")
        print("\n💡 Aide:")
        print("   1. Vérifiez votre fichier .env")
        print("   2. Consultez le README.md")
        print("   3. Vérifiez votre dashboard Supabase")

if __name__ == "__main__":
    asyncio.run(main())
