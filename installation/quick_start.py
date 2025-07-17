#!/usr/bin/env python3
"""
🚀 Quick Start - SentinelIQ Harvester
Script de démarrage rapide pour une installation complète
"""
import subprocess
import sys
import os
from pathlib import Path

def run_command(description, command, critical=True):
    """Exécute une commande avec gestion d'erreur"""
    print(f"\n🔄 {description}...")
    print(f"💻 Commande: {' '.join(command)}")
    
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"✅ {description} - Réussi")
        if result.stdout.strip():
            print(f"📄 Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - Échoué")
        print(f"🔥 Erreur: {e.stderr.strip() if e.stderr else str(e)}")
        if critical:
            print("🛑 Arrêt du processus d'installation")
            sys.exit(1)
        return False
    except FileNotFoundError:
        print(f"❌ {description} - Commande non trouvée")
        if critical:
            print("🛑 Arrêt du processus d'installation")
            sys.exit(1)
        return False

def check_file(filepath, description):
    """Vérifie l'existence d'un fichier"""
    if Path(filepath).exists():
        print(f"✅ {description} trouvé")
        return True
    else:
        print(f"❌ {description} manquant")
        return False

def main():
    """Installation automatique complète"""
    print("🚀 SentinelIQ Harvester - Installation Automatique")
    print("🤖 Configuration complète avec Supabase")
    print("=" * 60)
    
    # Vérifications préliminaires
    print("\n📋 ÉTAPE 1: Vérifications préliminaires")
    
    if not check_file(".env", "Fichier .env"):
        print("💡 Vous devez d'abord configurer votre fichier .env")
        print("💡 Lancez: cp .env.example .env")
        print("💡 Puis éditez .env avec vos credentials Supabase")
        sys.exit(1)
    
    if not check_file("requirements.txt", "Requirements"):
        print("❌ Fichier requirements.txt manquant")
        sys.exit(1)
    
    # Vérification environnement virtuel
    if not (hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)):
        print("⚠️  Environnement virtuel non activé")
        print("💡 Activez-le avec: source .venv/bin/activate")
        response = input("🤔 Continuer quand même ? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Installation des dépendances
    print("\n📦 ÉTAPE 2: Installation des dépendances")
    run_command(
        "Installation des packages Python",
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
    )
    
    run_command(
        "Installation des dépendances Supabase",
        [sys.executable, "-m", "pip", "install", "python-dotenv", "psycopg2-binary"]
    )
    
    # Vérification des prérequis
    print("\n🔍 ÉTAPE 3: Vérification des prérequis")
    run_command(
        "Vérification système",
        [sys.executable, "installation/check_requirements.py"],
        critical=False
    )
    
    # Test de connexion Supabase
    print("\n🗄️  ÉTAPE 4: Test de connexion Supabase")
    if run_command(
        "Test connexion base de données",
        [sys.executable, "installation/test_connection.py"],
        critical=False
    ):
        print("✅ Connexion Supabase validée")
    else:
        print("❌ Problème de connexion Supabase")
        print("💡 Vérifiez vos credentials dans .env")
        response = input("🤔 Continuer quand même ? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Configuration de la base de données
    print("\n🛠️  ÉTAPE 5: Configuration de la base de données")
    run_command(
        "Création des tables Supabase",
        [sys.executable, "installation/setup_supabase.py"]
    )
    
    # Services auxiliaires
    print("\n🐳 ÉTAPE 6: Services auxiliaires")
    
    # Vérifier Docker
    docker_available = run_command(
        "Vérification Docker",
        ["docker", "--version"],
        critical=False
    )
    
    if docker_available:
        print("🔄 Démarrage de Redis avec Docker...")
        redis_started = run_command(
            "Démarrage Redis",
            ["docker-compose", "up", "-d", "redis"],
            critical=False
        )
        
        if redis_started:
            print("✅ Redis démarré avec Docker")
        else:
            print("⚠️  Échec démarrage Redis Docker")
            print("💡 Configurez Redis manuellement ou utilisez Redis Cloud")
    else:
        print("⚠️  Docker non disponible")
        print("💡 Installez Redis manuellement ou utilisez un service cloud")
        print("💡 Exemples: Upstash, Redis Cloud, ElastiCache")
    
    # Vérifications finales
    print("\n🎯 ÉTAPE 7: Vérifications finales")
    
    # Test Redis (optionnel)
    redis_working = run_command(
        "Test Redis",
        [sys.executable, "-c", "import redis; r=redis.from_url('redis://localhost:6379'); r.ping(); print('Redis OK')"],
        critical=False
    )
    
    # Résumé final
    print("\n" + "=" * 60)
    print("🎉 INSTALLATION TERMINÉE!")
    print("=" * 60)
    
    print("\n📊 Statut des services:")
    print("   ✅ Python et dépendances")
    print("   ✅ Configuration Supabase")
    print("   ✅ Tables base de données")
    print(f"   {'✅' if redis_working else '⚠️ '} Redis")
    
    print("\n🚀 Démarrage de l'application:")
    print("   python src/main.py")
    
    print("\n🔗 URLs utiles:")
    print("   📊 API: http://localhost:8000")
    print("   📚 Docs: http://localhost:8000/docs")
    print("   🗄️  Supabase: https://supabase.com/dashboard")
    
    if not redis_working:
        print("\n⚠️  Configuration Redis requise:")
        print("   • Option 1: docker-compose up -d redis")
        print("   • Option 2: Service Redis Cloud")
        print("   • Option 3: Installation locale")
    
    print("\n🛠️  Commandes utiles:")
    print("   • Tests: pytest tests/")
    print("   • Logs: tail -f logs/app.log")
    print("   • Monitoring: http://localhost:9090")
    
    print("\n🎯 Bon développement avec SentinelIQ Harvester!")

if __name__ == "__main__":
    main()
