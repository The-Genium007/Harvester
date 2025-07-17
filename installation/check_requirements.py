#!/usr/bin/env python3
"""
Vérification des prérequis pour SentinelIQ Harvester
"""
import sys
import subprocess
import os
from pathlib import Path

def check_python_version():
    """Vérifie la version Python"""
    version = sys.version_info
    required = (3, 11)
    
    print(f"🐍 Python: {version.major}.{version.minor}.{version.micro}")
    
    if version >= required:
        print("   ✅ Version compatible")
        return True
    else:
        print(f"   ❌ Version trop ancienne (requis: {required[0]}.{required[1]}+)")
        return False

def check_pip():
    """Vérifie pip"""
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "--version"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"📦 pip: {result.stdout.strip().split()[1]}")
            print("   ✅ pip disponible")
            return True
    except:
        pass
    
    print("❌ pip non disponible")
    return False

def check_git():
    """Vérifie git"""
    try:
        result = subprocess.run(["git", "--version"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip().split()[2]
            print(f"🌿 Git: {version}")
            print("   ✅ Git disponible")
            return True
    except:
        pass
    
    print("⚠️  Git non trouvé (optionnel pour le déploiement)")
    return False

def check_docker():
    """Vérifie Docker"""
    try:
        result = subprocess.run(["docker", "--version"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip().split()[2].rstrip(',')
            print(f"🐳 Docker: {version}")
            print("   ✅ Docker disponible")
            return True
    except:
        pass
    
    print("⚠️  Docker non trouvé (requis pour Redis local)")
    return False

def check_env_file():
    """Vérifie le fichier .env"""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if env_file.exists():
        print("📁 .env: Présent")
        print("   ✅ Fichier de configuration trouvé")
        
        # Vérifier les variables essentielles
        with open(env_file, 'r') as f:
            content = f.read()
            
        required_vars = [
            'DATABASE_URL',
            'SUPABASE_URL', 
            'SUPABASE_KEY',
            'REDIS_URL'
        ]
        
        missing_vars = []
        for var in required_vars:
            if var not in content or f"{var}=" not in content:
                missing_vars.append(var)
        
        if missing_vars:
            print(f"   ⚠️  Variables manquantes: {', '.join(missing_vars)}")
            return False
        else:
            print("   ✅ Variables essentielles présentes")
            return True
    else:
        print("📁 .env: Absent")
        if env_example.exists():
            print("   💡 Lancez: cp .env.example .env")
            print("   💡 Puis éditez .env avec vos credentials Supabase")
        else:
            print("   ❌ .env.example aussi absent")
        return False

def check_virtual_env():
    """Vérifie l'environnement virtuel"""
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        venv_path = sys.prefix
        print(f"🔒 Environnement virtuel: Actif")
        print(f"   📍 Path: {venv_path}")
        print("   ✅ Isolation Python active")
        return True
    else:
        print("🔒 Environnement virtuel: Inactif")
        print("   💡 Recommandé: python -m venv .venv && source .venv/bin/activate")
        return False

def main():
    """Fonction principale"""
    print("🚀 Vérification des Prérequis")
    print("🤖 SentinelIQ Harvester")
    print("=" * 50)
    
    checks = [
        ("Python 3.11+", check_python_version),
        ("pip", check_pip),
        ("Git", check_git),
        ("Docker", check_docker),
        ("Environnement virtuel", check_virtual_env),
        ("Fichier .env", check_env_file),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n🔍 {name}:")
        results.append(check_func())
    
    print("\n" + "=" * 50)
    print("📊 Résumé:")
    
    essential_passed = results[0] and results[1] and results[5]  # Python, pip, .env
    optional_passed = sum(results[2:5])  # Git, Docker, venv
    
    if essential_passed:
        print("✅ Prérequis essentiels: OK")
        print(f"📈 Prérequis optionnels: {optional_passed}/3")
        
        if results[3]:  # Docker
            print("\n💡 Prochaines étapes:")
            print("   1. python installation/test_connection.py")
            print("   2. python installation/setup_supabase.py") 
            print("   3. docker-compose up -d redis")
            print("   4. python src/main.py")
        else:
            print("\n💡 Prochaines étapes (sans Docker):")
            print("   1. Installez Redis manuellement ou utilisez Redis Cloud")
            print("   2. python installation/test_connection.py")
            print("   3. python installation/setup_supabase.py")
            print("   4. python src/main.py")
    else:
        print("❌ Prérequis essentiels manquants")
        print("\n🔧 À corriger:")
        if not results[0]:
            print("   - Installer Python 3.11+")
        if not results[1]:
            print("   - Installer pip")
        if not results[5]:
            print("   - Configurer le fichier .env")

if __name__ == "__main__":
    main()
