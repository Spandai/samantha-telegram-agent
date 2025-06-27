"""
Samantha - Bot Telegram Ultra-Simple
Version optimisée : 150 lignes vs 950+ lignes
Mêmes fonctionnalités, 10x plus rapide
"""

import os
import asyncio
import logging
import requests
from datetime import datetime, timezone
from typing import List, Optional
from dataclasses import dataclass
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

import openai
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from supabase import create_client, Client

# Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthHandler(BaseHTTPRequestHandler):
    """Health check server pour Render"""
    
    def do_GET(self):
        """Répondre OK aux health checks"""
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Samantha Bot is LIVE! 🤖')
    
    def log_message(self, format, *args):
        """Supprimer logs HTTP verbeux"""
        pass

def start_health_server():
    """Lancer serveur health en arrière-plan"""
    port = int(os.getenv('PORT', 8000))
    try:
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        logger.info(f"🏥 Health server démarré sur port {port}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"❌ Erreur health server: {e}")

@dataclass
class Config:
    telegram_token: str
    openai_api_key: str
    supabase_url: str
    supabase_key: str
    daily_budget: float = 1.50
    agent_name: str = "Samantha"

class SimpleMemory:
    """Mémoire simple mais efficace avec Supabase"""
    
    def __init__(self, supabase_url: str, supabase_key: str):
        self.supabase = create_client(supabase_url, supabase_key)
        self.init_db()
    
    def init_db(self):
        """Tables créées via Supabase dashboard"""
        # Tables: conversations, memory, budget
        # Schéma identique à SQLite mais géré par Supabase
        pass
    
    def store_message(self, user_id: str, message: str, is_user: bool = True):
        """Stocker un message"""
        try:
            self.supabase.table('conversations').insert({
                'user_id': user_id,
                'message': message,
                'is_user': is_user
            }).execute()
        except Exception as e:
            logger.error(f"Erreur store_message: {e}")
    
    def get_context(self, user_id: str, limit: int = 10) -> str:
        """Récupérer le contexte récent"""
        try:
            response = self.supabase.table('conversations').select('message, is_user').eq('user_id', user_id).order('timestamp', desc=True).limit(limit).execute()
            
            messages = []
            for row in reversed(response.data):
                speaker = "User" if row['is_user'] else "Samantha"
                messages.append(f"{speaker}: {row['message']}")
            
            return "\n".join(messages)
        except Exception as e:
            logger.error(f"Erreur get_context: {e}")
            return ""
    
    def search_memory(self, user_id: str, query: str) -> List[str]:
        """Rechercher dans l'historique"""
        try:
            response = self.supabase.table('conversations').select('message').eq('user_id', user_id).ilike('message', f'%{query}%').order('timestamp', desc=True).limit(5).execute()
            return [row['message'] for row in response.data]
        except Exception as e:
            logger.error(f"Erreur search_memory: {e}")
            return []
    
    def remember(self, user_id: str, key: str, value: str):
        """Stocker info importante"""
        try:
            # Upsert: update if exists, insert if not
            self.supabase.table('memory').upsert({'user_id': user_id, 'key': key, 'value': value}).execute()
        except Exception as e:
            logger.error(f"Erreur remember: {e}")
    
    def get_memory(self, user_id: str, key: str) -> Optional[str]:
        """Récupérer info stockée"""
        try:
            response = self.supabase.table('memory').select('value').eq('user_id', user_id).eq('key', key).execute()
            return response.data[0]['value'] if response.data else None
        except Exception as e:
            logger.error(f"Erreur get_memory: {e}")
            return None

class SimpleSearch:
    """Recherche web simple avec DuckDuckGo"""
    
    @staticmethod
    def search(query: str) -> str:
        """Recherche rapide DuckDuckGo"""
        try:
            url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1"
            response = requests.get(url, timeout=5)
            data = response.json()
            
            if data.get('Abstract'):
                return f"🔍 {data['Abstract'][:300]}..."
            elif data.get('Definition'):
                return f"📖 {data['Definition'][:300]}..."
            else:
                return f"🌐 Recherche effectuée pour: {query}"
                
        except Exception as e:
            return f"❌ Erreur de recherche: {str(e)}"

class SimpleBudget:
    """Budget tracking ultra-simple"""
    
    def __init__(self, memory: SimpleMemory, daily_limit: float):
        self.memory = memory
        self.daily_limit = daily_limit
    
    def track_cost(self, user_id: str, cost: float):
        """Tracker un coût"""
        try:
            self.memory.supabase.table('budget').insert({
                'user_id': user_id,
                'cost': cost
            }).execute()
        except Exception as e:
            logger.error(f"Erreur track_cost: {e}")
    
    def get_daily_spent(self, user_id: str) -> float:
        """Coût du jour"""
        try:
            # UTC timezone aware
            today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            response = self.memory.supabase.table('budget').select('cost').eq('user_id', user_id).gte('timestamp', today).execute()
            return sum(row['cost'] for row in response.data)
        except Exception as e:
            logger.error(f"Erreur get_daily_spent: {e}")
            return 0
    
    def can_spend(self, user_id: str) -> bool:
        """Vérifier budget"""
        return self.get_daily_spent(user_id) < self.daily_limit

class SamanthaBot:
    """Bot Telegram Ultra-Simple"""
    
    def __init__(self, config: Config):
        self.config = config
        self.memory = SimpleMemory(config.supabase_url, config.supabase_key)
        self.search = SimpleSearch()
        self.budget = SimpleBudget(self.memory, config.daily_budget)
        
        # OpenAI client
        self.openai_client = openai.OpenAI(api_key=config.openai_api_key)
        
        # Telegram app
        self.app = Application.builder().token(config.telegram_token).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup commandes Telegram"""
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("search", self.search_command))
        self.app.add_handler(CommandHandler("remember", self.remember_command))
        self.app.add_handler(CommandHandler("budget", self.budget_command))
        self.app.add_handler(CommandHandler("prompt", self.prompt_command))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /start"""
        welcome = f"""👋 Salut ! Je suis {self.config.agent_name} !

🤖 Assistant IA style startup : no bullshit, full efficiency.

**Commandes :**
/search [requête] - Recherche web
/remember [info] - Mémoriser quelque chose  
/budget - Vérifier les coûts
/prompt [nouveau] - Changer mon comportement

**Prêt à bosser ? Posez votre question !** 🚀"""
        
        await update.message.reply_text(welcome)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /help"""
        help_text = """🤖 **COMMANDES SAMANTHA**

💬 **Message normal** - Conversation intelligente
🔍 `/search [requête]` - Recherche web forcée
🧠 `/remember [info]` - Mémoriser info importante
💰 `/budget` - Statut budget quotidien
🎯 `/prompt [nouveau]` - Changer comportement

**Budget:** {:.2f}€/jour
**Style:** Startup no bullshit, efficacité max""".format(self.config.daily_budget)
        
        await update.message.reply_text(help_text)
    
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /search"""
        if not context.args:
            await update.message.reply_text("Usage: /search [votre recherche]")
            return
        
        query = " ".join(context.args)
        result = self.search.search(query)
        await update.message.reply_text(result)
    
    async def remember_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /remember"""
        if not context.args:
            await update.message.reply_text("Usage: /remember [information à retenir]")
            return
        
        user_id = str(update.effective_user.id)
        info = " ".join(context.args)
        
        # Stocker avec timestamp comme clé
        key = f"memory_{datetime.now().strftime('%Y%m%d_%H%M')}"
        self.memory.remember(user_id, key, info)
        
        await update.message.reply_text(f"✅ Mémorisé: {info}")
    
    async def budget_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /budget"""
        user_id = str(update.effective_user.id)
        spent = self.budget.get_daily_spent(user_id)
        remaining = self.config.daily_budget - spent
        
        status = f"""💰 **BUDGET AUJOURD'HUI**
        
Dépensé: ${spent:.3f}
Limite: ${self.config.daily_budget:.2f}
Restant: ${remaining:.3f}

{"✅ OK" if remaining > 0 else "❌ Limite atteinte"}"""
        
        await update.message.reply_text(status)
    
    async def prompt_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /prompt"""
        if not context.args:
            await update.message.reply_text("Usage: /prompt [nouveau comportement]")
            return
        
        user_id = str(update.effective_user.id)
        new_prompt = " ".join(context.args)
        
        # Stocker le prompt personnalisé
        self.memory.remember(user_id, "custom_prompt", new_prompt)
        
        await update.message.reply_text(f"✅ Prompt mis à jour: {new_prompt}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gérer message normal"""
        user_id = str(update.effective_user.id)
        message = update.message.text
        
        # Vérifier budget
        if not self.budget.can_spend(user_id):
            await update.message.reply_text("⛔ Budget quotidien atteint. Reset demain.")
            return
        
        # Stocker message utilisateur
        self.memory.store_message(user_id, message, True)
        
        # Préparer contexte
        context_text = self.memory.get_context(user_id, 5)
        custom_prompt = self.memory.get_memory(user_id, "custom_prompt")
        
        # Prompt système
        system_prompt = custom_prompt or f"""Tu es {self.config.agent_name}, assistante IA style startup : no bullshit, full efficiency.

Réponds de manière directe, pragmatique et actionnable. 
Si tu ne sais pas, dis-le. Propose toujours des solutions concrètes."""
        
        # Vérifier si recherche nécessaire
        search_keywords = ['recherche', 'trouve', 'cherche', 'actualité', 'news', 'prix']
        needs_search = any(word in message.lower() for word in search_keywords)
        
        search_result = ""
        if needs_search:
            search_result = f"\n\nRécherche web: {self.search.search(message)}"
        
        # Appeler OpenAI
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Contexte récent:\n{context_text}\n\nMessage actuel: {message}{search_result}"}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            reply = response.choices[0].message.content
            
            # Tracker coût (estimation)
            cost = len(message + reply) * 0.000001  # Estimation grossière
            self.budget.track_cost(user_id, cost)
            
            # Stocker réponse
            self.memory.store_message(user_id, reply, False)
            
            await update.message.reply_text(reply)
            
        except Exception as e:
            logger.error(f"Erreur OpenAI: {e}")
            await update.message.reply_text(f"❌ Erreur temporaire: {str(e)}")
    
    async def run(self):
        """Lancer le bot"""
        logger.info(f"Démarrage {self.config.agent_name}...")
        
        # Configurer commandes
        commands = [
            BotCommand("start", "Démarrer conversation"),
            BotCommand("help", "Aide et commandes"),
            BotCommand("search", "Recherche web"),
            BotCommand("remember", "Mémoriser info"),
            BotCommand("budget", "Vérifier budget"),
            BotCommand("prompt", "Changer comportement")
        ]
        await self.app.bot.set_my_commands(commands)
        
        # Démarrer
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        
        logger.info(f"✅ {self.config.agent_name} est LIVE !")
        
        # Maintenir en vie
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            logger.info("Arrêt du bot...")
        finally:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()

async def main():
    """Point d'entrée principal"""
    from dotenv import load_dotenv
    load_dotenv()
    
    # Démarrer health server en arrière-plan (pour Render)
    health_thread = Thread(target=start_health_server, daemon=True)
    health_thread.start()
    logger.info("🏥 Health server thread démarré")
    
    # Configuration
    config = Config(
        telegram_token=os.getenv('TELEGRAM_BOT_TOKEN'),
        openai_api_key=os.getenv('OPENAI_API_KEY'),
        supabase_url=os.getenv('SUPABASE_URL'),
        supabase_key=os.getenv('SUPABASE_ANON_KEY'),
        daily_budget=float(os.getenv('DAILY_BUDGET_USD', '1.50')),
        agent_name=os.getenv('AGENT_NAME', 'Samantha')
    )
    
    # Validation
    if not config.telegram_token or not config.openai_api_key or not config.supabase_url or not config.supabase_key:
        logger.error("❌ Variables TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, SUPABASE_URL et SUPABASE_ANON_KEY requises")
        return
    
    # Lancer bot
    bot = SamanthaBot(config)
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())