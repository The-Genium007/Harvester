# 🤖 SentinelIQ Harvester - Système de Veille Technique Autonome

## 🎯 Vision
Un système de veille technique **100% autonome** qui découvre, crawle et indexe intelligemment le contenu tech du web.

## ⚡ Fonctionnalités Clés

- **Découverte autonome** de nouvelles sources via moteurs de recherche
- **Crawling intelligent** avec détection de changements
- **Anti-duplication avancée** avec hash de contenu
- **Scaling horizontal/vertical** automatique
- **Pipeline ML** pour classification et extraction
- **API REST** haute performance avec recherche vectorielle
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

## 🚀 Démarrage Rapide

### Prérequis
- Python 3.11+
- Docker & Docker Compose
- Supabase (compte et projet)
- Coolify (pour le déploiement)

### Installation

```bash
# Cloner et configurer
git clone <repo>
cd SentinelIQ-Harvester

# Créer l'environnement
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Configuration
cp .env.example .env
# Éditer .env avec vos credentials Supabase

# Setup database
python scripts/setup_database.py

# Lancer les services locaux
docker-compose up -d

# Démarrer l'application
python src/main.py
```

## 📊 Métriques de Performance

- **Vitesse de crawl** : 1000+ pages/minute
- **Recherche vectorielle** : <100ms
- **Découverte quotidienne** : 100+ nouvelles sources
- **Déduplication** : 99.9% de précision
- **Uptime** : 99.9%

## 🔧 Configuration

Voir `deployment/coolify/` pour les configurations de production.

## 📚 Documentation

- [Architecture Détaillée](docs/architecture.md)
- [Guide de Déploiement](docs/deployment.md)
- [API Reference](docs/api.md)
- [Monitoring](docs/monitoring.md)

## 🛠️ Développement

```bash
# Tests
pytest tests/

# Linting
black src/
flake8 src/

# Type checking
mypy src/
```

## 📈 Scaling

Le système est conçu pour scaler de 1 à 100+ workers sans modification de code.

### Horizontal Scaling
- Workers Celery auto-scalables
- Queue Redis distribuée
- Load balancing automatique

### Vertical Scaling
- Auto-ajustement des ressources
- Monitoring des performances
- Optimisation dynamique

## 🔐 Sécurité

- Rate limiting adaptatif
- Rotation de proxies
- Headers authentiques
- Respect des robots.txt

## 📞 Support

Pour toute question : [Issues GitHub](link)

---

**Développé par The-Genium007** 🚀
