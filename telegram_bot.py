"""
Telegram bot interface for Samantha
Handles all Telegram interactions, commands, and message processing
"""

import asyncio
import os
import logging
from typing import Dict, Optional
from datetime import datetime

from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

from agent import get_agent, initialize_agent
from memory_manager import MemoryManager
from budget_tracker import BudgetTracker

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SamanthaTelegramBot:
    def __init__(self, telegram_token: str, openai_api_key: str, supabase_url: str, 
                 supabase_key: str, daily_budget: float = 1.50, monthly_budget: float = 40.00):
        """Initialize Telegram bot with Samantha agent"""
        self.telegram_token = telegram_token
        self.openai_api_key = openai_api_key
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.daily_budget = daily_budget
        self.monthly_budget = monthly_budget
        
        # Rate limiting (simple in-memory for now)
        self.user_last_message: Dict[str, datetime] = {}
        self.rate_limit_seconds = 2  # Minimum 2 seconds between messages
        
        # Application will be set in initialize()
        self.application: Optional[Application] = None
        
    async def initialize(self):
        """Initialize the bot and agent"""
        # Initialize Samantha agent
        await initialize_agent(
            self.openai_api_key, 
            self.supabase_url, 
            self.supabase_key,
            self.daily_budget,
            self.monthly_budget
        )
        
        # Create Telegram application
        self.application = Application.builder().token(self.telegram_token).build()
        
        # Register handlers
        await self._register_handlers()
        
        # Set bot commands
        await self._set_bot_commands()
        
        logger.info("Samantha Telegram bot initialized successfully")
    
    async def _register_handlers(self):
        """Register all command and message handlers"""
        app = self.application
        
        # Command handlers
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("prompt", self.prompt_command))
        app.add_handler(CommandHandler("search", self.search_command))
        app.add_handler(CommandHandler("budget", self.budget_command))
        app.add_handler(CommandHandler("memory", self.memory_command))
        app.add_handler(CommandHandler("stats", self.stats_command))
        app.add_handler(CommandHandler("reset", self.reset_command))
        
        # Message handler (for regular conversation)
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Error handler
        app.add_error_handler(self.error_handler)
    
    async def _set_bot_commands(self):
        """Set bot commands menu"""
        commands = [
            BotCommand("start", "Démarrer une conversation avec Samantha"),
            BotCommand("help", "Voir la liste des commandes"),
            BotCommand("prompt", "Changer le comportement de Samantha"),
            BotCommand("search", "Forcer une recherche web"),
            BotCommand("budget", "Vérifier le budget et les coûts"),
            BotCommand("memory", "Gérer la mémoire long terme"),
            BotCommand("stats", "Voir les statistiques d'utilisation"),
            BotCommand("reset", "Réinitialiser la conversation")
        ]
        
        await self.application.bot.set_my_commands(commands)
    
    def _check_rate_limit(self, user_id: str) -> bool:
        """Check if user is within rate limits"""
        now = datetime.utcnow()
        last_message = self.user_last_message.get(user_id)
        
        if last_message:
            time_diff = (now - last_message).total_seconds()
            if time_diff < self.rate_limit_seconds:
                return False
        
        self.user_last_message[user_id] = now
        return True
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = str(update.effective_user.id)
        
        welcome_message = """👋 **Salut ! Je suis Samantha !**

Je suis votre assistante IA avec un style startup : no bullshit, full efficiency.

**Mes capacités :**
• 🔍 Recherche web instantanée
• 🧠 Mémoire des conversations  
• 💰 Gestion de budget intelligent
• 🎯 Réponses directes et actionables

**Commandes utiles :**
/help - Voir toutes les commandes
/search [requête] - Recherche web forcée
/budget - Vérifier les coûts
/prompt [nouveau] - Changer mon comportement

**Prêt à bosser ensemble ? Posez-moi votre première question !** 🚀"""
        
        await update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """🤖 **COMMANDES SAMANTHA**

**💬 Conversation :**
Tapez simplement votre message - je réponds avec recherche et mémoire !

**🔧 Commandes spéciales :**
• `/search [requête]` - Force recherche web
• `/prompt [nouveau]` - Change mon comportement
• `/budget` - Statut budget et coûts  
• `/memory add [info]` - Ajoute en mémoire long terme
• `/stats` - Statistiques d'utilisation
• `/reset` - Remet à zéro la conversation

**💡 Exemples :**
• `Recherche les dernières news IA`
• `/search prix bitcoin aujourd'hui`
• `/prompt Tu es maintenant un expert marketing`
• `/memory add J'aime les réponses courtes`

**💰 Budget :** {daily}€/jour, {monthly}€/mois
**🔄 Style :** Startup no bullshit, efficacité max

**Questions ? Tapez juste votre message !**"""
        
        formatted_help = help_text.format(
            daily=self.daily_budget,
            monthly=self.monthly_budget
        )
        
        await update.message.reply_text(formatted_help, parse_mode=ParseMode.MARKDOWN)
    
    async def prompt_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /prompt command"""
        user_id = str(update.effective_user.id)
        
        if not context.args:
            await update.message.reply_text(
                "❓ **Usage :** `/prompt [nouveau comportement]`\n\n"
                "**Exemples :**\n"
                "• `/prompt Tu es un expert en marketing`\n"
                "• `/prompt Réponds toujours avec des bullet points`\n"
                "• `/prompt Sois très concis, max 2 phrases`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        new_prompt = " ".join(context.args)
        
        try:
            agent = get_agent()
            result = await agent.update_system_prompt(user_id, new_prompt)
            await update.message.reply_text(f"✅ **Prompt mis à jour !**\n\n{result}")
        except Exception as e:
            logger.error(f"Prompt update error: {e}")
            await update.message.reply_text(f"❌ Erreur: {str(e)}")
    
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command"""
        user_id = str(update.effective_user.id)
        
        if not context.args:
            await update.message.reply_text(
                "❓ **Usage :** `/search [votre recherche]`\n\n"
                "**Exemple :** `/search dernières actualités IA 2024`"
            )
            return
        
        if not self._check_rate_limit(user_id):
            await update.message.reply_text("⏳ Doucement ! Attendez 2 secondes entre les messages.")
            return
        
        query = " ".join(context.args)
        
        # Show typing indicator
        await update.message.reply_text("🔍 Recherche en cours...")
        
        try:
            agent = get_agent()
            response = await agent.process_message(user_id, query, force_search=True)
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Search error: {e}")
            await update.message.reply_text(f"❌ Erreur de recherche: {str(e)}")
    
    async def budget_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /budget command"""
        user_id = str(update.effective_user.id)
        
        try:
            agent = get_agent()
            budget_status = await agent.budget_tracker.check_budget_status(user_id)
            stats = await agent.budget_tracker.get_usage_stats(user_id, 7)
            
            message = agent.budget_tracker.format_budget_status(budget_status)
            
            message += f"""

📊 **STATS 7 DERNIERS JOURS:**
• Messages: {stats['total_messages']}
• Coût total: ${stats['total_cost']:.3f}
• Coût moyen/message: ${stats['avg_cost_per_message']:.4f}
• Tokens utilisés: {stats['total_tokens']:,}"""
            
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Budget check error: {e}")
            await update.message.reply_text(f"❌ Erreur budget: {str(e)}")
    
    async def memory_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /memory command"""
        user_id = str(update.effective_user.id)
        
        if not context.args:
            await update.message.reply_text(
                "❓ **Usage :** `/memory add [information]`\n\n"
                "**Exemples :**\n"
                "• `/memory add Je préfère les réponses courtes`\n"
                "• `/memory add Je travaille dans le marketing`\n"
                "• `/memory add J'aime les bullet points`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        if context.args[0] == "add" and len(context.args) > 1:
            info = " ".join(context.args[1:])
            try:
                agent = get_agent()
                await agent.memory_manager.add_to_long_term_memory(user_id, "user_preference", info)
                await update.message.reply_text(f"✅ **Ajouté en mémoire :**\n{info}")
            except Exception as e:
                logger.error(f"Memory add error: {e}")
                await update.message.reply_text(f"❌ Erreur mémoire: {str(e)}")
        else:
            await update.message.reply_text("❓ Utilisez: `/memory add [information]`")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        user_id = str(update.effective_user.id)
        
        try:
            agent = get_agent()
            memory_stats = await agent.memory_manager.get_memory_stats(user_id)
            usage_stats = await agent.budget_tracker.get_usage_stats(user_id, 30)
            
            message = f"""📈 **VOS STATISTIQUES**

**💾 Mémoire :**
• Messages stockés: {memory_stats['total_messages']}
• Tokens en mémoire: {memory_stats['total_tokens']:,}
• Mémoire moyen terme: {'✅' if memory_stats['has_medium_term'] else '❌'}
• Mémoire long terme: {'✅' if memory_stats['has_long_term'] else '❌'}

**💰 Usage (30 jours) :**
• Messages: {usage_stats['total_messages']}
• Coût total: ${usage_stats['total_cost']:.2f}
• Coût moyen: ${usage_stats['avg_cost_per_message']:.4f}/msg
• Tokens: {usage_stats['total_tokens']:,}

**⚡ Performance :**
• Agent actif depuis le début
• Recherches web illimitées
• Mémoire adaptive activée"""
            
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Stats error: {e}")
            await update.message.reply_text(f"❌ Erreur stats: {str(e)}")
    
    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /reset command"""
        user_id = str(update.effective_user.id)
        
        try:
            agent = get_agent()
            # Clear short-term memory by cleaning up recent conversations
            await agent.memory_manager.cleanup_old_conversations(user_id, days_to_keep=0)
            
            await update.message.reply_text(
                "🔄 **Conversation remise à zéro !**\n\n"
                "• Mémoire court terme vidée\n"
                "• Mémoire long terme conservée\n"
                "• Prêt pour une nouvelle conversation !"
            )
            
        except Exception as e:
            logger.error(f"Reset error: {e}")
            await update.message.reply_text(f"❌ Erreur reset: {str(e)}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages"""
        user_id = str(update.effective_user.id)
        message = update.message.text
        
        # Rate limiting
        if not self._check_rate_limit(user_id):
            await update.message.reply_text("⏳ Doucement ! Attendez 2 secondes entre les messages.")
            return
        
        # Show typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        try:
            agent = get_agent()
            response = await agent.process_message(user_id, message)
            
            # Split long responses if needed
            if len(response) > 4096:
                for i in range(0, len(response), 4096):
                    await update.message.reply_text(
                        response[i:i+4096], 
                        parse_mode=ParseMode.MARKDOWN
                    )
            else:
                await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
                
        except Exception as e:
            logger.error(f"Message handling error: {e}")
            await update.message.reply_text(
                f"❌ Oups ! Erreur temporaire: {str(e)}\n\nRéessayez dans un moment."
            )
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.message:
            await update.message.reply_text(
                "❌ Erreur technique temporaire. Réessayez dans un moment."
            )
    
    async def start_polling(self):
        """Start the bot with polling"""
        if not self.application:
            await self.initialize()
        
        logger.info("Starting Samantha Telegram bot...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        # Keep running
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            logger.info("Stopping bot...")
        finally:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()

async def main():
    """Main function to run the bot"""
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Get configuration
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    openai_api_key = os.getenv('OPENAI_API_KEY')
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    daily_budget = float(os.getenv('DAILY_BUDGET_USD', '1.50'))
    monthly_budget = float(os.getenv('MONTHLY_BUDGET_USD', '40.00'))
    
    # Validate configuration
    if not all([telegram_token, openai_api_key, supabase_url, supabase_key]):
        logger.error("Missing required environment variables!")
        return
    
    # Create and start bot
    bot = SamanthaTelegramBot(
        telegram_token=telegram_token,
        openai_api_key=openai_api_key,
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        daily_budget=daily_budget,
        monthly_budget=monthly_budget
    )
    
    await bot.start_polling()

if __name__ == "__main__":
    asyncio.run(main())