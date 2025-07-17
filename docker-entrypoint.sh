#!/bin/bash
set -e

# Fonction d'attente pour les services
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    
    echo "⏳ Attente de $service_name ($host:$port)..."
    while ! nc -z $host $port; do
        sleep 1
    done
    echo "✅ $service_name est prêt !"
}

# Attendre les services requis
if [ -n "$DATABASE_HOST" ]; then
    wait_for_service $DATABASE_HOST ${DATABASE_PORT:-5432} "PostgreSQL"
fi

if [ -n "$REDIS_HOST" ]; then
    wait_for_service $REDIS_HOST ${REDIS_PORT:-6379} "Redis"
fi

# Migrations de base de données si nécessaire
if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "🔄 Exécution des migrations..."
    python -m alembic upgrade head
fi

# Commandes disponibles
case "$1" in
    "api")
        echo "🚀 Démarrage de l'API SentinelIQ..."
        exec python main.py
        ;;
    "worker")
        echo "👷 Démarrage du worker Celery..."
        exec celery -A src.celery_app worker --loglevel=info --queues=${WORKER_QUEUES:-default,crawler,discovery,indexing}
        ;;
    "beat")
        echo "⏰ Démarrage du scheduler Celery Beat..."
        exec celery -A src.celery_app beat --loglevel=info
        ;;
    "flower")
        echo "🌸 Démarrage de Flower (monitoring)..."
        exec celery -A src.celery_app flower --port=5555
        ;;
    "init-db")
        echo "🗄️ Initialisation de la base de données..."
        python dev.py init-db
        ;;
    "crawl")
        echo "🕷️ Mode crawler autonome..."
        exec python workers.py crawler
        ;;
    "discovery")
        echo "🔍 Mode découverte autonome..."
        exec python workers.py discovery
        ;;
    *)
        echo "Commandes disponibles:"
        echo "  api      - Démarre l'API REST (défaut)"
        echo "  worker   - Démarre un worker Celery"
        echo "  beat     - Démarre le scheduler"
        echo "  flower   - Démarre le monitoring"
        echo "  crawl    - Mode crawler autonome"
        echo "  discovery- Mode découverte autonome"
        echo "  init-db  - Initialise la base de données"
        exec "$@"
        ;;
esac
