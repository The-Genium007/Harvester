# Script d'initialisation PostgreSQL pour SentinelIQ
# Ce script sera exécuté lors du premier démarrage du container PostgreSQL

-- Active l'extension pgvector pour les embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Active d'autres extensions utiles
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Configuration pour améliorer les performances vectorielles
SET shared_preload_libraries = 'pg_stat_statements';
SET max_connections = 100;
SET shared_buffers = '256MB';
SET effective_cache_size = '1GB';
SET work_mem = '16MB';
SET maintenance_work_mem = '128MB';

-- Optimisations pour pgvector
SET ivfflat.probes = 10;

-- Création d'utilisateurs si nécessaire
-- (déjà géré par les variables d'environnement POSTGRES_USER/POSTGRES_PASSWORD)

-- Log de confirmation
DO $$
BEGIN
    RAISE NOTICE 'SentinelIQ database initialized successfully with pgvector support';
END $$;
