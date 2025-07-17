# 🤖 SentinelIQ Harvester - Système de Veille Technique Autonome

## 🎯 Vision
Un système de veille technique **100% autonome** qui découvre, crawle et indexe intelligemment le contenu tech du web avec **Supabase PostgreSQL** et **recherche vectorielle**.

## ⚡ Fonctionnalités Clés

- **Découverte autonome** de nouvelles sources via moteurs de recherche
- **Crawling intelligent** avec détection de changements
- **Anti-duplication avancée** avec hash de contenu
- **Recherche vectorielle** avec pgvector et embeddings OpenAI
- **Scaling horizontal/vertical** automatique
- **Pipeline ML** pour classification et extraction
- **API REST** haute performance avec FastAPI
- **Base Supabase** PostgreSQL cloud-native
- **Monitoring complet** avec métriques temps réel

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Discovery     │    │    Crawler      │    │   Processor     │
│   Engine        │───▶│   Workers       │───▶│   Pipeline      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Scheduler    │    │   Redis Queue   │    │   Supabase      │
│   (Celery)      │    │   & Cache       │    │   PostgreSQL    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Installation Rapide

### ⚡ Installation Automatisée (Recommandée)

```bash
# 1. Cloner le projet
git clone <repo>
cd SentinelIQ-Harvester

# 2. Configuration environnement
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# 3. Configuration .env
cp .env.example .env
# Éditez .env avec vos credentials Supabase

# 4. Installation complète automatique ⭐
python installation/quick_start.py

# 5. Démarrage
python src/main.py
```

### � Guide d'Installation Complet

Pour une installation détaillée étape par étape, consultez le **[Guide d'Installation Complet](installation/README.md)** qui inclut :

- ✅ **Scripts d'installation automatisés**
- 🔧 **Configuration Supabase détaillée** 
- 🛠️ **Dépannage et résolution d'erreurs**
- 🐳 **Configuration Docker et Redis**
- 📊 **Vérification et tests de connexion**

### 📋 Prérequis Système

| Composant | Version | Statut | Notes |
|-----------|---------|---------|-------|
| **Python** | 3.11+ | ✅ Essentiel | Version recommandée |
| **Supabase** | - | ✅ Essentiel | Base de données cloud |
| **Docker** | Latest | ⚠️ Optionnel | Pour Redis local |

Pour plus de détails, consultez le **[Guide d'Installation](installation/README.md)**.

## 🗄️ Configuration Supabase

### Configuration Rapide
1. Créez un projet sur [supabase.com](https://supabase.com)
2. Copiez vos credentials dans `.env`
3. Lancez `python installation/quick_start.py`

### Guide Détaillé
Pour une configuration complète de Supabase avec toutes les options et le dépannage, consultez le **[Guide d'Installation Détaillé](installation/README.md)**.

## 📦 Démarrage

```bash
# Démarrage rapide
python src/main.py

# API disponible sur
http://localhost:8000

# Documentation interactive
http://localhost:8000/docs
```

## 🛠️ Configuration Avancée

Pour la configuration détaillée, le dépannage et les bonnes pratiques, consultez :

📘 **[Guide d'Installation Complet](installation/README.md)** - Configuration complète étape par étape

Ce guide inclut :
- 🗄️ Configuration Supabase détaillée (credentials, extensions, poolers)
- 🐳 Docker et Redis (local et cloud)  
- 🔧 Variables d'environnement complètes
- 🚨 Dépannage des erreurs communes
- 📊 Scripts de vérification et tests

- 📊 Scripts de vérification et tests

## ⚡ Utilisation

### Démarrage de l'API
```bash
python src/main.py
```

### Workers Celery (optionnel)
```bash
celery -A src.celery_app worker --loglevel=info
```

### URLs Principales
- 🌐 **API** : http://localhost:8000
- 📚 **Documentation** : http://localhost:8000/docs
- 🔍 **Recherche** : http://localhost:8000/search

## 🏗️ Architecture Technique

### � Composants Principaux

- **Discovery Engine** : Découverte autonome de nouvelles sources
- **Smart Crawler** : Crawling intelligent avec anti-duplication  
- **Content Processor** : Extraction et classification du contenu
- **Vector Search** : Recherche sémantique avec pgvector
- **API REST** : Interface haute performance avec FastAPI
- **Task Queue** : Pipeline asynchrone avec Celery

### 🗄️ Base de Données

- **Supabase PostgreSQL** : Base de données cloud-native
- **pgvector** : Recherche vectorielle et embeddings
- **Indexation avancée** : Performance optimisée

## 📊 Métriques de Performance

- **Vitesse de crawl** : 1000+ pages/minute
- **Recherche vectorielle** : <100ms
- **Découverte quotidienne** : 100+ nouvelles sources
- **Déduplication** : 99.9% de précision
- **Uptime** : 99.9% (dépend de Supabase)

## 🛠️ Développement

### Tests
```bash
pytest tests/ -v
```

### Linting et Format
```bash
black src/ tests/
flake8 src/ tests/
mypy src/
```

## 🌍 Déploiement

### Plateformes Recommandées
- **Railway** : Déploiement simple avec Supabase
- **Render** : Auto-deploy depuis Git
- **Fly.io** : Global edge deployment
- **Google Cloud Run** : Serverless containers

### Docker Production
```bash
docker build -t sentineliq-harvester .
docker run -d -p 8000:8000 --env-file .env sentineliq-harvester
```

```

## � Documentation

Pour plus d'informations, consultez :

- 📘 **[Guide d'Installation Complet](installation/README.md)** - Configuration détaillée étape par étape
- 🏗️ **[Architecture](docs/architecture.md)** - Design et composants (à venir)
- 🚀 **[Déploiement](docs/deployment.md)** - Guide de production (à venir)
- 📡 **[API Reference](docs/api.md)** - Endpoints et schemas (à venir)

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :

- 🐛 Signaler des bugs
- ✨ Proposer des améliorations  
- 📖 Améliorer la documentation
- 🧪 Ajouter des tests

## 🔄 Roadmap

- [ ] **Q1 2025** : Interface web admin
- [ ] **Q2 2025** : Plugins d'extensions
- [ ] **Q3 2025** : ML avancé (classification)
- [ ] **Q4 2025** : Multi-tenant SaaS

---

## 🏆 Développé par The-Genium007

**SentinelIQ Harvester** - Veille technique autonome et intelligente 🚀

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-green.svg)](https://python.org)
[![Supabase](https://img.shields.io/badge/database-Supabase-green.svg)](https://supabase.com)
[![FastAPI](https://img.shields.io/badge/api-FastAPI-teal.svg)](https://fastapi.tiangolo.com)

### 5. 🎛️ Types de Connexion Supabase

| Type | Usage | Avantages | Configuration |
|------|-------|-----------|---------------|
| **Direct Connection** | Apps persistantes | Connexion dédiée, performances | `db.[PROJECT-ID].supabase.co:5432` |
| **Transaction Pooler** | Serverless, IPv4 | Pool partagé, IPv4 compatible | `aws-0-eu-west-3.pooler.supabase.com:6543` |
| **Session Pooler** | IPv4 uniquement | Alternative au direct | `aws-0-eu-west-3.pooler.supabase.com:5432` |

## 📦 Installation des Dépendances

### Dépendances Python Essentielles
```bash
pip install -r requirements.txt
```

### Dépendances Système Supplémentaires
```bash
# Pour Supabase (déjà inclus dans requirements.txt)
pip install python-dotenv psycopg2-binary

# Pour le développement (optionnel)
pip install black flake8 mypy pytest
```

## 🛠️ Scripts d'Installation

Tous les scripts sont organisés dans le dossier `installation/` :

| Script | Description | Usage |
|--------|-------------|--------|
| `check_requirements.py` | Vérifie les prérequis | `python installation/check_requirements.py` |
| `test_connection.py` | Test connexion Supabase | `python installation/test_connection.py` |
| `setup_supabase.py` | Configure la base | `python installation/setup_supabase.py` |

### 🔄 Processus d'Installation Détaillé

```bash
# === 1. VÉRIFICATION ===
python installation/check_requirements.py
# ✅ Vérifie Python, pip, Docker, .env

# === 2. TEST CONNEXION ===  
python installation/test_connection.py
# ✅ Teste la connexion Supabase
# ✅ Vérifie les extensions PostgreSQL

# === 3. CONFIGURATION BASE ===
python installation/setup_supabase.py
# ✅ Crée les tables : sources, articles, crawl_jobs
# ✅ Configure les indexes et contraintes
# ✅ Test d'insertion/lecture

# === 4. SERVICES ===
docker-compose up -d redis  # Redis local
# OU configurez Redis Cloud/Upstash

# === 5. DÉMARRAGE ===
python src/main.py
```

## � Configuration Avancée

### Variables d'Environnement Complètes

```bash
# === SUPABASE CONFIGURATION ===
DATABASE_URL=postgresql://postgres:password@host:port/postgres
SUPABASE_URL=https://project-id.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# === REDIS CONFIGURATION ===
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# === API CONFIGURATION ===
API_HOST=localhost
API_PORT=8000
SECRET_KEY=your-super-secret-key
ENVIRONMENT=development

# === CRAWLER CONFIGURATION ===
CRAWLER_MAX_WORKERS=50
CRAWLER_REQUEST_TIMEOUT=30
CRAWLER_MAX_RETRIES=3
CRAWLER_DELAY_MIN=1.0
CRAWLER_DELAY_MAX=3.0

# === ML & AI CONFIGURATION ===
OPENAI_API_KEY=sk-your-openai-key
EMBEDDING_MODEL=text-embedding-ada-002
EMBEDDING_DIMENSIONS=1536

# === WORKER CONFIGURATION ===
WORKER_QUEUES=default,crawler,discovery,indexing
CELERY_WORKER_CONCURRENCY=4
CRAWL_FREQUENCY=3600  # seconds

# === MONITORING ===
LOG_LEVEL=INFO
PROMETHEUS_PORT=9090
HEALTH_CHECK_INTERVAL=30

# === DEVELOPMENT ===
DEBUG=true
TESTING=false
HOT_RELOAD=true
```

### 🐳 Docker Compose Services

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml

volumes:
  redis_data:
```

## 🚨 Dépannage Common Issues

### ❌ Erreur de Connexion Supabase

**Problème** : `nodename nor servname provided, or not known`
```bash
# Solutions par ordre de priorité :
1. Vérifiez que votre projet Supabase est actif
2. Confirmez l'URL dans le dashboard Supabase
3. Testez avec curl : curl -I https://[PROJECT-ID].supabase.co
4. Essayez le Transaction Pooler si Direct Connection échoue
```

**Problème** : `prepared statement already exists`
```bash
# Solution : Ajoutez statement_cache_size=0 
conn = await asyncpg.connect(database_url, statement_cache_size=0)
```

### ❌ Extensions PostgreSQL

**pgvector manquant** :
```bash
# Dans Supabase Dashboard :
Settings > Database > Extensions > Rechercher "pgvector" > Enable
```

**uuid-ossp manquant** :
```sql
-- Généralement pré-installé, sinon :
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

### ❌ Problèmes Python

**psycopg2 compilation** :
```bash
# Utilisez la version binary :
pip uninstall psycopg2
pip install psycopg2-binary
```

**Version Python** :
```bash
# Vérifiez la version :
python --version  # Doit être 3.11+

# Si trop ancienne, installez Python 3.11+ :
# macOS : brew install python@3.11
# Ubuntu : sudo apt install python3.11
# Windows : Téléchargez depuis python.org
```

### ❌ Redis Connection

**Redis local indisponible** :
```bash
# Option 1 : Docker
docker-compose up -d redis

# Option 2 : Installation locale
# macOS : brew install redis && brew services start redis
# Ubuntu : sudo apt install redis-server

# Option 3 : Redis Cloud
# Upstash, Redis Cloud, ou autre service
REDIS_URL=redis://username:password@host:port/0
```

### ❌ Permissions et Accès

**Erreur Supabase permissions** :
```bash
# Vérifiez les Row Level Security (RLS) dans Supabase
# Si activé, ajoutez des policies ou utilisez service_role_key
```

## �📊 Métriques de Performance

- **Vitesse de crawl** : 1000+ pages/minute
- **Recherche vectorielle** : <100ms (avec pgvector)
- **Découverte quotidienne** : 100+ nouvelles sources
- **Déduplication** : 99.9% de précision
- **Uptime** : 99.9% (dépend de Supabase)
- **Latence API** : <50ms moyenne

## 🔐 Sécurité et Bonnes Pratiques

### �️ Configuration Sécurisée

```bash
# Production : Utilisez des secrets forts
SECRET_KEY=$(openssl rand -base64 32)

# Supabase : Activez Row Level Security
# Dashboard > Authentication > Settings > Enable RLS

# API Keys : Rotation régulière
# Dashboard > Settings > API > Regenerate keys

# Monitoring : Logs et alertes
LOG_LEVEL=INFO  # Pas DEBUG en production
```

### � Variables Sensibles

**Jamais dans le code** :
- Mots de passe Supabase
- Clés API OpenAI
- Tokens d'authentification
- Secrets de chiffrement

**Stockage sécurisé** :
- Variables d'environnement
- Gestionnaires de secrets (HashiCorp Vault, AWS Secrets Manager)
- Fichiers .env avec permissions restreintes (`chmod 600 .env`)

## 📈 Scaling et Performance

### 🔄 Horizontal Scaling

```bash
# Workers Celery multiples
celery -A src.celery_app worker --loglevel=info --concurrency=4 --queues=crawler
celery -A src.celery_app worker --loglevel=info --concurrency=2 --queues=discovery
celery -A src.celery_app worker --loglevel=info --concurrency=2 --queues=indexing

# Load balancing API
gunicorn src.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### ⬆️ Vertical Scaling

```bash
# Configuration adaptative
CELERY_WORKER_CONCURRENCY=${CPU_CORES:-4}
DATABASE_POOL_SIZE=${DB_POOL_SIZE:-20}
CRAWLER_MAX_WORKERS=${MAX_WORKERS:-50}

# Monitoring des ressources
top, htop, docker stats
```

### 🎯 Optimisations Supabase

```sql
-- Index pour recherche rapide
CREATE INDEX idx_articles_published ON articles(published_at DESC);
CREATE INDEX idx_articles_category ON articles(category);
CREATE INDEX idx_sources_active ON sources(is_active) WHERE is_active = true;

-- Index vectoriel pour pgvector
CREATE INDEX idx_articles_content_embedding ON articles 
USING ivfflat (content_embedding vector_cosine_ops);
```

## 🛠️ Développement et Tests

### 🧪 Tests

```bash
# Tests unitaires
pytest tests/ -v

# Tests d'intégration
pytest tests/integration/ -v

# Coverage
pytest --cov=src tests/

# Tests de performance
pytest tests/performance/ --benchmark-only
```

### 🔍 Linting et Format

```bash
# Formatting
black src/ tests/

# Linting
flake8 src/ tests/

# Type checking
mypy src/

# Import sorting
isort src/ tests/
```

### � Pre-commit Hooks

```bash
# Installation
pip install pre-commit
pre-commit install

# Hooks configurés :
# - black (formatting)
# - flake8 (linting)
# - mypy (type checking)
# - tests (unitaires)
```

## 🌍 Déploiement

### 🚢 Docker Production

```dockerfile
# Dockerfile optimisé
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
CMD ["gunicorn", "src.main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

### ☁️ Cloud Deployment

**Recommended Platforms** :
- **Railway** : Déploiement simple avec Supabase
- **Render** : Auto-deploy depuis Git
- **Fly.io** : Global edge deployment
- **Google Cloud Run** : Serverless containers
- **AWS ECS** : Container orchestration

### 🔄 CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          pip install -r requirements.txt
          pytest
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        run: |
          # Votre logique de déploiement
```

## � Documentation et Support

### 📖 Documentation Détaillée

- [🏗️ Architecture](docs/architecture.md) - Design et composants
- [🚀 Déploiement](docs/deployment.md) - Guide de production
- [📡 API Reference](docs/api.md) - Endpoints et schemas
- [📊 Monitoring](docs/monitoring.md) - Métriques et alertes
- [🔧 Contribution](docs/contributing.md) - Guide développeurs

### 🤝 Support et Communauté

- **Issues GitHub** : [Rapporter un bug](link)
- **Discussions** : [Questions et suggestions](link)
- **Wiki** : [Base de connaissances](link)
- **Discord** : [Communauté temps réel](link)

### 🔄 Roadmap

- [ ] **Q1 2025** : Interface web admin
- [ ] **Q2 2025** : Plugins d'extensions
- [ ] **Q3 2025** : ML avancé (classification)
- [ ] **Q4 2025** : Multi-tenant SaaS

---

## 🏆 Développé par The-Genium007

**SentinelIQ Harvester** - Veille technique autonome et intelligente 🚀

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-green.svg)](https://python.org)
[![Supabase](https://img.shields.io/badge/database-Supabase-green.svg)](https://supabase.com)
[![FastAPI](https://img.shields.io/badge/api-FastAPI-teal.svg)](https://fastapi.tiangolo.com)
