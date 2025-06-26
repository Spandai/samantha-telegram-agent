# 🤖 Samantha - AI Telegram Agent

**Samantha** est votre assistante IA avec un style startup : no bullshit, full efficiency.

## ✨ Fonctionnalités

- 🧠 **Mémoire intelligente** (court, moyen, long terme)
- 🔍 **Recherche web** gratuite (DuckDuckGo)
- 💰 **Gestion budget** automatique
- 🎯 **Adaptation continue** du comportement
- ⚡ **Interface 100% Telegram**

## 🚀 Setup Rapide (5 minutes)

### 1. Clone et Installation
```bash
git clone <your-repo>
cd TelegramAgent
pip install -r requirements.txt
```

### 2. Configuration Supabase
1. Allez dans votre projet Supabase
2. SQL Editor → Collez le contenu de `create_tables.sql` → Run
3. Vérifiez que les 3 tables sont créées

### 3. Variables d'Environnement
Copiez `.env.example` vers `.env` et remplissez vos valeurs :
```bash
cp .env.example .env
nano .env  # ou votre éditeur préféré
```

### 4. Test Local
```bash
python telegram_bot.py
```

### 5. Déploiement Render
1. Push sur GitHub
2. Connectez Render à votre repo
3. Variables d'environnement dans Render dashboard
4. Deploy automatique !

## 💬 Commandes Telegram

### Commands Principales
- **Message normal** → Conversation intelligente avec mémoire
- `/search [requête]` → Force recherche web
- `/prompt [nouveau]` → Change le comportement
- `/budget` → Vérifier coûts et limites
- `/memory add [info]` → Ajoute en mémoire long terme

### Commands d'Administration
- `/stats` → Statistiques d'utilisation
- `/reset` → Remet à zéro la conversation
- `/help` → Liste complète des commandes

## 💰 Gestion Budget

### Limites par Défaut
- **Quotidien :** $1.50 (~45€/mois)
- **Mensuel :** $40.00 (sécurité)
- **Alerte :** 75% du budget

### Coûts Réels
- Message court : ~$0.0003
- Message + recherche : ~$0.0008  
- Conversation normale : ~$1/jour

## 🧠 Système de Mémoire

### Court Terme (50 messages)
Buffer des derniers messages pour contexte immédiat

### Moyen Terme (résumé hebdomadaire)
Résumé automatique des conversations importantes

### Long Terme (profil utilisateur)
- Préférences personnelles
- Style de communication
- Informations importantes
- Prompt personnalisé

## ⚙️ Architecture

```
telegram_bot.py         # Interface Telegram
├── agent.py           # Agent principal (Pydantic AI)
├── memory_manager.py  # Système mémoire 3 niveaux
├── search_tools.py    # Recherche DuckDuckGo
├── budget_tracker.py  # Tracking coûts OpenAI
└── agent_prompts.py   # Prompts dynamiques
```

## 🔧 Configuration Avancée

### Personnalisation Budget
```env
DAILY_BUDGET_USD=2.00      # Budget quotidien
MONTHLY_BUDGET_USD=50.00   # Budget mensuel
WARNING_THRESHOLD=0.80     # Alerte à 80%
```

### Style de l'Agent
```env
AGENT_NAME=Samantha
DEFAULT_TONE=startup style no bullshit full efficiency
PRIMARY_LANGUAGE=français
```

### Optimisations Performance
```env
MAX_MEMORY_MESSAGES=50     # Messages en mémoire court terme
RATE_LIMIT_PER_HOUR=30    # (Non utilisé, remplacé par budget)
DEBUG_MODE=false          # Mode debug
```

## 📊 Monitoring

### Métriques Automatiques
- Coût par message
- Utilisation token
- Performance mémoire
- Alertes budget

### Logs
```bash
# Logs en temps réel
tail -f logs/samantha.log

# Render logs
render logs --service=your-service-name
```

## 🛠️ Développement

### Tests Locaux
```bash
# Test agent seul
python -c "import asyncio; from agent import *; asyncio.run(test_agent())"

# Test recherche
python -c "import asyncio; from search_tools import *; asyncio.run(search_manager.smart_search('test'))"

# Test mémoire
python -c "import asyncio; from memory_manager import *; asyncio.run(test_memory())"
```

### Débogage
```bash
export DEBUG_MODE=true
export LOG_LEVEL=DEBUG
python telegram_bot.py
```

## 🚀 Déploiement Production

### Render (Recommandé)
1. **GitHub :** Push code
2. **Render :** New Web Service → Connect repo
3. **Build :** `pip install -r requirements.txt`
4. **Start :** `python telegram_bot.py`
5. **Variables :** Coller vos `.env` values

### Variables Render Requises
```
TELEGRAM_BOT_TOKEN=your_token
OPENAI_API_KEY=your_key  
SUPABASE_URL=your_url
SUPABASE_ANON_KEY=your_key
SUPABASE_SERVICE_KEY=your_key
DAILY_BUDGET_USD=1.50
MONTHLY_BUDGET_USD=40.00
```

## 📈 Optimisations

### Réduction Coûts
- Cache intelligent (résultats similaires)
- Compression mémoire (résumés)
- DuckDuckGo gratuit (vs APIs payantes)
- Budget strict (protection)

### Performance
- Async/await partout
- Supabase optimisé (indexes)
- Rate limiting intelligent
- Mémoire progressive

## 🔐 Sécurité

### Données Utilisateur
- Row Level Security (Supabase)
- Pas de logs des messages
- Clés API chiffrées (Render)
- Rate limiting anti-spam

### Budget Protection
- Limites strictes par user
- Alertes automatiques
- Stop d'urgence si dépassement
- Monitoring en temps réel

## 🆘 Dépannage

### Erreurs Communes
```bash
# Bot ne répond pas
→ Vérifier TELEGRAM_BOT_TOKEN

# Pas de recherche web  
→ Vérifier connexion internet

# Erreur Supabase
→ Vérifier URL + clés

# Budget bloqué
→ /budget reset ou attendre minuit
```

### Support
- Logs dans Render dashboard
- Test avec `/stats` commande
- Check Supabase table data
- Restart service si nécessaire

## 📝 Changelog

### v1.0 (Initial)
- ✅ Agent Pydantic AI complet
- ✅ Mémoire 3 niveaux  
- ✅ Recherche DuckDuckGo
- ✅ Budget tracking USD
- ✅ Interface Telegram native
- ✅ Déploiement Render

---

**Samantha est prête ! 🎉**

Budget optimisé, mémoire intelligente, recherche illimitée.
Coût réel : ~$6-20/mois selon usage.