"""
Samantha - AI Agent with memory, web search, and budget tracking
Startup-style efficient assistant with continuous learning
"""

import asyncio
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass

import logfire
from pydantic_ai import Agent, RunContext, ModelRetry
from pydantic_ai.models.openai import OpenAIModel

from memory_manager import MemoryManager
from search_tools import search_manager
from budget_tracker import BudgetTracker
from agent_prompts import BASE_SYSTEM_PROMPT, build_dynamic_prompt, get_search_enhanced_prompt, get_memory_enhanced_prompt
from supabase import create_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure logfire (optional monitoring)
logfire.configure(send_to_logfire='if-token-present')

@dataclass
class AgentDeps:
    memory_manager: MemoryManager
    budget_tracker: BudgetTracker
    user_id: str
    adaptive_layers: list = None

class SamanthaAgent:
    def __init__(self, openai_api_key: str, supabase_url: str, supabase_key: str, 
                 daily_budget: float = 1.50, monthly_budget: float = 40.00):
        """Initialize Samantha with all dependencies"""
        
        # Initialize components
        self.supabase = create_client(supabase_url, supabase_key)
        self.memory_manager = MemoryManager(supabase_url, supabase_key)
        self.budget_tracker = BudgetTracker(self.supabase, daily_budget, monthly_budget)
        
        # Initialize Pydantic AI agent
        # Set OpenAI API key as environment variable (required by pydantic-ai)
        os.environ['OPENAI_API_KEY'] = openai_api_key
        
        self.agent = Agent(
            'openai:gpt-4o-mini',
            deps_type=AgentDeps,
            retries=2
        )
        
        # Register tools
        self._register_tools()
        
        logger.info("Samantha initialized successfully")
    
    async def initialize(self):
        """Initialize database tables and setup"""
        await self.memory_manager.initialize_tables()
        logger.info("Database initialized")
    
    def _register_tools(self):
        """Register all agent tools"""
        
        @self.agent.tool
        async def web_search(ctx: RunContext[AgentDeps], query: str) -> str:
            """
            Search the web for current information using DuckDuckGo.
            Use this when you need recent information or facts not in your training data.
            
            Args:
                query: The search query
                
            Returns:
                Formatted search results
            """
            try:
                results = await search_manager.smart_search(query)
                return results
            except Exception as e:
                logger.error(f"Search error: {e}")
                return f"❌ Erreur de recherche: {str(e)}"
        
        @self.agent.tool  
        async def add_to_memory(ctx: RunContext[AgentDeps], info: str, category: str = "general") -> str:
            """
            Add important information to long-term memory.
            Use this for user preferences, important facts, or context to remember.
            
            Args:
                info: Information to remember
                category: Category for organization (preferences, facts, context, etc.)
                
            Returns:
                Confirmation message
            """
            try:
                await ctx.deps.memory_manager.add_to_long_term_memory(
                    ctx.deps.user_id, category, info
                )
                return f"✅ Ajouté en mémoire: {info} (catégorie: {category})"
            except Exception as e:
                logger.error(f"Memory error: {e}")
                return f"❌ Erreur mémoire: {str(e)}"
        
        @self.agent.tool
        async def get_budget_status(ctx: RunContext[AgentDeps]) -> str:
            """
            Check current budget status and spending for the user.
            
            Returns:
                Budget information and usage statistics
            """
            try:
                budget_status = await ctx.deps.budget_tracker.check_budget_status(ctx.deps.user_id)
                return ctx.deps.budget_tracker.format_budget_status(budget_status)
            except Exception as e:
                logger.error(f"Budget check error: {e}")
                return f"❌ Erreur budget: {str(e)}"
    
    async def process_message(self, user_id: str, message: str, force_search: bool = False) -> str:
        """
        Process a user message with full context and capabilities
        
        Args:
            user_id: User identifier
            message: User message
            force_search: Force web search even if not needed
            
        Returns:
            Agent response
        """
        try:
            # Check budget first
            can_proceed, budget_msg = await self.budget_tracker.can_make_request(user_id)
            if not can_proceed:
                return budget_msg
            
            # Store user message
            await self.memory_manager.store_message(user_id, message, is_user=True)
            
            # Get memory context
            memory_context = await self.memory_manager.get_context_for_conversation(user_id)
            
            # Get adaptive layers for this user
            adaptive_layers = await self._get_user_adaptive_layers(user_id)
            
            # Build dynamic prompt
            system_prompt = build_dynamic_prompt(BASE_SYSTEM_PROMPT, adaptive_layers)
            
            # Add memory context if available
            if memory_context:
                system_prompt = get_memory_enhanced_prompt(system_prompt, memory_context)
            
            # Determine if we need web search
            needs_search = force_search or self._should_search(message)
            search_context = ""
            
            if needs_search:
                search_results = await search_manager.smart_search(message)
                search_context = search_results
                system_prompt = get_search_enhanced_prompt(system_prompt, search_results)
            
            # Create dependencies
            deps = AgentDeps(
                memory_manager=self.memory_manager,
                budget_tracker=self.budget_tracker,
                user_id=user_id,
                adaptive_layers=adaptive_layers
            )
            
            # Run agent with dynamic prompt
            self.agent.system_prompt = system_prompt
            
            result = await self.agent.run(message, deps=deps)
            response = result.data
            
            # Store agent response
            await self.memory_manager.store_message(user_id, response, is_user=False)
            
            # Track usage and costs
            input_text = system_prompt + message + memory_context + search_context
            await self.budget_tracker.track_usage(user_id, input_text, response)
            
            # Check for budget warnings
            warning = await self.budget_tracker.get_budget_warning(user_id)
            if warning:
                response += f"\n\n{warning}"
            
            # Update medium-term memory if needed
            if await self.memory_manager.should_update_medium_term(user_id):
                await self._update_medium_term_memory(user_id)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"❌ Erreur: {str(e)}. Réessayez dans un moment."
    
    async def update_system_prompt(self, user_id: str, new_prompt: str) -> str:
        """Update the system prompt for a specific user"""
        try:
            await self.memory_manager.add_to_long_term_memory(
                user_id, "custom_prompt", new_prompt
            )
            return f"✅ Prompt mis à jour: {new_prompt[:100]}..."
        except Exception as e:
            logger.error(f"Error updating prompt: {e}")
            return f"❌ Erreur mise à jour prompt: {str(e)}"
    
    async def _get_user_adaptive_layers(self, user_id: str) -> list:
        """Get adaptive prompt layers for user"""
        try:
            long_term_memory = await self.memory_manager.get_long_term_memory(user_id)
            if not long_term_memory:
                return []
            
            layers = []
            
            # Add custom prompt if exists
            if 'custom_prompt' in long_term_memory:
                layers.append(long_term_memory['custom_prompt'])
            
            # Add learned preferences
            if 'communication_style' in long_term_memory:
                style = long_term_memory['communication_style']
                layers.append(f"Style de communication préféré: {style}")
            
            if 'response_length' in long_term_memory:
                length = long_term_memory['response_length']
                layers.append(f"Longueur de réponse préférée: {length}")
            
            return layers
            
        except Exception as e:
            logger.error(f"Error getting adaptive layers: {e}")
            return []
    
    def _should_search(self, message: str) -> bool:
        """Determine if message requires web search"""
        search_indicators = [
            'recherche', 'trouve', 'cherche', 'infos sur', 'actualité',
            'récent', 'nouveau', 'dernier', 'current', 'latest', 'news',
            'prix', 'course', 'météo', 'horaire', 'quoi de neuf'
        ]
        
        message_lower = message.lower()
        return any(indicator in message_lower for indicator in search_indicators)
    
    async def _update_medium_term_memory(self, user_id: str) -> None:
        """Update medium-term memory with conversation summary"""
        try:
            recent_messages = await self.memory_manager.get_short_term_memory(user_id)
            if len(recent_messages) < 10:  # Not enough for summary
                return
            
            # Create summary prompt
            conversation_text = "\n".join([
                f"{'User' if msg['is_user_message'] else 'Samantha'}: {msg['message']}"
                for msg in recent_messages[-20:]  # Last 20 messages
            ])
            
            summary_prompt = f"""Résume cette conversation en français en 2-3 phrases, en gardant:
1. Les préférences utilisateur importantes
2. Les sujets principaux abordés  
3. Le style de communication préféré

Conversation:
{conversation_text}

Résumé:"""
            
            # Use a simple model call for summary (cheaper)
            deps = AgentDeps(
                memory_manager=self.memory_manager,
                budget_tracker=self.budget_tracker,
                user_id=user_id
            )
            
            # Create temporary agent for summary
            summary_agent = Agent(
                self.agent.model,
                system_prompt="Tu es un assistant qui résume des conversations de manière concise."
            )
            
            result = await summary_agent.run(summary_prompt)
            summary = result.data
            
            # Store summary
            await self.memory_manager.update_medium_term_memory(user_id, summary)
            
            logger.info(f"Updated medium-term memory for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error updating medium-term memory: {e}")

# Global agent instance (will be initialized in main)
samantha: Optional[SamanthaAgent] = None

def get_agent() -> SamanthaAgent:
    """Get the global agent instance"""
    if samantha is None:
        raise RuntimeError("Agent not initialized. Call initialize_agent() first.")
    return samantha

async def initialize_agent(openai_api_key: str, supabase_url: str, supabase_key: str,
                          daily_budget: float = 1.50, monthly_budget: float = 40.00) -> SamanthaAgent:
    """Initialize the global agent instance"""
    global samantha
    samantha = SamanthaAgent(openai_api_key, supabase_url, supabase_key, daily_budget, monthly_budget)
    await samantha.initialize()
    return samantha