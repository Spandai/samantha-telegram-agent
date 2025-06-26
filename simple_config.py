"""
Configuration simple pour Samantha
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Variables d'environnement requises
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Variables optionnelles avec defaults
DAILY_BUDGET_USD = float(os.getenv('DAILY_BUDGET_USD', '1.50'))
AGENT_NAME = os.getenv('AGENT_NAME', 'Samantha')
DEFAULT_TONE = os.getenv('DEFAULT_TONE', 'startup style no bullshit full efficiency')

# Base de données locale
DB_PATH = 'samantha.db'

# Validation
def validate_config():
    """Vérifier que la configuration est valide"""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN manquant")
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY manquant")
    
    print("✅ Configuration validée")
    print(f"📱 Agent: {AGENT_NAME}")
    print(f"💰 Budget: ${DAILY_BUDGET_USD}/jour")

if __name__ == "__main__":
    validate_config()