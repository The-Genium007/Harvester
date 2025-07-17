# 📁 Scripts d'Installation - SentinelIQ Harvester

Ce dossier contient tous les scripts nécessaires pour installer et configurer SentinelIQ Harvester.

## 🗂️ Fichiers d'Installation

### 1. **quick_start.py** ⭐
Script d'installation automatique complète (recommandé)
```bash
python installation/quick_start.py
```

### 2. **check_requirements.py**
Vérifie tous les prérequis système
```bash
python installation/check_requirements.py
```

### 3. **test_connection.py** 
Teste votre connexion Supabase
```bash
python installation/test_connection.py
```

### 4. **setup_supabase.py**
Configure la base de données Supabase
```bash
python installation/setup_supabase.py
```

## 🚀 Ordre d'Exécution Recommandé

### Option 1 : Installation Automatique (Recommandée) ⭐
```bash
# Installation complète en une commande
python installation/quick_start.py
```

### Option 2 : Installation Manuelle
```bash
# 1. Vérifier les prérequis
python installation/check_requirements.py

# 2. Tester la connexion Supabase
python installation/test_connection.py

# 3. Configurer la base de données
python installation/setup_supabase.py

# 4. Démarrer Redis (si Docker disponible)
docker-compose up -d redis

# 5. Lancer l'application
python src/main.py
```

## ⚙️ Configuration Requise

Avant d'exécuter ces scripts, assurez-vous d'avoir :

1. **Copié .env.example vers .env**
   ```bash
   cp .env.example .env
   ```

2. **Configuré vos credentials Supabase dans .env**
   - DATABASE_URL
   - SUPABASE_URL  
   - SUPABASE_KEY
   - SUPABASE_SERVICE_ROLE_KEY

3. **Activé votre environnement virtuel**
   ```bash
   source .venv/bin/activate  # Linux/Mac
   # ou
   .venv\Scripts\activate     # Windows
   ```

## 🔧 Dépannage

### Problème de connexion Supabase
- Vérifiez que votre projet Supabase est actif
- Confirmez vos credentials dans le dashboard Supabase
- Essayez le Transaction Pooler si la connexion directe échoue

### Extensions PostgreSQL manquantes
- Activez pgvector dans Settings > Database > Extensions
- Les autres extensions (uuid-ossp, pg_trgm) sont généralement pré-installées

### Erreur de Transaction Pooler
- C'est normal avec Supabase, les scripts gèrent automatiquement cette limitation
- Utilisez `statement_cache_size=0` dans vos connexions asyncpg

## 📚 Documentation

Consultez le README.md principal pour plus d'informations sur :
- Configuration détaillée de Supabase
- Architecture du système
- Guide de déploiement
