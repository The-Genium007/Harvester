"""
Script de démarrage des workers Celery pour SentinelIQ
"""
import sys
import subprocess
from pathlib import Path

def start_redis():
    """Démarre Redis si pas déjà en cours"""
    try:
        subprocess.run(["redis-cli", "ping"], check=True, capture_output=True)
        print("✅ Redis déjà en cours d'exécution")
    except subprocess.CalledProcessError:
        print("🔄 Démarrage de Redis...")
        subprocess.Popen(["redis-server"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def start_celery_worker(queue="default"):
    """Démarre un worker Celery pour une queue spécifique"""
    cmd = [
        "celery", "-A", "src.celery_app", "worker",
        f"--queues={queue}",
        "--loglevel=info",
        "--concurrency=2"
    ]
    
    print(f"🔧 Démarrage worker Celery pour queue: {queue}")
    return subprocess.Popen(cmd)

def start_celery_beat():
    """Démarre le scheduler Celery Beat"""
    cmd = [
        "celery", "-A", "src.celery_app", "beat",
        "--loglevel=info"
    ]
    
    print("⏰ Démarrage Celery Beat (scheduler)")
    return subprocess.Popen(cmd)

def start_flower():
    """Démarre Flower pour le monitoring"""
    cmd = [
        "celery", "-A", "src.celery_app", "flower",
        "--port=5555"
    ]
    
    print("🌸 Démarrage Flower (monitoring) sur http://localhost:5555")
    return subprocess.Popen(cmd)

def main():
    """Point d'entrée principal"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python workers.py redis        # Démarre Redis")
        print("  python workers.py worker       # Démarre un worker par défaut")
        print("  python workers.py discovery    # Démarre worker découverte")
        print("  python workers.py crawler      # Démarre worker crawling")
        print("  python workers.py indexing     # Démarre worker indexation")
        print("  python workers.py beat         # Démarre scheduler")
        print("  python workers.py flower       # Démarre monitoring")
        print("  python workers.py all          # Démarre tout")
        return
    
    command = sys.argv[1]
    
    if command == "redis":
        start_redis()
        
    elif command == "worker":
        start_redis()
        worker = start_celery_worker("default,crawler,indexing")
        worker.wait()
        
    elif command == "discovery":
        start_redis()
        worker = start_celery_worker("discovery")
        worker.wait()
        
    elif command == "crawler":
        start_redis()
        worker = start_celery_worker("crawler")
        worker.wait()
        
    elif command == "indexing":
        start_redis()
        worker = start_celery_worker("indexing")
        worker.wait()
        
    elif command == "beat":
        start_redis()
        beat = start_celery_beat()
        beat.wait()
        
    elif command == "flower":
        start_redis()
        flower = start_flower()
        flower.wait()
        
    elif command == "all":
        print("🚀 Démarrage de tous les services...")
        start_redis()
        
        processes = []
        
        # Workers
        processes.append(start_celery_worker("discovery"))
        processes.append(start_celery_worker("crawler"))
        processes.append(start_celery_worker("indexing"))
        processes.append(start_celery_worker("maintenance"))
        
        # Scheduler
        processes.append(start_celery_beat())
        
        # Monitoring
        processes.append(start_flower())
        
        print("✅ Tous les services démarrés")
        print("📊 Monitoring: http://localhost:5555")
        print("🛑 Ctrl+C pour arrêter tous les services")
        
        try:
            # Attend que tous les processus se terminent
            for process in processes:
                process.wait()
        except KeyboardInterrupt:
            print("\n🛑 Arrêt des services...")
            for process in processes:
                process.terminate()
                
    else:
        print(f"❌ Commande inconnue: {command}")

if __name__ == "__main__":
    main()
