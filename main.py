import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timezone

# --- CONFIG & DESIGN ---
st.set_page_config(page_title="PolyScanner V3", page_icon="💀", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #E0E0E0; }
    .metric-card { background-color: #21262D; padding: 15px; border-radius: 10px; border: 1px solid #30363D; }
    .stButton > button { background: #2E75FF; color: white; border: none; width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- FONCTION DE RÉCUPERATION ROBUSTE ---
def fetch_data_stealth(min_reward, max_days):
    # Endpoint principal
    url = "https://gamma-api.polymarket.com/markets"
    
    # 1. Paramètres de requête
    params = {
        "active": "true",
        "closed": "false",
        "limit": 500,
        "order": "volume24hr",
        "ascending": "false"
    }

    # 2. HEADERS CRUCIAUX (Pour ne pas être détecté comme un bot Railway)
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://polymarket.com/",
        "Origin": "https://polymarket.com"
    }

    try:
        # On lance la requête
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        # SI ERREUR HTTP (403, 404, 500)
        if response.status_code != 200:
            st.error(f"❌ BLOCAGE API DETECTÉ. Code: {response.status_code}")
            st.error(f"Message serveur: {response.text[:200]}")
            return pd.DataFrame()

        data = response.json()
        markets = data if isinstance(data, list) else data.get('data', [])
        
        # Analyse des opportunités
        opportunities = []
        now = datetime.now(timezone.utc)

        for m in markets:
            # Filtre Date
            if not m.get('endDate'): continue
            try:
                end_date = datetime.fromisoformat(m['endDate'].replace('Z', '+00:00'))
                days_remaining = (end_date - now).days
                if days_remaining > max_days or days_remaining < 0: continue
            except: continue

            # Récupération Rewards (Méthode souple)
            rewards = m.get('rewards', {})
            daily_reward = 0
            
            # On cherche n'importe quelle valeur numérique dans rewards
            if isinstance(rewards, dict) and 'rates' in rewards:
                for rate in rewards['rates']:
                    amt = float(rate.get('asset_amount', 0))
                    daily_reward += amt
            
            # Filtre Reward Min
            if daily_reward < min_reward: continue

            # Données
            liq = float(m.get('liquidity', 0) or 0)
            price = float(m.get('lastTradePrice', 0.5))
            
            opportunities.append({
                "Question": m.get('question'),
                "Reward ($)": round(daily_reward, 2),
                "Liquidité": round(liq, 0),
                "Prix": price,
                "Score": round((daily_reward / (liq+1))*1000, 2),
                "slug": f"https://polymarket.com/event/{m.get('slug')}"
            })

        return pd.DataFrame(opportunities)

    except Exception as e:
        st.error(f"❌ Erreur Python: {str(e)}")
        return pd.DataFrame()

# --- UI ---
with st.sidebar:
    st.header("⚙️ Scanner V3")
    reward_input = st.slider("Reward Min ($)", 0, 50, 0) # Par défaut 0 pour tester
    days_input = st.slider("Jours Max", 1, 60, 30)
    
    if st.button("LANCER LE SCAN"):
        st.session_state['run'] = True

st.title("💀 PolyScanner V3 (Mode Stealth)")

# Auto-run ou bouton
if st.session_state.get('run', False):
    with st.spinner("Infiltration de l'API en cours..."):
        df = fetch_data_stealth(reward_input, days_input)

    if not df.empty:
        st.success(f"✅ {len(df)} Marchés trouvés !")
        
        # Affichage simple et robuste
        st.dataframe(
            df.sort_values(by="Score", ascending=False),
            column_config={
                "slug": st.column_config.LinkColumn("Lien"),
                "Score": st.column_config.ProgressColumn("Rentabilité", max_value=df['Score'].max())
            },
            use_container_width=True
        )
    else:
        st.warning("Aucune donnée retournée (liste vide).")
        st.info("Conseil : Laisse 'Reward Min' à 0 pour vérifier la connexion.")
