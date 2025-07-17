# Guide de déploiement Coolify pour SentinelIQ Harvester

## 🚀 Déploiement sur Coolify

### 1. Services requis

Dans Coolify, créez d'abord ces services :

**PostgreSQL avec pgvector :**
```
Image: pgvector/pgvector:pg15
Variables d'environnement:
- POSTGRES_DB=sentineliq
- POSTGRES_USER=sentineliq  
- POSTGRES_PASSWORD=your-secure-password
```

**Redis :**
```
Image: redis:7-alpine
Commande: redis-server --appendonly yes
```

### 2. Application principale

**Créer une nouvelle application :**
- Repository: votre-repo/SentinelIQ-Harvester
- Build Pack: Dockerfile
- Port: 8000

**Variables d'environnement requises :**
```
DATABASE_URL=postgresql://sentineliq:password@postgres:5432/sentineliq
REDIS_URL=redis://redis:6379/0
ENVIRONMENT=production
SECRET_KEY=your-super-secret-key-change-me
OPENAI_API_KEY=sk-your-openai-key (optionnel)
RUN_MIGRATIONS=true
```

### 3. Workers Celery (optionnel mais recommandé)

**Worker généraliste :**
```
Même image/repo que l'API
CMD override: ["worker"]
Variables d'environnement: mêmes que l'API
+ WORKER_QUEUES=default,crawler,indexing
```

**Worker découverte :**
```
Même image/repo que l'API  
CMD override: ["discovery"]
Variables d'environnement: mêmes que l'API
```

**Scheduler Celery Beat :**
```
Même image/repo que l'API
CMD override: ["beat"]
Variables d'environnement: mêmes que l'API
```

### 4. Monitoring (optionnel)

**Flower - Interface de monitoring :**
```
Même image/repo que l'API
CMD override: ["flower"]
Port: 5555
Variables d'environnement: mêmes que l'API
```

## 🔧 Configuration réseau

Coolify gère automatiquement le réseau entre services. Utilisez les noms de services comme hostnames :
- `postgres` pour PostgreSQL
- `redis` pour Redis
- `app` pour l'API principale

## 📊 URLs d'accès

Une fois déployé :
- **API principale :** `https://your-app.coolify.domain`
- **Documentation :** `https://your-app.coolify.domain/docs`
- **Health check :** `https://your-app.coolify.domain/health`
- **Flower (si déployé) :** `https://flower.coolify.domain`

## ⚙️ Commandes utiles

**Initialiser la base :**
```bash
# Via l'interface Coolify ou exec
docker exec -it container-name python dev.py init-db
```

**Lancer une découverte manuelle :**
```bash
docker exec -it container-name python dev.py test-discovery
```

**Vérifier le statut :**
```bash
docker exec -it container-name python dev.py status
```

## 🔍 Architecture déployée

```
┌─────────────────────────────────────────────────────┐
│                    Coolify                          │
├─────────────────────────────────────────────────────┤
│ 🌐 Load Balancer + SSL                             │
├─────────────────────────────────────────────────────┤
│ 🚀 SentinelIQ API (Port 8000)                      │
│    ├── FastAPI REST endpoints                      │
│    ├── Recherche sémantique                        │
│    └── Interface web (/docs)                       │
├─────────────────────────────────────────────────────┤
│ 👷 Workers Celery                                   │
│    ├── Discovery worker (découverte auto)          │
│    ├── Crawler worker (crawling intelligent)       │
│    ├── Indexing worker (embeddings)                │
│    └── Beat scheduler (tâches programmées)         │
├─────────────────────────────────────────────────────┤
│ 🗄️  PostgreSQL + pgvector                          │
│    ├── Articles et métadonnées                     │
│    ├── Embeddings vectoriels                       │
│    └── Métriques système                           │
├─────────────────────────────────────────────────────┤
│ 🔄 Redis                                            │
│    ├── Queue Celery                                │
│    ├── Cache sessions                              │
│    └── Rate limiting                               │
├─────────────────────────────────────────────────────┤
│ 📊 Monitoring (optionnel)                          │
│    └── Flower (monitoring Celery)                  │
└─────────────────────────────────────────────────────┘
```

## 🎯 Mode 100% autonome

Une fois déployé, le système fonctionne de manière complètement autonome :

- **Découverte :** Toutes les 6 heures, trouve de nouvelles sources
- **Crawling :** Toutes les 2 heures, crawle les sources actives  
- **Indexation :** Toutes les heures, indexe les nouveaux articles
- **Maintenance :** Nettoyage quotidien automatique
- **Métriques :** Collecte continue des performances

Le système peut tourner des mois sans intervention ! 🚀

## 📈 Scaling

Coolify permet d'ajuster facilement :
- **CPU/RAM** : Via l'interface de gestion des ressources
- **Workers** : Augmenter le nombre de replicas des workers
- **Base de données** : Upgrade PostgreSQL si nécessaire

## 🔐 Sécurité

- SSL automatique via Coolify
- Variables d'environnement sécurisées
- Container non-root
- Validation des entrées API
- Rate limiting intégré
