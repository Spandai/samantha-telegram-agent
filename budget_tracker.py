"""
Budget tracking system for OpenAI API costs
Monitors spending and enforces daily/monthly limits
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from supabase import Client
import tiktoken

logger = logging.getLogger(__name__)

@dataclass
class UsageStats:
    input_tokens: int
    output_tokens: int
    cost_usd: float
    message_type: str
    timestamp: datetime

class BudgetTracker:
    def __init__(self, supabase_client: Client, daily_limit: float = 1.50, monthly_limit: float = 40.00):
        self.supabase = supabase_client
        self.daily_limit = daily_limit
        self.monthly_limit = monthly_limit
        self.warning_threshold = 0.75
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # OpenAI GPT-4o-mini pricing (as of 2024)
        self.pricing = {
            'gpt-4o-mini': {
                'input': 0.00015 / 1000,   # $0.15 per 1M input tokens
                'output': 0.0006 / 1000,   # $0.60 per 1M output tokens
            },
            'text-embedding-3-small': {
                'input': 0.00002 / 1000,   # $0.02 per 1M tokens
                'output': 0.0,
            }
        }
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        try:
            return len(self.tokenizer.encode(text))
        except Exception:
            # Fallback estimation
            return int(len(text.split()) * 1.3)
    
    def calculate_cost(self, input_text: str, output_text: str, model: str = 'gpt-4o-mini') -> Tuple[int, int, float]:
        """
        Calculate the cost of an API call
        
        Returns:
            Tuple of (input_tokens, output_tokens, cost_usd)
        """
        input_tokens = self.count_tokens(input_text)
        output_tokens = self.count_tokens(output_text)
        
        if model not in self.pricing:
            model = 'gpt-4o-mini'  # Default fallback
        
        input_cost = input_tokens * self.pricing[model]['input']
        output_cost = output_tokens * self.pricing[model]['output']
        total_cost = input_cost + output_cost
        
        return input_tokens, output_tokens, total_cost
    
    async def track_usage(self, user_id: str, input_text: str, output_text: str, 
                         message_type: str = 'chat', model: str = 'gpt-4o-mini') -> UsageStats:
        """Track usage and store in database"""
        try:
            input_tokens, output_tokens, cost = self.calculate_cost(input_text, output_text, model)
            
            usage_data = {
                'user_id': user_id,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'cost_usd': cost,
                'message_type': message_type,
                'model': model,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Store in database
            self.supabase.table('budget_tracking').insert(usage_data).execute()
            
            stats = UsageStats(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                message_type=message_type,
                timestamp=datetime.utcnow()
            )
            
            logger.info(f"Tracked usage for {user_id}: ${cost:.4f} ({input_tokens}+{output_tokens} tokens)")
            return stats
            
        except Exception as e:
            logger.error(f"Error tracking usage: {e}")
            # Return zero usage on error
            return UsageStats(0, 0, 0.0, message_type, datetime.utcnow())
    
    async def get_daily_spending(self, user_id: str) -> float:
        """Get today's spending for user"""
        try:
            today = datetime.utcnow().date()
            today_start = datetime.combine(today, datetime.min.time())
            today_end = datetime.combine(today, datetime.max.time())
            
            result = self.supabase.table('budget_tracking')\
                .select('cost_usd')\
                .eq('user_id', user_id)\
                .gte('timestamp', today_start.isoformat())\
                .lte('timestamp', today_end.isoformat())\
                .execute()
            
            return sum(row['cost_usd'] for row in result.data)
            
        except Exception as e:
            logger.error(f"Error getting daily spending: {e}")
            return 0.0
    
    async def get_monthly_spending(self, user_id: str) -> float:
        """Get this month's spending for user"""
        try:
            now = datetime.utcnow()
            month_start = datetime(now.year, now.month, 1)
            
            result = self.supabase.table('budget_tracking')\
                .select('cost_usd')\
                .eq('user_id', user_id)\
                .gte('timestamp', month_start.isoformat())\
                .execute()
            
            return sum(row['cost_usd'] for row in result.data)
            
        except Exception as e:
            logger.error(f"Error getting monthly spending: {e}")
            return 0.0
    
    async def check_budget_status(self, user_id: str) -> Dict[str, any]:
        """Check current budget status and limits"""
        daily_spent = await self.get_daily_spending(user_id)
        monthly_spent = await self.get_monthly_spending(user_id)
        
        daily_remaining = max(0, self.daily_limit - daily_spent)
        monthly_remaining = max(0, self.monthly_limit - monthly_spent)
        
        daily_percentage = (daily_spent / self.daily_limit) * 100 if self.daily_limit > 0 else 0
        monthly_percentage = (monthly_spent / self.monthly_limit) * 100 if self.monthly_limit > 0 else 0
        
        # Determine status
        status = "ok"
        if daily_percentage >= 100 or monthly_percentage >= 100:
            status = "exceeded"
        elif daily_percentage >= (self.warning_threshold * 100) or monthly_percentage >= (self.warning_threshold * 100):
            status = "warning"
        
        return {
            'status': status,
            'daily_spent': daily_spent,
            'daily_limit': self.daily_limit,
            'daily_remaining': daily_remaining,
            'daily_percentage': daily_percentage,
            'monthly_spent': monthly_spent,
            'monthly_limit': self.monthly_limit,
            'monthly_remaining': monthly_remaining,
            'monthly_percentage': monthly_percentage
        }
    
    async def can_make_request(self, user_id: str, estimated_cost: float = 0.01) -> Tuple[bool, str]:
        """Check if user can make a request within budget limits"""
        try:
            budget_status = await self.check_budget_status(user_id)
            
            # Check daily limit
            if budget_status['daily_spent'] + estimated_cost > self.daily_limit:
                return False, f"⛔ Budget quotidien atteint (${budget_status['daily_spent']:.2f}/${self.daily_limit:.2f}). Reset à minuit."
            
            # Check monthly limit
            if budget_status['monthly_spent'] + estimated_cost > self.monthly_limit:
                return False, f"⛔ Budget mensuel atteint (${budget_status['monthly_spent']:.2f}/${self.monthly_limit:.2f}). Reset le 1er du mois."
            
            return True, ""
            
        except Exception as e:
            logger.error(f"Error checking budget: {e}")
            return True, ""  # Allow request on error to avoid blocking
    
    async def get_budget_warning(self, user_id: str) -> Optional[str]:
        """Get budget warning message if needed"""
        try:
            budget_status = await self.check_budget_status(user_id)
            
            # Daily warnings
            if budget_status['daily_percentage'] >= 90:
                return f"🔴 Budget quotidien presque épuisé: ${budget_status['daily_spent']:.2f}/${self.daily_limit:.2f} ({budget_status['daily_percentage']:.0f}%)"
            elif budget_status['daily_percentage'] >= (self.warning_threshold * 100):
                return f"⚠️ Budget quotidien à {budget_status['daily_percentage']:.0f}%: ${budget_status['daily_spent']:.2f}/${self.daily_limit:.2f}"
            
            # Monthly warnings  
            if budget_status['monthly_percentage'] >= 90:
                return f"🔴 Budget mensuel presque épuisé: ${budget_status['monthly_spent']:.2f}/${self.monthly_limit:.2f} ({budget_status['monthly_percentage']:.0f}%)"
            elif budget_status['monthly_percentage'] >= (self.warning_threshold * 100):
                return f"⚠️ Budget mensuel à {budget_status['monthly_percentage']:.0f}%: ${budget_status['monthly_spent']:.2f}/${self.monthly_limit:.2f}"
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting budget warning: {e}")
            return None
    
    async def get_usage_stats(self, user_id: str, days: int = 7) -> Dict[str, any]:
        """Get usage statistics for the last N days"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            result = self.supabase.table('budget_tracking')\
                .select('*')\
                .eq('user_id', user_id)\
                .gte('timestamp', cutoff_date.isoformat())\
                .order('timestamp', desc=True)\
                .execute()
            
            if not result.data:
                return {
                    'total_cost': 0.0,
                    'total_messages': 0,
                    'avg_cost_per_message': 0.0,
                    'total_tokens': 0,
                    'days_analyzed': days
                }
            
            total_cost = sum(row['cost_usd'] for row in result.data)
            total_messages = len(result.data)
            total_tokens = sum(row['input_tokens'] + row['output_tokens'] for row in result.data)
            avg_cost = total_cost / total_messages if total_messages > 0 else 0
            
            return {
                'total_cost': total_cost,
                'total_messages': total_messages,
                'avg_cost_per_message': avg_cost,
                'total_tokens': total_tokens,
                'days_analyzed': days
            }
            
        except Exception as e:
            logger.error(f"Error getting usage stats: {e}")
            return {
                'total_cost': 0.0,
                'total_messages': 0,
                'avg_cost_per_message': 0.0,
                'total_tokens': 0,
                'days_analyzed': days
            }
    
    def format_budget_status(self, budget_status: Dict) -> str:
        """Format budget status for display"""
        daily_bar = self._create_progress_bar(budget_status['daily_percentage'])
        monthly_bar = self._create_progress_bar(budget_status['monthly_percentage'])
        
        return f"""💰 **BUDGET STATUS**

**Aujourd'hui:** ${budget_status['daily_spent']:.2f} / ${budget_status['daily_limit']:.2f}
{daily_bar} {budget_status['daily_percentage']:.0f}%

**Ce mois:** ${budget_status['monthly_spent']:.2f} / ${budget_status['monthly_limit']:.2f}  
{monthly_bar} {budget_status['monthly_percentage']:.0f}%

**Restant aujourd'hui:** ${budget_status['daily_remaining']:.2f}"""
    
    def _create_progress_bar(self, percentage: float, length: int = 10) -> str:
        """Create a text progress bar"""
        filled = int(percentage / 10)
        empty = length - filled
        
        if percentage >= 90:
            return "🔴" + "█" * filled + "░" * empty
        elif percentage >= 75:
            return "🟡" + "█" * filled + "░" * empty
        else:
            return "🟢" + "█" * filled + "░" * empty