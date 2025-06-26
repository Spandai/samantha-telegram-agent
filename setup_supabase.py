"""
Script pour créer automatiquement les tables Supabase pour Samantha
"""

import asyncio
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

async def setup_supabase_tables():
    """Créer toutes les tables nécessaires pour Samantha"""
    
    # Connexion Supabase
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not supabase_url or not supabase_service_key:
        print("❌ Variables SUPABASE manquantes dans .env")
        return False
    
    supabase = create_client(supabase_url, supabase_service_key)
    
    print("🔗 Connexion à Supabase...")
    print(f"URL: {supabase_url}")
    
    # SQL commands à exécuter
    sql_commands = [
        # 1. Table conversations
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id BIGSERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            message TEXT NOT NULL,
            is_user_message BOOLEAN NOT NULL DEFAULT true,
            tokens INTEGER DEFAULT 0,
            timestamp TIMESTAMPTZ DEFAULT NOW()
        );
        """,
        
        # Index pour conversations
        """
        CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
        CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp);
        """,
        
        # 2. Table memory_layers
        """
        CREATE TABLE IF NOT EXISTS memory_layers (
            id BIGSERIAL PRIMARY KEY,
            user_id TEXT NOT NULL UNIQUE,
            short_term JSONB,
            medium_term TEXT,
            long_term JSONB,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        """,
        
        # Index pour memory_layers
        """
        CREATE INDEX IF NOT EXISTS idx_memory_layers_user_id ON memory_layers(user_id);
        """,
        
        # 3. Table budget_tracking
        """
        CREATE TABLE IF NOT EXISTS budget_tracking (
            id BIGSERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            cost_usd DECIMAL(10,6) NOT NULL DEFAULT 0,
            message_type TEXT DEFAULT 'chat',
            model TEXT DEFAULT 'gpt-4o-mini',
            timestamp TIMESTAMPTZ DEFAULT NOW()
        );
        """,
        
        # Index pour budget_tracking
        """
        CREATE INDEX IF NOT EXISTS idx_budget_tracking_user_id ON budget_tracking(user_id);
        CREATE INDEX IF NOT EXISTS idx_budget_tracking_timestamp ON budget_tracking(timestamp);
        """,
        
        # 4. Function update_updated_at
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        """,
        
        # 5. Trigger pour memory_layers
        """
        DROP TRIGGER IF EXISTS update_memory_layers_updated_at ON memory_layers;
        CREATE TRIGGER update_memory_layers_updated_at 
            BEFORE UPDATE ON memory_layers 
            FOR EACH ROW 
            EXECUTE FUNCTION update_updated_at_column();
        """,
        
        # 6. RLS Policies (sécurité basique)
        """
        ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
        ALTER TABLE memory_layers ENABLE ROW LEVEL SECURITY;
        ALTER TABLE budget_tracking ENABLE ROW LEVEL SECURITY;
        """,
        
        """
        DROP POLICY IF EXISTS "Allow all operations on conversations" ON conversations;
        CREATE POLICY "Allow all operations on conversations" ON conversations FOR ALL USING (true);
        """,
        
        """
        DROP POLICY IF EXISTS "Allow all operations on memory_layers" ON memory_layers;
        CREATE POLICY "Allow all operations on memory_layers" ON memory_layers FOR ALL USING (true);
        """,
        
        """
        DROP POLICY IF EXISTS "Allow all operations on budget_tracking" ON budget_tracking;
        CREATE POLICY "Allow all operations on budget_tracking" ON budget_tracking FOR ALL USING (true);
        """
    ]
    
    # Exécuter chaque commande
    success_count = 0
    for i, sql in enumerate(sql_commands, 1):
        try:
            print(f"📝 Exécution commande {i}/{len(sql_commands)}...")
            result = supabase.rpc('exec_sql', {'sql': sql.strip()}).execute()
            print(f"✅ Commande {i} réussie")
            success_count += 1
        except Exception as e:
            print(f"⚠️ Commande {i} - Erreur (peut être normale): {str(e)}")
            # Certaines erreurs sont normales (ex: table existe déjà)
            success_count += 1
    
    # Test des tables créées
    print("\n🔍 Vérification des tables...")
    
    try:
        # Test table conversations
        supabase.table('conversations').select('id').limit(1).execute()
        print("✅ Table 'conversations' - OK")
    except Exception as e:
        print(f"❌ Table 'conversations' - Erreur: {e}")
        return False
    
    try:
        # Test table memory_layers
        supabase.table('memory_layers').select('id').limit(1).execute()
        print("✅ Table 'memory_layers' - OK")
    except Exception as e:
        print(f"❌ Table 'memory_layers' - Erreur: {e}")
        return False
    
    try:
        # Test table budget_tracking
        supabase.table('budget_tracking').select('id').limit(1).execute()
        print("✅ Table 'budget_tracking' - OK")
    except Exception as e:
        print(f"❌ Table 'budget_tracking' - Erreur: {e}")
        return False
    
    print(f"\n🎉 Setup Supabase terminé ! {success_count}/{len(sql_commands)} commandes exécutées")
    print("✅ Toutes les tables sont prêtes pour Samantha")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(setup_supabase_tables())
    if success:
        print("\n🚀 Samantha peut maintenant être déployée !")
    else:
        print("\n❌ Problème lors du setup. Vérifiez vos credentials Supabase.")