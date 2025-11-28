import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timezone

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="PolyScanner Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- DESIGN SYSTEM (CSS 2025) ---
st.markdown("""
<style>
    /* Fond global sombre et profond */
    .stApp {
        background-color: #0E1117;
        color: #E0E0E0;
    }
    
    /* Sidebar propre */
    section[data-testid="stSidebar"] {
        background-color: #161B22;
        border-right: 1px solid #30363D;
    }

    /* Titres */
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        color: #FFFFFF;
        letter-spacing: -0.5px;
    }
    
    /* Metrics Cards (KPIs) */
    div[data-testid="metric-container"] {
        background-color: #21262D;
        border: 1px solid #30363D;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s;
    }
    div[data-testid="metric-container"]:hover {
        border-color: #2E75FF; /* Polymarket Blue */
    }

    /* Boutons stylisés */
    .stButton > button {
        background: linear-gradient(90deg, #2E75FF 0%, #00D4FF 100%);
        color: white;
        font-weight: 600;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        box-shadow: 0 0 15px rgba(46, 117, 255, 0.5);
        transform: translateY(-2px);
    }

    /* Tableaux de données */
    div[data-testid="stDataFrame"] {
        border: 1px solid #30363D;
        border-radius: 10px;
        overflow: hidden;
    }

    /* Liens */
    a {
        color: #58A6FF !important;
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
    }
</style>
""", unsafe_allow_html=True)

# --- LOGIQUE BACKEND ---

@st.cache_data(ttl=300) # Cache de 5 min pour éviter de spammer l'API
def fetch_opportunities(min_reward, max_days, min_liquidity):
    GAMMA_API = "https://gamma-api.polymarket.com/markets"
    params = {
        "active": "true",
        "closed": "false",
        "limit": 1000, 
        "order": "volume24hr", 
        "ascending": "false"
    }
    
    try:
        response = requests.get(GAMMA_API, params=params)
        markets = response.json()
        if isinstance(markets, dict): markets = markets.get('data', [])
        
        opportunities = []
        now = datetime.now(timezone.utc)

        for m in markets:
            # 1. Filtre Date
            if not m.get('endDate'): continue
            try:
                end_date = datetime.fromisoformat(m['endDate'].replace('Z', '+00:00'))
                days_remaining = (end_date - now).days
                if days_remaining > max_days or days_remaining < 0: continue
            except: continue

            # 2. Filtre Rewards
            rewards = m.get('rewards', {})
            daily_reward = 0
            if rewards and isinstance(rewards, dict) and rewards.get('rates'):
                for rate in rewards['rates']:
                    daily_reward += float(rate.get('asset_amount', 0))
            
            if daily_reward < min_reward: continue

            # 3. Filtre Liquidité
            liquidity = float(m.get('liquidity', 0) or 0)
            if liquidity < min_liquidity: continue

            # 4. Calculs Trading
            last_price = float(m.get('lastTradePrice', 0.5))
            target_buy = last_price - 0.035 # Un peu plus agressif que 0.03
            
            # Score de compétition (Reward / Liquidité)
            # Plus il y a de reward par dollar de liquidité, mieux c'est.
            comp_score = (daily_reward / liquidity) * 1000 

            opportunities.append({
                "Question": m.get('question'),
                "Jours restants": days_remaining,
                "Daily Reward ($)": round(daily_reward, 2),
                "Liquidité ($)": round(liquidity, 0),
                "Prix Actuel": round(last_price, 2),
                "Cible Achat (Bid)": round(target_buy, 2),
                "Score": round(comp_score, 2),
                "slug": m.get('slug')
            })

        return pd.DataFrame(opportunities)

    except Exception as e:
        st.error(f"Erreur API: {e}")
        return pd.DataFrame()

# --- INTERFACE ---

st.title("⚡ PolyScanner Pro")
st.markdown("*L'outil de détection de liquidité pour Polymarket - Édition 2025*")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ Paramètres de Scan")
    
    min_reward_input = st.slider("Reward Min. Journalier ($)", 10, 200, 30)
    max_days_input = st.slider("Durée Max (Jours)", 1, 30, 7)
    min_liquidity_input = st.number_input("Liquidité Min ($)", value=2000, step=500)
    
    st.markdown("---")
    st.info("""
    **Stratégie :**
    1. Placer un ordre LIMIT à la **Cible Achat**.
    2. Vérifier que le cercle devient **BLEU** sur Polymarket.
    3. Attendre l'exécution ou collecter les rewards.
    """)
    
    if st.button("Lancer le Scan 🚀", use_container_width=True):
        st.session_state['refresh'] = True

# Main Logic
df = fetch_opportunities(min_reward_input, max_days_input, min_liquidity_input)

if not df.empty:
    # Top metrics
    top_opp = df.sort_values(by="Score", ascending=False).iloc[0]
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Opportunités Trouvées", len(df))
    c2.metric("Meilleur Daily Reward", f"${df['Daily Reward ($)'].max()}")
    c3.metric("Marché Top Score", f"{top_opp['Score']}")
    c4.metric("Liquidité Totale Scannée", f"${df['Liquidité ($)'].sum():,.0f}")

    st.markdown("### 🏆 Top Opportunités (Classées par Score de Rentabilité)")
    
    # Configuration de l'affichage du tableau
    # On ajoute une colonne lien cliquable
    df_display = df.sort_values(by="Score", ascending=False).copy()
    
    # On rend le tableau interactif
    st.dataframe(
        df_display,
        column_config={
            "Question": st.column_config.TextColumn("Marché", width="medium"),
            "slug": st.column_config.LinkColumn(
                "Lien",
                display_text="Ouvrir ↗",
                help="Aller sur Polymarket"
            ),
            "Score": st.column_config.ProgressColumn(
                "Rentabilité",
                format="%.1f",
                min_value=0,
                max_value=df_display['Score'].max(),
            ),
             "Daily Reward ($)": st.column_config.NumberColumn(
                "Reward/J",
                format="$%.2f"
            )
        },
        hide_index=True,
        use_container_width=True,
        height=600
    )
    
    # Astuce pour générer les liens corrects dans la dataframe
    # Streamlit ne gère pas nativement les liens dynamiques complexes dans un dataframe simple
    # sauf via LinkColumn qui attend une URL complète.
    # On modifie la colonne slug pour qu'elle soit une URL complète.
    df_display['slug'] = "https://polymarket.com/event/" + df_display['slug']
    
else:
    st.warning("Aucun marché ne correspond à tes critères stricts. Essaie d'élargir la recherche (plus de jours, moins de rewards).")