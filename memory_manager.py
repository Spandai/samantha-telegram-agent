"""
Multi-level memory system for Samantha
Handles short-term, medium-term, and long-term memory with Supabase
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from supabase import create_client, Client
import tiktoken

logger = logging.getLogger(__name__)

@dataclass
class MemoryEntry:
    content: str
    timestamp: datetime
    importance: int  # 1-10 scale
    context: str
    tokens: int

class MemoryManager:
    def __init__(self, supabase_url: str, supabase_key: str, max_messages: int = 50):
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.max_messages = max_messages
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
    async def initialize_tables(self):
        """Initialize Supabase tables for memory system"""
        try:
            # Create conversations table
            self.supabase.table('conversations').select('id').limit(1).execute()
        except Exception:
            logger.info("Creating conversations table...")
            # Table will be created via Supabase dashboard or migration
            
        try:
            # Create memory_layers table  
            self.supabase.table('memory_layers').select('user_id').limit(1).execute()
        except Exception:
            logger.info("Creating memory_layers table...")
            
        try:
            # Create budget_tracking table
            self.supabase.table('budget_tracking').select('user_id').limit(1).execute()
        except Exception:
            logger.info("Creating budget_tracking table...")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        try:
            return len(self.tokenizer.encode(text))
        except Exception:
            return len(text.split()) * 1.3  # Rough estimate

    async def store_message(self, user_id: str, message: str, is_user: bool = True) -> None:
        """Store a message in conversations table"""
        try:
            tokens = self.count_tokens(message)
            
            data = {
                'user_id': user_id,
                'message': message,
                'is_user_message': is_user,
                'tokens': tokens,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table('conversations').insert(data).execute()
            logger.debug(f"Stored message for user {user_id}: {len(message)} chars")
            
        except Exception as e:
            logger.error(f"Error storing message: {e}")

    async def get_short_term_memory(self, user_id: str) -> List[Dict]:
        """Get last 50 messages for short-term memory"""
        try:
            result = self.supabase.table('conversations')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('timestamp', desc=True)\
                .limit(self.max_messages)\
                .execute()
            
            return list(reversed(result.data))  # Chronological order
            
        except Exception as e:
            logger.error(f"Error getting short-term memory: {e}")
            return []

    async def get_medium_term_memory(self, user_id: str) -> Optional[str]:
        """Get weekly summary and important facts"""
        try:
            result = self.supabase.table('memory_layers')\
                .select('medium_term')\
                .eq('user_id', user_id)\
                .single()\
                .execute()
            
            return result.data.get('medium_term') if result.data else None
            
        except Exception as e:
            logger.debug(f"No medium-term memory found for user {user_id}")
            return None

    async def get_long_term_memory(self, user_id: str) -> Optional[Dict]:
        """Get user profile and key memories"""
        try:
            result = self.supabase.table('memory_layers')\
                .select('long_term')\
                .eq('user_id', user_id)\
                .single()\
                .execute()
            
            long_term_data = result.data.get('long_term') if result.data else None
            
            if isinstance(long_term_data, str):
                return json.loads(long_term_data)
            
            return long_term_data
            
        except Exception as e:
            logger.debug(f"No long-term memory found for user {user_id}")
            return {}

    async def update_medium_term_memory(self, user_id: str, summary: str) -> None:
        """Update medium-term memory with new summary"""
        try:
            # Check if record exists
            existing = self.supabase.table('memory_layers')\
                .select('user_id')\
                .eq('user_id', user_id)\
                .execute()
            
            data = {
                'user_id': user_id,
                'medium_term': summary,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            if existing.data:
                # Update existing
                self.supabase.table('memory_layers')\
                    .update(data)\
                    .eq('user_id', user_id)\
                    .execute()
            else:
                # Insert new
                self.supabase.table('memory_layers')\
                    .insert(data)\
                    .execute()
                    
            logger.info(f"Updated medium-term memory for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error updating medium-term memory: {e}")

    async def add_to_long_term_memory(self, user_id: str, key: str, value: Any) -> None:
        """Add specific information to long-term memory"""
        try:
            current_memory = await self.get_long_term_memory(user_id) or {}
            current_memory[key] = value
            current_memory['last_updated'] = datetime.utcnow().isoformat()
            
            # Check if record exists
            existing = self.supabase.table('memory_layers')\
                .select('user_id')\
                .eq('user_id', user_id)\
                .execute()
            
            data = {
                'user_id': user_id,
                'long_term': json.dumps(current_memory),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            if existing.data:
                # Update existing
                self.supabase.table('memory_layers')\
                    .update(data)\
                    .eq('user_id', user_id)\
                    .execute()
            else:
                # Insert new
                self.supabase.table('memory_layers')\
                    .insert(data)\
                    .execute()
                    
            logger.info(f"Added to long-term memory for user {user_id}: {key}")
            
        except Exception as e:
            logger.error(f"Error adding to long-term memory: {e}")

    async def get_context_for_conversation(self, user_id: str) -> str:
        """Build context string from all memory levels"""
        context_parts = []
        
        # Get long-term memory (user profile)
        long_term = await self.get_long_term_memory(user_id)
        if long_term:
            context_parts.append("PROFIL UTILISATEUR :")
            for key, value in long_term.items():
                if key != 'last_updated':
                    context_parts.append(f"- {key}: {value}")
        
        # Get medium-term memory (weekly summary)
        medium_term = await self.get_medium_term_memory(user_id)
        if medium_term:
            context_parts.append("\nRÉSUMÉ RÉCENT :")
            context_parts.append(medium_term)
        
        # Get short-term memory (recent messages)
        short_term = await self.get_short_term_memory(user_id)
        if short_term:
            context_parts.append("\nCONVERSATIONS RÉCENTES :")
            for msg in short_term[-10:]:  # Last 10 messages for context
                speaker = "Utilisateur" if msg['is_user_message'] else "Samantha"
                context_parts.append(f"{speaker}: {msg['message']}")
        
        return "\n".join(context_parts)

    async def should_update_medium_term(self, user_id: str) -> bool:
        """Check if medium-term memory needs updating (weekly)"""
        try:
            result = self.supabase.table('memory_layers')\
                .select('updated_at')\
                .eq('user_id', user_id)\
                .single()\
                .execute()
            
            if not result.data or not result.data.get('updated_at'):
                return True
                
            last_update = datetime.fromisoformat(result.data['updated_at'].replace('Z', '+00:00'))
            return datetime.utcnow() - last_update > timedelta(days=7)
            
        except Exception:
            return True

    async def cleanup_old_conversations(self, user_id: str, days_to_keep: int = 30) -> None:
        """Clean up conversations older than specified days"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            self.supabase.table('conversations')\
                .delete()\
                .eq('user_id', user_id)\
                .lt('timestamp', cutoff_date.isoformat())\
                .execute()
                
            logger.info(f"Cleaned up old conversations for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up conversations: {e}")

    async def get_memory_stats(self, user_id: str) -> Dict[str, Any]:
        """Get memory usage statistics"""
        try:
            # Count total messages
            messages_result = self.supabase.table('conversations')\
                .select('id', count='exact')\
                .eq('user_id', user_id)\
                .execute()
            
            # Get total tokens used
            tokens_result = self.supabase.table('conversations')\
                .select('tokens')\
                .eq('user_id', user_id)\
                .execute()
            
            total_tokens = sum(msg.get('tokens', 0) for msg in tokens_result.data)
            
            return {
                'total_messages': messages_result.count,
                'total_tokens': total_tokens,
                'has_medium_term': bool(await self.get_medium_term_memory(user_id)),
                'has_long_term': bool(await self.get_long_term_memory(user_id))
            }
            
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return {
                'total_messages': 0,
                'total_tokens': 0,
                'has_medium_term': False,
                'has_long_term': False
            }