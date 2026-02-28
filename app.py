import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import html as html_lib
from datetime import datetime
from agent import configurer_gemini, chat_avec_agent, chat_employe
from data import (EMPLOYES, PLANNING_SEMAINE, ABSENCES,
                  ALERTES, METRIQUES, PHARMACIE)
from store import load_store, reset_store, get_notifications, mark_notifications_read
from Rulesengine import run_full_compliance_check
from pdf_export import export_planning_pdf, export_conformite_pdf

st.set_page_config(
    page_title="PharmAssist RH",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# THEME STATE
# ─────────────────────────────────────────────
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

def switch_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"

IS_DARK = st.session_state.theme == "dark"

# ─────────────────────────────────────────────
# PALETTE
# ─────────────────────────────────────────────
if IS_DARK:
    BG         = "#07100e"
    BG2        = "#0b1a16"
    BG3        = "#0f211c"
    CARD       = "#0c1e19"
    CARD2      = "#102319"
    BORDER     = "rgba(52,211,153,0.14)"
    BORDER2    = "rgba(52,211,153,0.38)"
    TEXT       = "#e8f0ed"
    TEXT2      = "#7db59a"
    MUTED      = "#3a6654"
    ACCENT     = "#34d399"
    ACCENT2    = "#6ee7b7"
    ACCENT_BG  = "rgba(52,211,153,0.10)"
    BLUE       = "#38bdf8"
    GREEN      = "#34d399"
    ORANGE     = "#fbbf24"
    RED        = "#f87171"
    SIDEBAR    = "#060f0c"
    SHADOW     = "0 8px 30px rgba(0,0,0,0.55)"
    PLOT_FONT  = "#7db59a"
else:
    BG         = "#f4faf7"
    BG2        = "#eaf5ef"
    BG3        = "#dff0e8"
    CARD       = "#ffffff"
    CARD2      = "#f8fdfb"
    BORDER     = "rgba(16,148,88,0.18)"
    BORDER2    = "rgba(16,148,88,0.45)"
    TEXT       = "#0a1f17"
    TEXT2      = "#2d6e52"
    MUTED      = "#7db59a"
    ACCENT     = "#059669"
    ACCENT2    = "#10b981"
    ACCENT_BG  = "rgba(16,148,88,0.07)"
    BLUE       = "#0284c7"
    GREEN      = "#059669"
    ORANGE     = "#d97706"
    RED        = "#dc2626"
    SIDEBAR    = "#ebf5ef"
    SHADOW     = "0 4px 20px rgba(5,150,105,0.09)"
    PLOT_FONT  = "#2d6e52"

# ─────────────────────────────────────────────
# CSS GLOBAL
# ─────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=Nunito:wght@300;400;500;600;700&display=swap');

* {{ box-sizing: border-box; }}
html, body, [class*="css"] {{
  font-family: 'Nunito', sans-serif;
  background: {BG}; color: {TEXT};
}}
.stApp {{ background: {BG}; }}

[data-testid="stSidebar"] {{
  background: {SIDEBAR} !important;
  border-right: 1px solid {BORDER};
}}

.logo-wrap {{
  text-align: center;
  padding: 26px 12px 20px;
  border-bottom: 1px solid {BORDER};
  margin-bottom: 18px;
}}
.logo-cross {{
  font-size: 2.6rem; display: block; margin-bottom: 8px;
  filter: drop-shadow(0 0 12px {ACCENT}88);
}}
.logo-name {{
  font-family: 'Cormorant Garamond', serif;
  font-size: 1.65rem; font-weight: 700; color: {TEXT}; letter-spacing: 0.5px;
}}
.logo-sub {{
  font-size: 0.67rem; color: {MUTED};
  text-transform: uppercase; letter-spacing: 2.5px; font-weight: 600; margin-top: 3px;
}}

.status-on {{
  background: {ACCENT_BG}; border: 1px solid {BORDER2};
  border-radius: 10px; padding: 11px 14px; text-align: center; margin-bottom: 14px;
}}
.status-off {{
  background: rgba(248,113,113,0.07); border: 1px solid rgba(248,113,113,0.28);
  border-radius: 10px; padding: 11px 14px; text-align: center; margin-bottom: 14px;
}}
.dot-on  {{ color: {GREEN}; font-weight: 700; font-size: 0.84rem; }}
.dot-off {{ color: {RED};   font-weight: 700; font-size: 0.84rem; }}
.dot-sub {{ color: {MUTED}; font-size: 0.72rem; margin-top: 3px; }}

.page-header {{
  background: linear-gradient(135deg, {CARD} 0%, {CARD2} 100%);
  border: 1px solid {BORDER}; border-top: 3px solid {ACCENT};
  border-radius: 18px; padding: 32px 40px 28px;
  margin-bottom: 26px; position: relative; overflow: hidden;
  box-shadow: {SHADOW};
}}
.page-header::after {{
  content: '✚'; position: absolute; top: 10px; right: 32px;
  font-size: 7rem; font-weight: 900; color: {BORDER}; line-height: 1;
  user-select: none; pointer-events: none;
  font-family: 'Cormorant Garamond', serif;
}}
.ph-eyebrow {{
  font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: 2.5px; color: {ACCENT}; margin-bottom: 10px;
}}
.ph-title {{
  font-family: 'Cormorant Garamond', serif;
  font-size: 2.3rem; font-weight: 700; color: {TEXT};
  line-height: 1.1; margin-bottom: 8px;
}}
.ph-sub {{ color: {TEXT2}; font-size: 0.9rem; font-weight: 400; }}

.metric-card {{
  background: linear-gradient(135deg, {CARD} 0%, {CARD2} 100%);
  border: 1px solid {BORDER}; border-radius: 14px;
  padding: 22px 24px; text-align: center; height: 130px;
  display: flex; flex-direction: column; justify-content: center;
  box-shadow: {SHADOW};
}}
.metric-value {{
  font-family: 'Cormorant Garamond', serif;
  font-size: 2.5rem; color: {ACCENT}; line-height: 1; margin-bottom: 6px;
}}
.metric-value.green {{ color: {GREEN}; }}
.metric-value.orange {{ color: {ORANGE}; }}
.metric-value.red {{ color: {RED}; }}
.metric-label {{
  font-size: 0.72rem; color: {MUTED};
  text-transform: uppercase; letter-spacing: 1px; font-weight: 700;
}}

.section-title {{
  font-family: 'Cormorant Garamond', serif;
  font-size: 1.3rem; font-weight: 600; color: {TEXT}; margin: 0 0 16px 0;
}}

.stTabs [data-baseweb="tab-list"] {{
  background: transparent !important;
  border-bottom: 2px solid {BORDER} !important;
}}
.stTabs [data-baseweb="tab"] {{
  background: transparent !important; color: {MUTED} !important;
  font-family: 'Nunito', sans-serif !important;
  font-size: 0.84rem !important; font-weight: 600 !important;
  padding: 10px 18px !important; border-radius: 0 !important;
  border-bottom: 2px solid transparent !important; margin-bottom: -2px !important;
}}
.stTabs [aria-selected="true"] {{
  background: {ACCENT_BG} !important; color: {ACCENT} !important;
  border-bottom: 2px solid {ACCENT} !important;
}}

.chat-container {{
  background: {CARD}; border: 1px solid {BORDER}; border-radius: 16px; padding: 20px;
  min-height: 420px; max-height: 520px; overflow-y: auto; margin-bottom: 14px;
  box-shadow: {SHADOW};
}}
.chat-empty {{
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; height: 360px; text-align: center; color: {MUTED};
}}
.chat-empty-icon {{
  width: 66px; height: 66px; background: {ACCENT_BG}; border: 1px solid {BORDER2};
  border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-size: 1.9rem; margin: 0 auto 14px;
}}

.message-label-user {{
  font-size: 0.67rem; color: {BLUE}; font-weight: 700;
  text-transform: uppercase; letter-spacing: 1.6px; margin-bottom: 5px;
}}
.message-label-agent {{
  font-size: 0.67rem; color: {ACCENT}; font-weight: 700;
  text-transform: uppercase; letter-spacing: 1.6px; margin-bottom: 5px;
}}
.message-user {{
  background: linear-gradient(135deg, rgba(56,189,248,0.1), rgba(56,189,248,0.05));
  border: 1px solid rgba(56,189,248,0.22); border-radius: 16px 16px 4px 16px;
  padding: 13px 17px; margin: 8px 0 8px 52px; font-size: 0.91rem; line-height: 1.65; color: {TEXT};
}}
.message-agent {{
  background: linear-gradient(135deg, {ACCENT_BG}, rgba(52,211,153,0.04));
  border: 1px solid {BORDER}; border-radius: 16px 16px 16px 4px;
  padding: 13px 17px; margin: 8px 52px 8px 0; font-size: 0.91rem; line-height: 1.75; color: {TEXT};
}}
.tool-tag {{
  display: inline-block; background: {ACCENT_BG}; border: 1px solid {BORDER2};
  border-radius: 6px; padding: 4px 11px; margin: 3px 0;
  font-size: 0.74rem; color: {ACCENT2}; font-weight: 600;
}}

.stButton > button {{
  background: {CARD2} !important; border: 1px solid {BORDER} !important;
  color: {TEXT} !important; border-radius: 10px !important;
  font-family: 'Nunito', sans-serif !important;
  font-size: 0.82rem !important; font-weight: 600 !important;
  text-align: left !important; transition: all 0.16s !important;
}}
.stButton > button:hover {{
  background: {ACCENT_BG} !important; border-color: {BORDER2} !important;
  color: {ACCENT} !important; transform: translateX(3px) !important;
}}

[data-testid="stFormSubmitButton"] > button {{
  background: linear-gradient(135deg, {ACCENT}, {ACCENT2}) !important;
  border: none !important; color: #fff !important; border-radius: 10px !important;
  font-weight: 700 !important; font-family: 'Nunito', sans-serif !important;
  box-shadow: 0 4px 14px rgba(52,211,153,0.3) !important; transition: all 0.18s !important;
}}
[data-testid="stFormSubmitButton"] > button:hover {{
  transform: translateY(-1px) !important;
  box-shadow: 0 6px 22px rgba(52,211,153,0.45) !important;
}}

.stTextInput > div > div > input {{
  background: {CARD} !important; border: 1px solid {BORDER} !important;
  border-radius: 10px !important; color: {TEXT} !important;
  font-family: 'Nunito', sans-serif !important; font-size: 0.9rem !important;
}}
.stTextInput > div > div > input:focus {{
  border-color: {ACCENT} !important; box-shadow: 0 0 0 3px {ACCENT_BG} !important;
}}
.stSelectbox > div > div {{
  background: {CARD} !important; border: 1px solid {BORDER} !important;
  border-radius: 10px !important; color: {TEXT} !important;
}}

.alerte-rouge {{
  background: rgba(248,113,113,0.07); border: 1px solid rgba(248,113,113,0.3);
  border-left: 4px solid {RED}; border-radius: 10px; padding: 14px 18px; margin-bottom: 10px;
}}
.alerte-orange {{
  background: rgba(251,191,36,0.07); border: 1px solid rgba(251,191,36,0.3);
  border-left: 4px solid {ORANGE}; border-radius: 10px; padding: 14px 18px; margin-bottom: 10px;
}}
.alerte-vert {{
  background: rgba(52,211,153,0.07); border: 1px solid {BORDER};
  border-left: 4px solid {GREEN}; border-radius: 10px; padding: 14px 18px; margin-bottom: 10px;
}}
.alerte-title {{
  font-weight: 700; font-size: 0.78rem;
  text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;
}}
.alerte-rouge  .alerte-title {{ color: {RED}; }}
.alerte-orange .alerte-title {{ color: {ORANGE}; }}
.alerte-vert   .alerte-title {{ color: {GREEN}; }}
.alerte-message {{ font-size: 0.88rem; color: {TEXT2}; line-height: 1.5; }}

.employe-row {{
  display: flex; align-items: center; background: {CARD};
  border: 1px solid {BORDER}; border-radius: 12px; padding: 13px 16px;
  margin-bottom: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  transition: border-color 0.16s, box-shadow 0.16s;
}}
.employe-row:hover {{ border-color: {BORDER2}; box-shadow: 0 4px 16px rgba(52,211,153,0.08); }}
.employe-avatar {{
  width: 40px; height: 40px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  font-family: 'Cormorant Garamond', serif;
  font-weight: 700; font-size: 1rem; margin-right: 14px; flex-shrink: 0;
}}
.avatar-pde  {{ background: linear-gradient(135deg, {ACCENT}, {ACCENT2}); color: #fff; }}
.avatar-prep {{ background: linear-gradient(135deg, {BLUE}, #7dd3fc); color: #fff; }}
.badge-pde  {{ background: {ACCENT_BG}; border: 1px solid {BORDER2}; color: {ACCENT}; padding: 2px 10px; border-radius: 12px; font-size: 0.7rem; font-weight: 700; }}
.badge-prep {{ background: rgba(56,189,248,0.1); border: 1px solid rgba(56,189,248,0.3); color: {BLUE}; padding: 2px 10px; border-radius: 12px; font-size: 0.7rem; font-weight: 700; }}

.score-circle {{
  background: {CARD}; border-radius: 16px; padding: 28px 20px;
  text-align: center; box-shadow: {SHADOW};
}}
.hist-item {{
  background: {CARD}; border: 1px solid {BORDER}; border-left: 3px solid {ACCENT};
  border-radius: 10px; padding: 12px 16px; margin-bottom: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}}

::-webkit-scrollbar {{ width: 5px; height: 5px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: {BORDER2}; border-radius: 10px; }}
hr {{ border-color: {BORDER} !important; }}
[data-testid="stDataFrame"] {{ border: 1px solid {BORDER} !important; border-radius: 12px !important; overflow: hidden; }}
[data-testid="stDownloadButton"] > button {{
  background: {ACCENT_BG} !important; border: 1px solid {BORDER2} !important;
  color: {ACCENT} !important; border-radius: 10px !important; font-weight: 700 !important;
}}
.stSpinner > div {{ border-top-color: {ACCENT} !important; }}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
for k, v in {
    "model": None, "historique_chat": [], "messages_affichage": [],
    "api_configuree": False, "employe_actif": None,
    "historique_employe": [], "messages_employe": []
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

if not st.session_state.api_configuree:
    try:
        st.session_state.model = configurer_gemini()
        st.session_state.api_configuree = True
    except Exception:
        st.session_state.api_configuree = False

# ─────────────────────────────────────────────
# THEME TOGGLE BUTTON
# ─────────────────────────────────────────────
t_col1, t_col2 = st.columns([9, 1])
with t_col2:
    lbl = "☀️ Clair" if IS_DARK else "🌙 Sombre"
    st.button(lbl, on_click=switch_theme, key="theme_btn")

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div class='logo-wrap'>
        <span class='logo-cross'>✚</span>
        <div class='logo-name'>PharmAssist</div>
        <div class='logo-sub'>Agent RH Intelligent</div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.api_configuree:
        st.markdown(f"<div class='status-on'><div class='dot-on'>⬤ Agent Actif</div><div class='dot-sub'>Groq · LLaMA 3.3 70B</div></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='status-off'><div class='dot-off'>⬤ Agent Inactif</div><div class='dot-sub'>GROQ_API_KEY manquante dans .env</div></div>", unsafe_allow_html=True)

    st.markdown(f"""
    <div style='background:{CARD};border:1px solid {BORDER};border-radius:10px;padding:14px 16px;margin-bottom:16px;'>
        <div style='font-size:0.67rem;color:{MUTED};text-transform:uppercase;letter-spacing:2px;font-weight:700;margin-bottom:10px;'>📍 Pharmacie</div>
        <div style='font-family:Cormorant Garamond,serif;font-size:1.05rem;font-weight:700;color:{TEXT};margin-bottom:4px;'>{PHARMACIE['nom']}</div>
        <div style='color:{TEXT2};font-size:0.8rem;margin-bottom:2px;'>📍 {PHARMACIE['ville']}</div>
        <div style='color:{TEXT2};font-size:0.8rem;'>🕐 {PHARMACIE['horaires']}</div>
    </div>
    <div style='font-size:0.67rem;color:{MUTED};text-transform:uppercase;letter-spacing:2px;font-weight:700;margin-bottom:8px;'>👤 Portail Employé</div>
    """, unsafe_allow_html=True)

    noms_employes = [e["nom"] for e in EMPLOYES]
    employe_selectionne = st.selectbox("Connexion", ["— Manager —"] + noms_employes, label_visibility="collapsed")
    if employe_selectionne != "— Manager —":
        if st.session_state.employe_actif != employe_selectionne:
            st.session_state.employe_actif = employe_selectionne
            st.session_state.historique_employe = []
            st.session_state.messages_employe = []
        notifs = get_notifications(employe_selectionne)
        non_lues = [n for n in notifs if not n["lu"]]
        if non_lues:
            st.markdown(f"<div style='background:rgba(248,113,113,0.08);border:1px solid rgba(248,113,113,0.25);border-radius:8px;padding:9px 13px;color:{RED};font-size:0.8rem;margin-top:8px;'>🔔 {len(non_lues)} notification(s) non lue(s)</div>", unsafe_allow_html=True)
    else:
        st.session_state.employe_actif = None

    st.markdown(f"""
    <div style='margin-top:22px;border-top:1px solid {BORDER};padding-top:14px;
         font-size:0.67rem;color:{MUTED};text-align:center;line-height:1.9;'>
        Convention Collective IDCC 1996<br>Pharmacie d'officine · France<br>
        <span style='color:{ACCENT};font-weight:700;'>Powered by Groq API</span>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PAGE HEADER
# ─────────────────────────────────────────────
rapport = run_full_compliance_check()
score = rapport["rapport"]["score_conformite"]
score_color = "green" if score >= 90 else "orange" if score >= 75 else "red"

st.markdown(f"""
<div class='page-header'>
    <div class='ph-eyebrow'>Agent RH • IA Générative • IDCC 1996</div>
    <div class='ph-title'>✚ PharmAssist — Tableau de Bord RH</div>
    <div class='ph-sub'>{PHARMACIE['nom']} &nbsp;·&nbsp; {PHARMACIE['ville']} &nbsp;·&nbsp; {datetime.now().strftime('%A %d %B %Y').capitalize()}</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# MÉTRIQUES
# ─────────────────────────────────────────────
pde_count = sum(1 for e in EMPLOYES if e['qualifie'])
c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1:
    st.markdown(f"<div class='metric-card'><div class='metric-value green'>{METRIQUES['taux_couverture']}%</div><div class='metric-label'>Taux de couverture</div></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='metric-card'><div class='metric-value'>{len(EMPLOYES)}</div><div class='metric-label'>Employés actifs</div></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='metric-card'><div class='metric-value'>{pde_count}</div><div class='metric-label'>Pharmaciens PDE</div></div>", unsafe_allow_html=True)
with c4:
    st.markdown(f"<div class='metric-card'><div class='metric-value orange'>{METRIQUES['absences_ce_mois']}</div><div class='metric-label'>Absences ce mois</div></div>", unsafe_allow_html=True)
with c5:
    st.markdown(f"<div class='metric-card'><div class='metric-value red'>{METRIQUES['alertes_actives']}</div><div class='metric-label'>Alertes actives</div></div>", unsafe_allow_html=True)
with c6:
    st.markdown(f"<div class='metric-card'><div class='metric-value {score_color}'>{score}%</div><div class='metric-label'>Score conformité</div></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "💬 Agent IA", "📅 Planning", "👥 Équipe", "⚠️ Alertes",
    "✅ Conformité", "📋 Historique", "👤 Employés", "🏠 Portail Employé"
])

# ══════════════════════════════════════════════
# TAB 1 — CHAT
# ══════════════════════════════════════════════
with tab1:
    col_chat, col_suggestions = st.columns([2, 1])
    with col_chat:
        st.markdown("<div class='section-title'>💬 Conversation avec PharmAssist</div>", unsafe_allow_html=True)
        chat_html = "<div class='chat-container'>"
        if not st.session_state.messages_affichage:
            chat_html += f"""
            <div class='chat-empty'>
                <div class='chat-empty-icon'>✚</div>
                <div style='font-family:Cormorant Garamond,serif;font-size:1.1rem;color:{TEXT2};margin-bottom:6px;'>PharmAssist est prêt</div>
                <div style='font-size:0.83rem;color:{MUTED};'>Posez une question ou utilisez les suggestions →</div>
            </div>"""
        else:
            for msg in st.session_state.messages_affichage:
                if msg["role"] == "user":
                    contenu = html_lib.escape(msg['content'])
                    chat_html += f"<div><div class='message-label-user'>👤 Manager</div><div class='message-user'>{contenu}</div></div>"
                else:
                    contenu = html_lib.escape(msg['content']).replace('\n', '<br>')
                    chat_html += f"<div><div class='message-label-agent'>✚ PharmAssist</div><div class='message-agent'>{contenu}</div></div>"
                    if msg.get('actions'):
                        for act in msg['actions']:
                            succes = act['resultat'].get('succes', True)
                            icon = '✅' if succes else '❌'
                            label = act['outil'].replace('_', ' ').title()
                            msg_act = html_lib.escape(act['resultat'].get('message', ''))
                            chat_html += f"<div class='tool-tag'>{icon} {label} — {msg_act}</div>"
        chat_html += "</div>"
        st.markdown(chat_html, unsafe_allow_html=True)

        with st.form("chat_form", clear_on_submit=True):
            col_input, col_send = st.columns([5, 1])
            with col_input:
                user_input = st.text_input("Message", placeholder="Ex: Marie est absente demain matin, qui peut la remplacer ?", label_visibility="collapsed")
            with col_send:
                send = st.form_submit_button("Envoyer →", use_container_width=True)
        if send and user_input:
            if not st.session_state.api_configuree:
                st.error("⚠️ Agent inactif — vérifiez GROQ_API_KEY dans votre fichier .env")
            else:
                st.session_state.messages_affichage.append({"role": "user", "content": user_input})
                with st.spinner("PharmAssist analyse..."):
                    reponse, actions = chat_avec_agent(st.session_state.model, st.session_state.historique_chat, user_input)
                st.session_state.messages_affichage.append({"role": "agent", "content": reponse, "actions": actions})
                st.rerun()

    with col_suggestions:
        st.markdown("<div class='section-title'>⚡ Questions rapides</div>", unsafe_allow_html=True)
        suggestions = [
            ("🔄 Remplacement urgent",   "Marie est absente demain matin, qui peut la remplacer ?"),
            ("📅 Générer planning",       "Génère le planning de la semaine prochaine pour toute l'équipe"),
            ("⚠️ Périodes de surcharge",  "Quelles sont les semaines à risque de surcharge ce mois-ci ?"),
            ("📋 Congés Karim",           "Karim demande un congé payé du 15 au 19 mars, est-ce possible ?"),
            ("⚖️ Règles légales",         "Quelles sont les règles légales sur les heures de travail en pharmacie ?"),
            ("📊 Bilan RH",               "Donne-moi un bilan RH de la semaine en cours"),
            ("✅ Conformité",             "Quelles violations de conformité sont actives en ce moment ?"),
            ("📋 Créer absence",          "Crée une demande d'absence pour Karim Benali le 2025-03-15 de type Congé payé"),
            ("⚙️ Planning simulé",        "Génère une proposition de planning pour la semaine, sans remplacer l'actuel"),
        ]
        for label, question in suggestions:
            if st.button(label, use_container_width=True, key=f"sug_{label}"):
                if not st.session_state.api_configuree:
                    st.error("⚠️ Agent inactif — vérifiez votre fichier .env")
                else:
                    st.session_state.messages_affichage.append({"role": "user", "content": question})
                    with st.spinner("Analyse en cours..."):
                        reponse, actions = chat_avec_agent(st.session_state.model, st.session_state.historique_chat, question)
                    st.session_state.messages_affichage.append({"role": "agent", "content": reponse, "actions": actions})
                    st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Effacer conversation", use_container_width=True):
            st.session_state.messages_affichage = []
            st.session_state.historique_chat = []
            st.rerun()
        if st.button("🔄 Réinitialiser les données", use_container_width=True):
            reset_store()
            st.success("Données réinitialisées")
            st.rerun()

# ══════════════════════════════════════════════
# TAB 2 — PLANNING
# ══════════════════════════════════════════════
with tab2:
    st.markdown("<div class='section-title'>📅 Planning de la Semaine</div>", unsafe_allow_html=True)
    jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"]
    jours_labels = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]
    _planning_live = load_store()["planning"]
    data_planning = []
    for emp in EMPLOYES:
        row = {"Employé": emp["nom"], "Rôle": "PDE 💊" if emp["qualifie"] else "Préparateur"}
        for jour, label in zip(jours, jours_labels):
            pm = emp["nom"] in _planning_live.get(jour, {}).get("matin", [])
            pa = emp["nom"] in _planning_live.get(jour, {}).get("apres_midi", [])
            row[label] = "✅ Journée" if pm and pa else "🌅 Matin" if pm else "🌆 Après-midi" if pa else "—"
        data_planning.append(row)
    st.dataframe(pd.DataFrame(data_planning), use_container_width=True, hide_index=True, height=280)
    st.markdown("<br>", unsafe_allow_html=True)
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("<div class='section-title' style='font-size:1.1rem;'>👥 Effectif par jour</div>", unsafe_allow_html=True)
        effectifs = [{"Jour": j.capitalize(), "Matin": len(PLANNING_SEMAINE.get(j,{}).get("matin",[])), "Après-midi": len(PLANNING_SEMAINE.get(j,{}).get("apres_midi",[]))} for j in jours]
        df_effectif = pd.DataFrame(effectifs)
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Matin', x=df_effectif['Jour'], y=df_effectif['Matin'], marker_color='rgba(52,211,153,0.78)', marker_line_color=ACCENT, marker_line_width=1))
        fig.add_trace(go.Bar(name='Après-midi', x=df_effectif['Jour'], y=df_effectif['Après-midi'], marker_color='rgba(56,189,248,0.78)', marker_line_color=BLUE, marker_line_width=1))
        fig.update_layout(barmode='group', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color=PLOT_FONT, family='Nunito'), legend=dict(bgcolor='rgba(0,0,0,0)'), margin=dict(l=20,r=20,t=20,b=20), height=250, xaxis=dict(gridcolor=BORDER), yaxis=dict(gridcolor=BORDER))
        st.plotly_chart(fig, use_container_width=True)
    with col_g2:
        st.markdown("<div class='section-title' style='font-size:1.1rem;'>📊 Heures planifiées vs légales</div>", unsafe_allow_html=True)
        fig2 = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=METRIQUES['heures_planifiees_semaine'],
            delta={'reference': METRIQUES['heures_legales_semaine'], 'valueformat': '.0f'},
            gauge={'axis': {'range': [0, METRIQUES['heures_legales_semaine']], 'tickcolor': PLOT_FONT}, 'bar': {'color': ACCENT}, 'bgcolor': 'rgba(0,0,0,0)', 'steps': [{'range': [0,147], 'color': 'rgba(248,113,113,0.07)'}, {'range': [147,210], 'color': 'rgba(52,211,153,0.07)'}]},
            title={'text': "Heures planifiées", 'font': {'color': PLOT_FONT, 'size': 14}},
            number={'font': {'color': ACCENT, 'size': 36}}
        ))
        fig2.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color=PLOT_FONT, family='Nunito'), margin=dict(l=20,r=20,t=30,b=20), height=250)
        st.plotly_chart(fig2, use_container_width=True)

# ══════════════════════════════════════════════
# TAB 3 — ÉQUIPE
# ══════════════════════════════════════════════
with tab3:
    st.markdown("<div class='section-title'>👥 Équipe de la Pharmacie</div>", unsafe_allow_html=True)
    col_e1, col_e2 = st.columns([3, 2])
    with col_e1:
        for emp in EMPLOYES:
            initiales = "".join([n[0] for n in emp["nom"].split()[:2]])
            avatar_class = "avatar-pde" if emp["qualifie"] else "avatar-prep"
            badge_class = "badge-pde" if emp["qualifie"] else "badge-prep"
            badge_text = "Pharmacien PDE" if emp["qualifie"] else "Préparateur"
            conge_color = RED if emp["jours_conge_restants"] <= 3 else GREEN
            st.markdown(f"""
            <div class='employe-row'>
                <div class='employe-avatar {avatar_class}'>{initiales}</div>
                <div style='flex:1;'>
                    <div style='font-family:Cormorant Garamond,serif;font-weight:700;color:{TEXT};font-size:1rem;'>{emp['nom']}</div>
                    <div style='color:{TEXT2};font-size:0.79rem;'>{emp['role']}</div>
                </div>
                <div style='display:flex;gap:12px;align-items:center;'>
                    <span class='{badge_class}'>{badge_text}</span>
                    <span style='color:{MUTED};font-size:0.79rem;'>{emp['heures_semaine']}h/sem</span>
                    <span style='color:{conge_color};font-size:0.79rem;font-weight:700;'>{emp['jours_conge_restants']}j congés</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    with col_e2:
        st.markdown("<div class='section-title' style='font-size:1.1rem;'>📈 Répartition des rôles</div>", unsafe_allow_html=True)
        pde = sum(1 for e in EMPLOYES if e["qualifie"])
        prep = len(EMPLOYES) - pde
        fig3 = go.Figure(data=[go.Pie(labels=['Pharmaciens PDE', 'Préparateurs'], values=[pde, prep], hole=0.6,
            marker=dict(colors=['rgba(52,211,153,0.82)', 'rgba(56,189,248,0.82)'], line=dict(color=[ACCENT, BLUE], width=2)),
            textfont=dict(color='white', size=12))])
        fig3.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color=PLOT_FONT, family='Nunito'), legend=dict(bgcolor='rgba(0,0,0,0)'), margin=dict(l=20,r=20,t=20,b=20), height=220, annotations=[dict(text=f'{len(EMPLOYES)}<br>Employés', x=0.5, y=0.5, font_size=16, font_color=TEXT, showarrow=False)])
        st.plotly_chart(fig3, use_container_width=True)
        st.markdown("<div class='section-title' style='font-size:1.1rem;margin-top:8px;'>📋 Absences récentes</div>", unsafe_allow_html=True)
        for absence in ABSENCES:
            couleur = GREEN if absence["statut"] == "Validée" else ORANGE
            st.markdown(f"""
            <div style='background:{CARD};border:1px solid {BORDER};border-radius:9px;padding:10px 14px;margin-bottom:6px;'>
                <div style='font-family:Cormorant Garamond,serif;font-weight:600;color:{TEXT};font-size:0.95rem;'>{absence['employe']}</div>
                <div style='color:{TEXT2};font-size:0.78rem;'>{absence['date']} · {absence['type']}</div>
                <div style='color:{couleur};font-size:0.74rem;margin-top:3px;font-weight:700;'>⬤ {absence['statut']}</div>
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════
# TAB 4 — ALERTES
# ══════════════════════════════════════════════
with tab4:
    st.markdown("<div class='section-title'>⚠️ Alertes & Anticipation</div>", unsafe_allow_html=True)
    col_a1, col_a2 = st.columns([3, 2])
    with col_a1:
        st.markdown(f"<p style='color:{TEXT2};font-size:0.84rem;margin-bottom:16px;'>Alertes actives nécessitant une action</p>", unsafe_allow_html=True)
        for alerte in ALERTES:
            css_class = "alerte-rouge" if alerte["niveau"] == "rouge" else "alerte-orange"
            icon = "🚨" if alerte["niveau"] == "rouge" else "⚠️"
            st.markdown(f"<div class='{css_class}'><div class='alerte-title'>{icon} {alerte['type']} — {alerte['semaine']}</div><div class='alerte-message'>{alerte['message']}</div></div>", unsafe_allow_html=True)
    with col_a2:
        st.markdown("<div class='section-title' style='font-size:1.1rem;'>📊 Prévision d'activité</div>", unsafe_allow_html=True)
        mois = ['Jan','Fév','Mar','Avr','Mai','Jun','Jul','Aoû','Sep','Oct','Nov','Déc']
        charge = [75, 70, 90, 72, 68, 65, 60, 55, 78, 82, 88, 95]
        couleurs = ['rgba(248,113,113,0.75)' if c >= 85 else 'rgba(251,191,36,0.75)' if c >= 75 else 'rgba(52,211,153,0.75)' for c in charge]
        fig4 = go.Figure(go.Bar(x=mois, y=charge, marker_color=couleurs, marker_line_width=0))
        fig4.add_hline(y=85, line_dash="dash", line_color="rgba(248,113,113,0.55)", annotation_text="Seuil critique", annotation_font_color=RED)
        fig4.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color=PLOT_FONT, family='Nunito'), margin=dict(l=20,r=20,t=20,b=20), height=250, xaxis=dict(gridcolor=BORDER), yaxis=dict(gridcolor=BORDER, title=dict(text='Indice de charge', font=dict(color=PLOT_FONT))))
        st.plotly_chart(fig4, use_container_width=True)
        st.markdown(f"<div style='font-size:0.78rem;color:{MUTED};line-height:1.8;'>🔴 Surcharge critique (≥85) &nbsp; 🟠 Charge élevée (≥75) &nbsp; 🟢 Activité normale</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════
# TAB 5 — CONFORMITÉ
# ══════════════════════════════════════════════
with tab5:
    st.markdown("<div class='section-title'>✅ Rapport de Conformité — Convention IDCC 1996</div>", unsafe_allow_html=True)
    r = rapport["rapport"]
    score_color_hex = GREEN if r["score_conformite"] >= 90 else ORANGE if r["score_conformite"] >= 75 else RED
    border_color_hex = "rgba(52,211,153,0.4)" if r["score_conformite"] >= 90 else "rgba(251,191,36,0.4)" if r["score_conformite"] >= 75 else "rgba(248,113,113,0.4)"

    col_score, col_stats = st.columns([1, 3])
    with col_score:
        st.markdown(f"""
        <div class='score-circle' style='border:2px solid {border_color_hex};'>
            <div style='font-family:Cormorant Garamond,serif;font-size:3.6rem;font-weight:700;color:{score_color_hex};line-height:1;'>{r["score_conformite"]}%</div>
            <div style='color:{MUTED};font-size:0.72rem;text-transform:uppercase;letter-spacing:1px;margin-top:8px;'>Score de conformité</div>
            <div style='color:{MUTED};font-size:0.7rem;margin-top:5px;'>{r["date_analyse"]}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_stats:
        cs1, cs2, cs3, cs4 = st.columns(4)
        with cs1:
            st.markdown(f"<div class='metric-card'><div class='metric-value'>{r['total_verifications']}</div><div class='metric-label'>Vérifications</div></div>", unsafe_allow_html=True)
        with cs2:
            st.markdown(f"<div class='metric-card'><div class='metric-value green'>{r['conformes']}</div><div class='metric-label'>Conformes</div></div>", unsafe_allow_html=True)
        with cs3:
            st.markdown(f"<div class='metric-card'><div class='metric-value red'>{r['violations_critiques']}</div><div class='metric-label'>Critiques 🔴</div></div>", unsafe_allow_html=True)
        with cs4:
            st.markdown(f"<div class='metric-card'><div class='metric-value orange'>{r['violations_mineures']}</div><div class='metric-label'>Mineures 🟠</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        if rapport["violations_critiques"]:
            st.markdown(f"<p style='color:{RED};font-weight:700;font-size:0.84rem;text-transform:uppercase;letter-spacing:0.8px;'>🔴 Violations Critiques</p>", unsafe_allow_html=True)
            for v in rapport["violations_critiques"]:
                st.markdown(f"<div class='alerte-rouge'><div class='alerte-title'>{v['code']}</div><div class='alerte-message'>{v['message']}</div></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='alerte-vert'><div class='alerte-title'>✅ Aucune violation critique</div><div class='alerte-message'>Toutes les règles obligatoires sont respectées.</div></div>", unsafe_allow_html=True)
        if rapport["violations_mineures"]:
            st.markdown(f"<p style='color:{ORANGE};font-weight:700;font-size:0.84rem;text-transform:uppercase;letter-spacing:0.8px;margin-top:16px;'>🟠 Violations Mineures</p>", unsafe_allow_html=True)
            for v in rapport["violations_mineures"]:
                st.markdown(f"<div class='alerte-orange'><div class='alerte-title'>{v['code']}</div><div class='alerte-message'>{v['message']}</div></div>", unsafe_allow_html=True)
    with col_v2:
        st.markdown(f"<p style='color:{GREEN};font-weight:700;font-size:0.84rem;text-transform:uppercase;letter-spacing:0.8px;'>✅ Points Conformes</p>", unsafe_allow_html=True)
        conformes_uniques = {}
        for v in rapport["points_conformes"]:
            code = v["code"]
            if code not in conformes_uniques:
                conformes_uniques[code] = {"message": v["message"], "count": 1}
            else:
                conformes_uniques[code]["count"] += 1
        for code, info in conformes_uniques.items():
            count_badge = f" <span style='color:{MUTED};'>×{info['count']}</span>" if info["count"] > 1 else ""
            st.markdown(f"<div class='alerte-vert' style='padding:10px 14px;margin-bottom:6px;'><div style='font-size:0.82rem;color:{GREEN};font-weight:700;'>{code}{count_badge}</div><div style='font-size:0.8rem;color:{TEXT2};margin-top:2px;'>{info['message']}</div></div>", unsafe_allow_html=True)
        fig5 = go.Figure(data=[go.Pie(
            labels=['Conformes', 'Violations critiques', 'Violations mineures'],
            values=[r["conformes"], r["violations_critiques"], r["violations_mineures"]],
            hole=0.55,
            marker=dict(colors=['rgba(52,211,153,0.82)','rgba(248,113,113,0.82)','rgba(251,191,36,0.82)'], line=dict(color=[GREEN,RED,ORANGE],width=2)),
            textfont=dict(color='white', size=11)
        )])
        fig5.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color=PLOT_FONT, family='Nunito'), legend=dict(bgcolor='rgba(0,0,0,0)'), margin=dict(l=10,r=10,t=10,b=10), height=220, annotations=[dict(text='Bilan', x=0.5, y=0.5, font_size=14, font_color=TEXT, showarrow=False)])
        st.plotly_chart(fig5, use_container_width=True)

# ══════════════════════════════════════════════
# TAB 6 — HISTORIQUE
# ══════════════════════════════════════════════
with tab6:
    st.markdown("<div class='section-title'>📋 Historique des Actions RH</div>", unsafe_allow_html=True)
    store_data = load_store()
    historique = store_data.get("historique_actions", [])
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        if not historique:
            st.markdown(f"<div style='text-align:center;padding:40px;color:{MUTED};'><div style='font-size:2rem;margin-bottom:8px;'>📭</div><div>Aucune action enregistrée pour le moment.</div><div style='font-size:0.8rem;margin-top:6px;'>Les actions effectuées par l'agent apparaîtront ici.</div></div>", unsafe_allow_html=True)
        else:
            icons = {"create_absence":"🏥","approve_absence":"✅","reject_absence":"❌","modify_planning":"📅","generate_planning":"⚙️"}
            for action in reversed(historique):
                icon = icons.get(action["action"], "🔧")
                label = action["action"].replace("_", " ").title()
                details_str = " · ".join(f"<span style='color:{ACCENT};'>{k}</span>: {v}" for k,v in action.get("details",{}).items() if k != "remplace")
                st.markdown(f"""
                <div class='hist-item'>
                    <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;'>
                        <span style='font-family:Cormorant Garamond,serif;font-weight:700;color:{TEXT};font-size:0.98rem;'>{icon} {label}</span>
                        <span style='color:{MUTED};font-size:0.74rem;'>🕐 {action["timestamp"]}</span>
                    </div>
                    <div style='color:{TEXT2};font-size:0.8rem;'>{details_str}</div>
                </div>
                """, unsafe_allow_html=True)
    with col_h2:
        st.markdown("<div class='section-title' style='font-size:1.1rem;'>📊 Résumé</div>", unsafe_allow_html=True)
        type_counts = {}
        for a in historique:
            t = a["action"].replace("_"," ").title()
            type_counts[t] = type_counts.get(t,0)+1
        for t, count in sorted(type_counts.items(), key=lambda x:-x[1]):
            st.markdown(f"<div style='background:{CARD};border:1px solid {BORDER};border-radius:8px;padding:10px 14px;margin-bottom:6px;display:flex;justify-content:space-between;'><span style='color:{TEXT};font-size:0.84rem;'>{t}</span><span style='color:{ACCENT};font-weight:700;'>{count}</span></div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<div class='section-title' style='font-size:1.1rem;'>📥 Exports PDF</div>", unsafe_allow_html=True)
        try:
            pdf_planning = export_planning_pdf()
            st.download_button("📅 Exporter le Planning", data=pdf_planning, file_name=f"planning_pharmassist_{datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf", use_container_width=True)
        except Exception as e:
            st.error(f"Erreur PDF planning: {e}")
        try:
            pdf_conformite = export_conformite_pdf()
            st.download_button("✅ Rapport de Conformité", data=pdf_conformite, file_name=f"conformite_pharmassist_{datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf", use_container_width=True)
        except Exception as e:
            st.error(f"Erreur PDF conformité: {e}")

# ══════════════════════════════════════════════
# TAB 7 — GESTION DES EMPLOYÉS
# ══════════════════════════════════════════════
with tab7:
    st.markdown("<div class='section-title'>👤 Gestion des Employés</div>", unsafe_allow_html=True)
    col_emp1, col_emp2 = st.columns([2, 1])
    with col_emp1:
        st.markdown(f"<p style='color:{TEXT2};font-size:0.84rem;margin-bottom:16px;'>Équipe actuelle — modifications via l'agent en session</p>", unsafe_allow_html=True)
        for emp in EMPLOYES:
            initiales = "".join([n[0] for n in emp["nom"].split()[:2]])
            avatar_class = "avatar-pde" if emp["qualifie"] else "avatar-prep"
            conge_color = RED if emp["jours_conge_restants"] <= 3 else GREEN
            st.markdown(f"""
            <div class='employe-row'>
                <div class='employe-avatar {avatar_class}'>{initiales}</div>
                <div style='flex:1;'>
                    <div style='font-family:Cormorant Garamond,serif;font-weight:700;color:{TEXT};font-size:1rem;'>{emp["nom"]}</div>
                    <div style='color:{TEXT2};font-size:0.78rem;'>{emp["role"]}</div>
                    <div style='color:{MUTED};font-size:0.71rem;margin-top:2px;'>Dispo: {", ".join(d.capitalize() for d in emp["disponibilites"])}</div>
                </div>
                <div style='text-align:right;'>
                    <div style='color:{TEXT2};font-size:0.8rem;'>{emp["heures_semaine"]}h/sem</div>
                    <div style='color:{conge_color};font-size:0.78rem;font-weight:700;'>{emp["jours_conge_restants"]}j congés</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    with col_emp2:
        st.markdown("<div class='section-title' style='font-size:1.1rem;'>➕ Nouvelle demande d'absence</div>", unsafe_allow_html=True)
        with st.form("form_absence"):
            emp_choix = st.selectbox("Employé", [e["nom"] for e in EMPLOYES])
            date_absence = st.date_input("Date")
            type_abs = st.selectbox("Type", ["Maladie", "Congé payé", "Congé sans solde", "Formation", "Autre"])
            submitted = st.form_submit_button("Créer la demande", use_container_width=True)
            if submitted:
                if st.session_state.api_configuree:
                    prompt = f"Crée une demande d'absence pour {emp_choix} le {date_absence.strftime('%Y-%m-%d')} de type {type_abs}"
                    with st.spinner("Traitement..."):
                        reponse, actions = chat_avec_agent(st.session_state.model, st.session_state.historique_chat, prompt)
                    if actions and actions[0]["resultat"].get("succes"):
                        st.success("✅ Demande créée !")
                    else:
                        st.warning(reponse[:200])
                else:
                    st.error("Agent inactif — vérifiez votre .env")
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<div class='section-title' style='font-size:1.1rem;'>📋 Absences en attente</div>", unsafe_allow_html=True)
        store_data = load_store()
        en_attente = [a for a in store_data.get("absences",[]) if a["statut"]=="En attente"]
        if not en_attente:
            st.markdown(f"<p style='color:{MUTED};font-size:0.82rem;'>Aucune absence en attente.</p>", unsafe_allow_html=True)
        else:
            for absence in en_attente:
                col_a, col_b, col_c = st.columns([3,1,1])
                with col_a:
                    st.markdown(f"<div style='padding:5px 0;'><div style='color:{TEXT};font-size:0.85rem;font-weight:600;'>{absence['employe']}</div><div style='color:{TEXT2};font-size:0.75rem;'>{absence['date']} · {absence['type']}</div></div>", unsafe_allow_html=True)
                with col_b:
                    if st.button("✅", key=f"app_{absence['employe']}_{absence['date']}", help="Approuver"):
                        if st.session_state.api_configuree:
                            chat_avec_agent(st.session_state.model, st.session_state.historique_chat, f"Approuve l'absence de {absence['employe']} le {absence['date']}")
                            st.rerun()
                with col_c:
                    if st.button("❌", key=f"rej_{absence['employe']}_{absence['date']}", help="Rejeter"):
                        if st.session_state.api_configuree:
                            chat_avec_agent(st.session_state.model, st.session_state.historique_chat, f"Rejette l'absence de {absence['employe']} le {absence['date']}")
                            st.rerun()

# ══════════════════════════════════════════════
# TAB 8 — PORTAIL EMPLOYÉ
# ══════════════════════════════════════════════
with tab8:
    if not st.session_state.employe_actif:
        st.markdown(f"""
        <div style='text-align:center;padding:70px 20px;color:{MUTED};'>
            <div style='font-size:3.5rem;margin-bottom:14px;font-family:Cormorant Garamond,serif;color:{BORDER2};'>✚</div>
            <div style='font-family:Cormorant Garamond,serif;font-size:1.4rem;color:{TEXT2};margin-bottom:8px;'>Portail Employé</div>
            <div style='font-size:0.88rem;'>Sélectionnez votre nom dans la barre latérale gauche pour accéder à votre espace personnel.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        nom = st.session_state.employe_actif
        emp_info = next((e for e in EMPLOYES if e["nom"] == nom), {})
        store_data = load_store()
        solde = store_data.get("employes_soldes", {}).get(nom, emp_info.get("jours_conge_restants", 0))
        notifs = get_notifications(nom)
        non_lues = [n for n in notifs if not n["lu"]]
        initiales = "".join([n[0] for n in nom.split()[:2]])
        avatar_color = ACCENT if emp_info.get("qualifie") else BLUE

        st.markdown(f"""
        <div style='background:{CARD};border:1px solid {BORDER};border-top:3px solid {ACCENT};
             border-radius:14px;padding:20px 26px;margin-bottom:22px;
             display:flex;align-items:center;gap:18px;box-shadow:{SHADOW};'>
            <div style='width:52px;height:52px;border-radius:14px;background:{avatar_color};
                 display:flex;align-items:center;justify-content:center;
                 font-family:Cormorant Garamond,serif;font-weight:700;font-size:1.2rem;
                 color:white;flex-shrink:0;'>{initiales}</div>
            <div style='flex:1;'>
                <div style='font-family:Cormorant Garamond,serif;font-size:1.3rem;color:{TEXT};font-weight:700;'>{nom}</div>
                <div style='color:{TEXT2};font-size:0.84rem;'>{emp_info.get("role","")}</div>
            </div>
            <div style='text-align:right;'>
                <div style='font-family:Cormorant Garamond,serif;font-size:2.2rem;color:{GREEN};font-weight:700;line-height:1;'>{solde}</div>
                <div style='color:{MUTED};font-size:0.72rem;'>jours congés restants</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_emp_chat, col_emp_info2 = st.columns([3, 2])
        with col_emp_chat:
            st.markdown("<div class='section-title'>💬 Mon Assistant RH</div>", unsafe_allow_html=True)
            suggestions_emp = [
                ("📅 Mes shifts",      "Quels sont mes shifts cette semaine ?"),
                ("📋 Mes absences",    "Montre-moi mes demandes d'absence en cours"),
                ("🏖️ Poser un congé", f"Je voudrais poser un congé payé le 2025-03-20"),
                ("🔔 Notifications",  "Est-ce que j'ai des notifications ?"),
                ("⚖️ Mes droits",     "Combien de jours de congés me restent-il ?"),
            ]
            cols_sugg = st.columns(len(suggestions_emp))
            for i, (label, question) in enumerate(suggestions_emp):
                with cols_sugg[i]:
                    if st.button(label, key=f"emp_sug_{i}", use_container_width=True):
                        if st.session_state.api_configuree:
                            st.session_state.messages_employe.append({"role":"user","content":question})
                            with st.spinner("..."):
                                reponse, _ = chat_employe(st.session_state.model, st.session_state.historique_employe, question, nom)
                            st.session_state.messages_employe.append({"role":"agent","content":reponse})
                            st.rerun()

            chat_html = "<div class='chat-container' style='min-height:320px;max-height:420px;'>"
            if not st.session_state.messages_employe:
                chat_html += f"""
                <div class='chat-empty'>
                    <div class='chat-empty-icon'>✚</div>
                    <div style='font-family:Cormorant Garamond,serif;color:{TEXT2};font-size:1.05rem;'>Bonjour {nom.split()[0]} !</div>
                    <div style='font-size:0.81rem;color:{MUTED};margin-top:5px;'>Posez une question ou utilisez les raccourcis ci-dessus.</div>
                </div>"""
            else:
                for msg in st.session_state.messages_employe:
                    if msg["role"] == "user":
                        contenu = html_lib.escape(msg["content"])
                        chat_html += f"<div><div class='message-label-user'>👤 {nom.split()[0]}</div><div class='message-user'>{contenu}</div></div>"
                    else:
                        contenu = html_lib.escape(msg["content"]).replace("\n","<br>")
                        chat_html += f"<div><div class='message-label-agent'>✚ PharmAssist</div><div class='message-agent'>{contenu}</div></div>"
            chat_html += "</div>"
            st.markdown(chat_html, unsafe_allow_html=True)

            with st.form("emp_chat_form", clear_on_submit=True):
                col_ei, col_es = st.columns([5,1])
                with col_ei:
                    emp_input = st.text_input("Message", placeholder="Ex: Je suis malade jeudi, comment faire ?", label_visibility="collapsed")
                with col_es:
                    emp_send = st.form_submit_button("Envoyer →", use_container_width=True)
            if emp_send and emp_input:
                if not st.session_state.api_configuree:
                    st.error("Agent inactif — vérifiez votre .env")
                else:
                    st.session_state.messages_employe.append({"role":"user","content":emp_input})
                    with st.spinner("PharmAssist répond..."):
                        reponse, _ = chat_employe(st.session_state.model, st.session_state.historique_employe, emp_input, nom)
                    st.session_state.messages_employe.append({"role":"agent","content":reponse})
                    st.rerun()
            if st.button("🗑️ Effacer conversation", key="clear_emp"):
                st.session_state.messages_employe = []
                st.session_state.historique_employe = []
                st.rerun()

        with col_emp_info2:
            st.markdown("<div class='section-title' style='font-size:1.1rem;'>🔔 Mes Notifications</div>", unsafe_allow_html=True)
            if not notifs:
                st.markdown(f"<p style='color:{MUTED};font-size:0.82rem;'>Aucune notification.</p>", unsafe_allow_html=True)
            else:
                colors_map = {
                    "urgent":  (RED,    "rgba(248,113,113,0.07)", "rgba(248,113,113,0.28)"),
                    "warning": (ORANGE, "rgba(251,191,36,0.07)",  "rgba(251,191,36,0.28)"),
                    "success": (GREEN,  "rgba(52,211,153,0.07)",  "rgba(52,211,153,0.25)"),
                    "info":    (ACCENT2, ACCENT_BG, BORDER),
                }
                icons_n = {"urgent":"🚨","warning":"⚠️","success":"✅","info":"ℹ️"}
                for notif in reversed(notifs[-8:]):
                    text_c, bg_c, border_c = colors_map.get(notif["type"], colors_map["info"])
                    lu_opacity = "0.45" if notif["lu"] else "1"
                    icon_n = icons_n.get(notif["type"],"ℹ️")
                    st.markdown(f"""
                    <div style='background:{bg_c};border:1px solid {border_c};border-left:3px solid {text_c};
                         border-radius:8px;padding:10px 13px;margin-bottom:6px;opacity:{lu_opacity};'>
                        <div style='font-size:0.78rem;color:{text_c};font-weight:700;margin-bottom:3px;'>{icon_n} {notif["type"].upper()}</div>
                        <div style='font-size:0.82rem;color:{TEXT2};'>{notif["message"]}</div>
                        <div style='font-size:0.7rem;color:{MUTED};margin-top:4px;'>{notif["timestamp"]}</div>
                    </div>
                    """, unsafe_allow_html=True)
                if non_lues:
                    if st.button("✓ Marquer tout comme lu", key="mark_read", use_container_width=True):
                        mark_notifications_read(nom)
                        st.rerun()

            st.markdown("<div class='section-title' style='font-size:1.1rem;margin-top:16px;'>📅 Mes Shifts</div>", unsafe_allow_html=True)
            planning_live = store_data["planning"]
            jours_p = ["lundi","mardi","mercredi","jeudi","vendredi","samedi"]
            shifts_count = 0
            for jour in jours_p:
                matin = nom in planning_live.get(jour,{}).get("matin",[])
                am    = nom in planning_live.get(jour,{}).get("apres_midi",[])
                if matin or am:
                    shifts_count += 1
                    lb_s = "🌞 Journée" if matin and am else "🌅 Matin" if matin else "🌆 Après-midi"
                    col_s = ACCENT if matin and am else ORANGE if matin else GREEN
                    st.markdown(f"""
                    <div style='display:flex;justify-content:space-between;align-items:center;
                         background:{CARD};border:1px solid {BORDER};
                         border-radius:8px;padding:9px 13px;margin-bottom:5px;'>
                        <span style='color:{TEXT};font-size:0.84rem;font-weight:600;'>{jour.capitalize()}</span>
                        <span style='color:{col_s};font-size:0.82rem;font-weight:700;'>{lb_s}</span>
                    </div>
                    """, unsafe_allow_html=True)
            if shifts_count == 0:
                st.markdown(f"<p style='color:{MUTED};font-size:0.82rem;'>Aucun shift planifié cette semaine.</p>", unsafe_allow_html=True)