import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timezone

# --- CONFIGURATION (CSS & PAGE) ---
st.set_page_config(page_title="PolyScanner 2025", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #E0E0E0; }
    /* On retire le CSS custom des boutons car on utilise maintenant width='stretch' */
</style>
""", unsafe_allow_html=True)

# --- FONCTION API ---
def fetch_data_debug(min_reward, max_days):
    url = "https://gamma-api.polymarket.com/markets"
    
    # Paramètres élargis pour être sûr de capter quelque chose
    params = {
        "active": "true",
        "closed": "false",
        "limit": 100, # On réduit à 100 pour aller vite
        "order": "volume24hr",
        "ascending": "false"
    }

    # Headers pour simuler un vrai navigateur (Anti-Bot)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        # DEBUG : Si l'API bloque (403/429) ou plante (500)
        if response.status_code != 200:
            return pd.DataFrame(), f"ERREUR HTTP {response.status_code}", response.text

        data = response.json()
        
        # DEBUG : Si l'API renvoie un truc vide ou bizarre
        if not data:
            return pd.DataFrame(), "JSON VIDE", "L'API a renvoyé une réponse vide."

        # Gestion de la structure (liste ou dictionnaire)
        markets = data if isinstance(data, list) else data.get('data', [])
        
        if not markets:
             return pd.DataFrame(), "LISTE VIDE", str(data)

        # Si on a des marchés, on traite
        opportunities = []
        now = datetime.now(timezone.utc)

        for m in markets:
            # Filtre Date simple
            if m.get('endDate'):
                try:
                    end_date = datetime.fromisoformat(m['endDate'].replace('Z', '+00:00'))
                    days_remaining = (end_date - now).days
                    if days_remaining > max_days or days_remaining < 0: continue
                except: pass

            # Récupération Rewards (Check large)
            rewards = m.get('rewards', {})
            daily_reward = 0
            
            # On additionne tout ce qui ressemble à un chiffre dans rewards
            if isinstance(rewards, dict) and 'rates' in rewards:
                for rate in rewards['rates']:
                    daily_reward += float(rate.get('asset_amount', 0))
            
            # Filtre Reward Strict
            if daily_reward < min_reward: continue

            # Données finales
            liq = float(m.get('liquidity', 0) or 0)
            
            opportunities.append({
                "Question": m.get('question'),
                "Reward": round(daily_reward, 2),
                "Liquidité": round(liq, 0),
                "Score": round((daily_reward / (liq+1))*1000, 2),
                "Lien": f"https://polymarket.com/event/{m.get('slug')}"
            })

        return pd.DataFrame(opportunities), "OK", "Succès"

    except Exception as e:
        return pd.DataFrame(), "CRASH PYTHON", str(e)

# --- INTERFACE ---
with st.sidebar:
    st.header("Paramètres")
    # Valeurs par défaut très basses pour tester la connexion
    reward_input = st.slider("Reward Min ($)", 0, 50, 0)
    days_input = st.slider("Jours Max", 1, 60, 30)
    
    # Utilisation de la nouvelle syntaxe width='stretch' pour les boutons
    if st.button("LANCER LE SCAN", width='stretch'):
        st.session_state['run'] = True

st.title("⚡ PolyScanner V4 (Debug)")

if st.session_state.get('run', False):
    with st.spinner("Analyse en cours..."):
        df, status, debug_msg = fetch_data_debug(reward_input, days_input)

    if not df.empty:
        st.success(f"✅ {len(df)} opportunités trouvées !")
        
        # Nouvelle syntaxe width='stretch'
        st.dataframe(
            df.sort_values(by="Score", ascending=False),
            column_config={
                "Lien": st.column_config.LinkColumn("Lien"),
                "Score": st.column_config.ProgressColumn("Score", max_value=df['Score'].max())
            },
            width='stretch' 
        )
    else:
        st.error(f"❌ AUCUN RÉSULTAT - DIAGNOSTIC : {status}")
        st.warning("Voici ce que l'API a renvoyé (copie-colle ça à l'IA) :")
        # On affiche la réponse brute pour comprendre pourquoi c'est vide
        st.code(debug_msg[0:1000], language="json")
