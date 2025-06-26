"""
Script de déploiement automatique sur Render
"""

import requests
import json
import time
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration Render
RENDER_API_KEY = "rnd_0zxWHHYUEaSp7TsCz3QQJBVlGsQR"
RENDER_BASE_URL = "https://api.render.com/v1"

# Headers pour API Render
headers = {
    "Authorization": f"Bearer {RENDER_API_KEY}",
    "Content-Type": "application/json"
}

def create_github_repo():
    """Créer le repository GitHub (simulé pour le moment)"""
    print("📁 Repository GitHub créé localement")
    # Le repo sera créé manuellement ou via GitHub CLI
    return "https://github.com/USER/samantha-telegram-agent"

def create_render_service():
    """Créer le service Render via API"""
    
    service_data = {
        "type": "web_service",
        "name": "samantha-telegram-agent",
        "repo": "https://github.com/USER/samantha-telegram-agent",
        "branch": "main",
        "env": "python",
        "plan": "free",
        "buildCommand": "pip install -r requirements.txt",
        "startCommand": "python telegram_bot.py",
        "envVars": [
            {"key": "TELEGRAM_BOT_TOKEN", "value": os.getenv('TELEGRAM_BOT_TOKEN')},
            {"key": "OPENAI_API_KEY", "value": os.getenv('OPENAI_API_KEY')},
            {"key": "SUPABASE_URL", "value": os.getenv('SUPABASE_URL')},
            {"key": "SUPABASE_ANON_KEY", "value": os.getenv('SUPABASE_ANON_KEY')},
            {"key": "SUPABASE_SERVICE_KEY", "value": os.getenv('SUPABASE_SERVICE_KEY')},
            {"key": "DAILY_BUDGET_USD", "value": "1.50"},
            {"key": "MONTHLY_BUDGET_USD", "value": "40.00"},
            {"key": "WARNING_THRESHOLD", "value": "0.75"},
            {"key": "AGENT_NAME", "value": "Samantha"},
            {"key": "DEFAULT_MODEL", "value": "gpt-4o-mini"},
            {"key": "MAX_MEMORY_MESSAGES", "value": "50"},
            {"key": "PRIMARY_LANGUAGE", "value": "français"},
            {"key": "DEFAULT_TONE", "value": "startup style no bullshit full efficiency"}
        ]
    }
    
    print("🚀 Création du service Render...")
    response = requests.post(
        f"{RENDER_BASE_URL}/services",
        headers=headers,
        json=service_data
    )
    
    if response.status_code == 201:
        service = response.json()
        print(f"✅ Service créé: {service['name']}")
        print(f"🔗 URL: {service['serviceDetails']['url']}")
        return service
    else:
        print(f"❌ Erreur création service: {response.status_code}")
        print(response.text)
        return None

def deploy_service(service_id):
    """Déclencher le déploiement"""
    print("📦 Déploiement en cours...")
    
    response = requests.post(
        f"{RENDER_BASE_URL}/services/{service_id}/deploys",
        headers=headers
    )
    
    if response.status_code == 201:
        deploy = response.json()
        print(f"✅ Déploiement lancé: {deploy['id']}")
        return deploy
    else:
        print(f"❌ Erreur déploiement: {response.status_code}")
        return None

def check_deployment_status(service_id, deploy_id):
    """Vérifier le statut du déploiement"""
    print("⏳ Vérification du déploiement...")
    
    for i in range(20):  # Check pendant 10 minutes max
        response = requests.get(
            f"{RENDER_BASE_URL}/services/{service_id}/deploys/{deploy_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            deploy = response.json()
            status = deploy['status']
            
            print(f"Status: {status}")
            
            if status == "live":
                print("🎉 Déploiement réussi ! Samantha est live !")
                return True
            elif status in ["build_failed", "update_failed"]:
                print("❌ Déploiement échoué")
                return False
            
            time.sleep(30)  # Attendre 30 secondes
        else:
            print(f"Erreur check status: {response.status_code}")
            
    print("⏰ Timeout - Vérifiez manuellement sur Render dashboard")
    return False

def main():
    print("🚀 DÉPLOIEMENT AUTOMATIQUE SAMANTHA")
    print("="*50)
    
    # 1. Vérifier les variables d'environnement
    required_vars = ['TELEGRAM_BOT_TOKEN', 'OPENAI_API_KEY', 'SUPABASE_URL', 'SUPABASE_ANON_KEY', 'SUPABASE_SERVICE_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Variables manquantes: {missing_vars}")
        return
    
    print("✅ Variables d'environnement OK")
    
    # 2. Créer le service Render
    service = create_render_service()
    if not service:
        print("❌ Échec création service")
        return
    
    service_id = service['id']
    
    # 3. Déclencher le déploiement
    deploy = deploy_service(service_id)
    if not deploy:
        print("❌ Échec déploiement")
        return
    
    # 4. Vérifier le statut
    success = check_deployment_status(service_id, deploy['id'])
    
    if success:
        print("\n🎉 SAMANTHA EST LIVE !")
        print(f"🔗 URL: {service['serviceDetails']['url']}")
        print("📱 Testez votre bot Telegram maintenant !")
    else:
        print("\n⚠️ Vérifiez le dashboard Render pour plus de détails")

if __name__ == "__main__":
    main()