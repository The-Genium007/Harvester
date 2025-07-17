# Utilise une image Python officielle avec sécurité renforcée
FROM python:3.11-slim-bookworm

# Définit le répertoire de travail
WORKDIR /app

# Installe les dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copie les fichiers de requirements
COPY requirements.txt .

# Installe les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copie le code source
COPY . .

# Crée un utilisateur non-root
RUN useradd --create-home --shell /bin/bash sentineliq
RUN chown -R sentineliq:sentineliq /app
USER sentineliq

# Expose le port de l'API
EXPOSE 8000

# Variables d'environnement par défaut
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Script de démarrage
COPY --chown=sentineliq:sentineliq docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Point d'entrée
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Commande par défaut (API)
CMD ["api"]
