import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import html as html_lib
from datetime import datetime
from agent import configurer_gemini, chat_avec_agent
from data import (EMPLOYES, PLANNING_SEMAINE, ABSENCES,
                  ALERTES, METRIQUES, PHARMACIE)
from Rulesengine import run_full_compliance_check

st.set_page_config(
    page_title="PharmAssist RH",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0a0e1a;
    color: #e8eaf0;
}
.stApp {
    background: linear-gradient(135deg, #0a0e1a 0%, #0d1528 50%, #0a1020 100%);
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1528 0%, #111827 100%);
    border-right: 1px solid rgba(99, 179, 237, 0.15);
}
.main-header {
    background: linear-gradient(135deg, #0d1f3c 0%, #1a2f4e 100%);
    border: 1px solid rgba(99, 179, 237, 0.2);
    border-radius: 16px;
    padding: 28px 36px;
    margin-bottom: 28px;
    position: relative;
    overflow: hidden;
}
.main-header h1 {
    font-family: 'DM Serif Display', serif;
    font-size: 2.2rem;
    color: #ffffff;
    margin: 0;
    letter-spacing: -0.5px;
}
.main-header p { color: #7fb3d3; margin: 6px 0 0 0; font-size: 0.95rem; }
.header-badge {
    display: inline-block;
    background: rgba(99, 179, 237, 0.15);
    border: 1px solid rgba(99, 179, 237, 0.3);
    color: #63b3ed;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 500;
    margin-bottom: 12px;
    letter-spacing: 1px;
    text-transform: uppercase;
}
.metric-card {
    background: linear-gradient(135deg, #0d1f3c 0%, #132840 100%);
    border: 1px solid rgba(99, 179, 237, 0.18);
    border-radius: 14px;
    padding: 22px 24px;
    text-align: center;
    height: 130px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}
.metric-value { font-family: 'DM Serif Display', serif; font-size: 2.4rem; color: #63b3ed; line-height: 1; margin-bottom: 6px; }
.metric-value.green { color: #68d391; }
.metric-value.orange { color: #f6ad55; }
.metric-value.red { color: #fc8181; }
.metric-label { font-size: 0.8rem; color: #7fb3d3; font-weight: 400; text-transform: uppercase; letter-spacing: 0.8px; }
.section-title { font-family: 'DM Serif Display', serif; font-size: 1.25rem; color: #ffffff; margin: 0 0 18px 0; }
.alerte-rouge {
    background: rgba(252, 129, 129, 0.08);
    border: 1px solid rgba(252, 129, 129, 0.35);
    border-left: 4px solid #fc8181;
    border-radius: 10px; padding: 14px 18px; margin-bottom: 10px;
}
.alerte-orange {
    background: rgba(246, 173, 85, 0.08);
    border: 1px solid rgba(246, 173, 85, 0.35);
    border-left: 4px solid #f6ad55;
    border-radius: 10px; padding: 14px 18px; margin-bottom: 10px;
}
.alerte-vert {
    background: rgba(104, 211, 145, 0.08);
    border: 1px solid rgba(104, 211, 145, 0.35);
    border-left: 4px solid #68d391;
    border-radius: 10px; padding: 14px 18px; margin-bottom: 10px;
}
.alerte-title { font-weight: 600; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 4px; }
.alerte-rouge .alerte-title { color: #fc8181; }
.alerte-orange .alerte-title { color: #f6ad55; }
.alerte-vert .alerte-title { color: #68d391; }
.alerte-message { font-size: 0.9rem; color: #c4d4e3; }
.employe-row {
    display: flex; align-items: center;
    background: rgba(99, 179, 237, 0.05);
    border: 1px solid rgba(99, 179, 237, 0.1);
    border-radius: 10px; padding: 12px 16px; margin-bottom: 8px;
}
.employe-avatar { width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.85rem; margin-right: 14px; flex-shrink: 0; }
.avatar-pde { background: linear-gradient(135deg, #63b3ed, #4299e1); color: white; }
.avatar-prep { background: linear-gradient(135deg, #68d391, #48bb78); color: white; }
.badge-pde { background: rgba(99, 179, 237, 0.2); border: 1px solid rgba(99, 179, 237, 0.4); color: #63b3ed; padding: 2px 10px; border-radius: 12px; font-size: 0.72rem; }
.badge-prep { background: rgba(104, 211, 145, 0.2); border: 1px solid rgba(104, 211, 145, 0.4); color: #68d391; padding: 2px 10px; border-radius: 12px; font-size: 0.72rem; }
.chat-container {
    background: linear-gradient(135deg, #0a1628 0%, #0d1f3c 100%);
    border: 1px solid rgba(99, 179, 237, 0.2);
    border-radius: 14px; padding: 20px;
    min-height: 420px; max-height: 520px; overflow-y: auto; margin-bottom: 16px;
}
.message-user {
    background: linear-gradient(135deg, #1a3a5c, #1e4570);
    border: 1px solid rgba(99, 179, 237, 0.25);
    border-radius: 14px 14px 4px 14px;
    padding: 12px 16px; margin: 10px 0 10px 40px; font-size: 0.92rem; color: #e8eaf0;
}
.message-agent {
    background: linear-gradient(135deg, #0f2a1a, #122e1e);
    border: 1px solid rgba(104, 211, 145, 0.2);
    border-radius: 14px 14px 14px 4px;
    padding: 12px 16px; margin: 10px 40px 10px 0; font-size: 0.92rem; color: #e8eaf0;
}
.message-label-user { font-size: 0.72rem; color: #63b3ed; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px; }
.message-label-agent { font-size: 0.72rem; color: #68d391; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px; }
.stTextInput > div > div > input {
    background: rgba(13, 31, 60, 0.8) !important;
    border: 1px solid rgba(99, 179, 237, 0.3) !important;
    border-radius: 10px !important; color: #e8eaf0 !important;
}
.stButton > button {
    background: linear-gradient(135deg, #1a4a7a, #1e5a8a) !important;
    border: 1px solid rgba(99, 179, 237, 0.4) !important;
    color: #e8eaf0 !important; border-radius: 10px !important; font-weight: 500 !important;
}
.stTabs [data-baseweb="tab-list"] { background: transparent; border-bottom: 1px solid rgba(99, 179, 237, 0.15); }
.stTabs [data-baseweb="tab"] { background: transparent; color: #7fb3d3; }
.stTabs [aria-selected="true"] { background: rgba(99, 179, 237, 0.1) !important; color: #63b3ed !important; border-bottom: 2px solid #63b3ed !important; }
.score-circle {
    width: 120px; height: 120px; border-radius: 50%;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    margin: 0 auto 20px auto;
    font-family: 'DM Serif Display', serif;
}
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0a0e1a; }
::-webkit-scrollbar-thumb { background: rgba(99, 179, 237, 0.3); border-radius: 3px; }
hr { border-color: rgba(99, 179, 237, 0.1) !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
if "model" not in st.session_state:
    st.session_state.model = None
if "historique_chat" not in st.session_state:
    st.session_state.historique_chat = []
if "messages_affichage" not in st.session_state:
    st.session_state.messages_affichage = []
if "api_configuree" not in st.session_state:
    st.session_state.api_configuree = False

# Auto-connect depuis .env au démarrage
if not st.session_state.api_configuree:
    try:
        st.session_state.model = configurer_gemini()
        st.session_state.api_configuree = True
    except Exception:
        st.session_state.api_configuree = False

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 10px 0 20px 0;'>
        <div style='font-size: 2.5rem; margin-bottom: 8px;'>💊</div>
        <div style='font-family: DM Serif Display, serif; font-size: 1.4rem; color: #ffffff;'>PharmAssist</div>
        <div style='font-size: 0.78rem; color: #7fb3d3; letter-spacing: 1px; text-transform: uppercase;'>Agent RH Intelligent</div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    # Statut de connexion
    if st.session_state.api_configuree:
        st.markdown("""
        <div style='background: rgba(104, 211, 145, 0.1); border: 1px solid rgba(104, 211, 145, 0.3);
             border-radius: 10px; padding: 12px; text-align: center;'>
            <div style='color: #68d391; font-weight: 600; font-size: 0.85rem;'>● Agent Actif</div>
            <div style='color: #7fb3d3; font-size: 0.75rem; margin-top: 4px;'>Groq · LLaMA 3.3 70B</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='background: rgba(252, 129, 129, 0.08); border: 1px solid rgba(252, 129, 129, 0.25);
             border-radius: 10px; padding: 12px; text-align: center;'>
            <div style='color: #fc8181; font-weight: 600; font-size: 0.85rem;'>● Agent Inactif</div>
            <div style='color: #7fb3d3; font-size: 0.75rem; margin-top: 4px;'>GROQ_API_KEY manquante dans .env</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.markdown(f"""
    <div style='padding: 4px 0;'>
        <p style='color:#7fb3d3; font-size:0.78rem; text-transform:uppercase; letter-spacing:0.8px; font-weight:600; margin-bottom:12px;'>📍 Pharmacie</p>
        <p style='color:#e8eaf0; font-size:0.9rem; margin:4px 0;'><strong>{PHARMACIE['nom']}</strong></p>
        <p style='color:#7fb3d3; font-size:0.82rem; margin:4px 0;'>📍 {PHARMACIE['ville']}</p>
        <p style='color:#7fb3d3; font-size:0.82rem; margin:4px 0;'>🕐 {PHARMACIE['horaires']}</p>
    </div>
    """, unsafe_allow_html=True)
    st.divider()
    st.markdown("<p style='color:#4a6080; font-size:0.72rem; text-align:center;'>Convention Collective IDCC 1996<br>Pharmacie d'officine — France</p>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown(f"""
<div class='main-header'>
    <div class='header-badge'>Agent RH • IA Générative</div>
    <h1>💊 PharmAssist — Tableau de Bord RH</h1>
    <p>{PHARMACIE['nom']} · {PHARMACIE['ville']} · {datetime.now().strftime('%A %d %B %Y').capitalize()}</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# MÉTRIQUES
# ─────────────────────────────────────────────
rapport = run_full_compliance_check()
score = rapport["rapport"]["score_conformite"]
score_color = "green" if score >= 90 else "orange" if score >= 75 else "red"

c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1:
    st.markdown(f"<div class='metric-card'><div class='metric-value green'>{METRIQUES['taux_couverture']}%</div><div class='metric-label'>Taux de couverture</div></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='metric-card'><div class='metric-value'>{len(EMPLOYES)}</div><div class='metric-label'>Employés actifs</div></div>", unsafe_allow_html=True)
with c3:
    pde_count = sum(1 for e in EMPLOYES if e['qualifie'])
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
tab1, tab2, tab3, tab4, tab5 = st.tabs(["💬 Agent IA", "📅 Planning", "👥 Équipe", "⚠️ Alertes", "✅ Conformité"])

# ══════════════════════════════════════════════
# TAB 1 — CHAT
# ══════════════════════════════════════════════
with tab1:
    col_chat, col_suggestions = st.columns([2, 1])
    with col_chat:
        st.markdown("<div class='section-title'>💬 Conversation avec PharmAssist</div>", unsafe_allow_html=True)
        chat_html = "<div class='chat-container'>"
        if not st.session_state.messages_affichage:
            chat_html += """
            <div style='text-align:center; padding: 60px 20px; color: #4a6080;'>
                <div style='font-size: 2.5rem; margin-bottom: 12px;'>🤖</div>
                <div style='font-family: DM Serif Display, serif; font-size: 1.1rem; color: #7fb3d3; margin-bottom: 8px;'>PharmAssist est prêt</div>
                <div style='font-size: 0.85rem;'>Posez une question ou utilisez les suggestions →</div>
            </div>
            """
        else:
            for msg in st.session_state.messages_affichage:
                if msg["role"] == "user":
                    contenu = html_lib.escape(msg['content'])
                    chat_html += f"<div><div class='message-label-user'>👤 Manager</div><div class='message-user'>{contenu}</div></div>"
                else:
                    contenu = html_lib.escape(msg['content']).replace('\n', '<br>')
                    chat_html += f"<div><div class='message-label-agent'>🤖 PharmAssist</div><div class='message-agent'>{contenu}</div></div>"
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
                    reponse = chat_avec_agent(st.session_state.model, st.session_state.historique_chat, user_input)
                st.session_state.messages_affichage.append({"role": "agent", "content": reponse})
                st.rerun()

    with col_suggestions:
        st.markdown("<div class='section-title'>⚡ Questions rapides</div>", unsafe_allow_html=True)
        suggestions = [
            ("🔄 Remplacement urgent", "Marie est absente demain matin, qui peut la remplacer ?"),
            ("📅 Générer planning", "Génère le planning de la semaine prochaine pour toute l'équipe"),
            ("⚠️ Périodes de surcharge", "Quelles sont les semaines à risque de surcharge ce mois-ci ?"),
            ("📋 Congés Karim", "Karim demande un congé payé du 15 au 19 mars, est-ce possible ?"),
            ("⚖️ Règles légales", "Quelles sont les règles légales sur les heures de travail en pharmacie ?"),
            ("📊 Bilan RH", "Donne-moi un bilan RH de la semaine en cours"),
            ("✅ Conformité", "Quelles violations de conformité sont actives en ce moment ?"),
        ]
        for label, question in suggestions:
            if st.button(label, use_container_width=True, key=f"sug_{label}"):
                if not st.session_state.api_configuree:
                    st.error("⚠️ Agent inactif — vérifiez votre fichier .env")
                else:
                    st.session_state.messages_affichage.append({"role": "user", "content": question})
                    with st.spinner("Analyse en cours..."):
                        reponse = chat_avec_agent(st.session_state.model, st.session_state.historique_chat, question)
                    st.session_state.messages_affichage.append({"role": "agent", "content": reponse})
                    st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Effacer conversation", use_container_width=True):
            st.session_state.messages_affichage = []
            st.session_state.historique_chat = []
            st.rerun()

# ══════════════════════════════════════════════
# TAB 2 — PLANNING
# ══════════════════════════════════════════════
with tab2:
    st.markdown("<div class='section-title'>📅 Planning de la Semaine</div>", unsafe_allow_html=True)
    jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"]
    jours_labels = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]
    data_planning = []
    for emp in EMPLOYES:
        row = {"Employé": emp["nom"], "Rôle": "PDE 💊" if emp["qualifie"] else "Préparateur"}
        for jour, label in zip(jours, jours_labels):
            present_matin = emp["nom"] in PLANNING_SEMAINE.get(jour, {}).get("matin", [])
            present_am = emp["nom"] in PLANNING_SEMAINE.get(jour, {}).get("apres_midi", [])
            if present_matin and present_am:
                row[label] = "✅ Journée"
            elif present_matin:
                row[label] = "🌅 Matin"
            elif present_am:
                row[label] = "🌆 Après-midi"
            else:
                row[label] = "—"
        data_planning.append(row)
    df_planning = pd.DataFrame(data_planning)
    st.dataframe(df_planning, use_container_width=True, hide_index=True, height=280)
    st.markdown("<br>", unsafe_allow_html=True)
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("<div class='section-title' style='font-size:1rem;'>👥 Effectif par jour</div>", unsafe_allow_html=True)
        effectifs = []
        for jour in jours:
            matin = len(PLANNING_SEMAINE.get(jour, {}).get("matin", []))
            am = len(PLANNING_SEMAINE.get(jour, {}).get("apres_midi", []))
            effectifs.append({"Jour": jour.capitalize(), "Matin": matin, "Après-midi": am})
        df_effectif = pd.DataFrame(effectifs)
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Matin', x=df_effectif['Jour'], y=df_effectif['Matin'], marker_color='rgba(99, 179, 237, 0.8)'))
        fig.add_trace(go.Bar(name='Après-midi', x=df_effectif['Jour'], y=df_effectif['Après-midi'], marker_color='rgba(104, 211, 145, 0.8)'))
        fig.update_layout(barmode='group', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#7fb3d3'), legend=dict(bgcolor='rgba(0,0,0,0)'), margin=dict(l=20, r=20, t=20, b=20), height=250, xaxis=dict(gridcolor='rgba(99,179,237,0.1)'), yaxis=dict(gridcolor='rgba(99,179,237,0.1)'))
        st.plotly_chart(fig, use_container_width=True)
    with col_g2:
        st.markdown("<div class='section-title' style='font-size:1rem;'>📊 Heures planifiées vs légales</div>", unsafe_allow_html=True)
        fig2 = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=METRIQUES['heures_planifiees_semaine'],
            delta={'reference': METRIQUES['heures_legales_semaine'], 'valueformat': '.0f'},
            gauge={'axis': {'range': [0, METRIQUES['heures_legales_semaine']]}, 'bar': {'color': "rgba(99, 179, 237, 0.8)"}, 'bgcolor': "rgba(0,0,0,0)", 'steps': [{'range': [0, 147], 'color': 'rgba(252,129,129,0.1)'}, {'range': [147, 210], 'color': 'rgba(104,211,145,0.1)'}]},
            title={'text': "Heures planifiées", 'font': {'color': '#7fb3d3', 'size': 14}},
            number={'font': {'color': '#63b3ed', 'size': 36}}
        ))
        fig2.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#7fb3d3'), margin=dict(l=20, r=20, t=30, b=20), height=250)
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
            st.markdown(f"""
            <div class='employe-row'>
                <div class='employe-avatar {avatar_class}'>{initiales}</div>
                <div style='flex:1;'>
                    <div style='font-weight:600; color:#e8eaf0; font-size:0.92rem;'>{emp['nom']}</div>
                    <div style='color:#7fb3d3; font-size:0.8rem;'>{emp['role']}</div>
                </div>
                <div style='display:flex; gap:12px; align-items:center;'>
                    <span class='{badge_class}'>{badge_text}</span>
                    <span style='color:#7fb3d3; font-size:0.8rem;'>{emp['heures_semaine']}h/sem</span>
                    <span style='color:#68d391; font-size:0.8rem;'>{emp['jours_conge_restants']}j congés</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    with col_e2:
        st.markdown("<div class='section-title' style='font-size:1rem;'>📈 Répartition des rôles</div>", unsafe_allow_html=True)
        pde = sum(1 for e in EMPLOYES if e["qualifie"])
        prep = len(EMPLOYES) - pde
        fig3 = go.Figure(data=[go.Pie(labels=['Pharmaciens PDE', 'Préparateurs'], values=[pde, prep], hole=0.6, marker=dict(colors=['rgba(99, 179, 237, 0.8)', 'rgba(104, 211, 145, 0.8)'], line=dict(color=['#63b3ed', '#68d391'], width=2)), textfont=dict(color='white', size=12))])
        fig3.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#7fb3d3'), legend=dict(bgcolor='rgba(0,0,0,0)'), margin=dict(l=20, r=20, t=20, b=20), height=220, annotations=[dict(text=f'{len(EMPLOYES)}<br>Employés', x=0.5, y=0.5, font_size=16, font_color='#e8eaf0', showarrow=False)])
        st.plotly_chart(fig3, use_container_width=True)
        st.markdown("<div class='section-title' style='font-size:1rem; margin-top:8px;'>📋 Absences récentes</div>", unsafe_allow_html=True)
        for absence in ABSENCES:
            couleur = "#68d391" if absence["statut"] == "Validée" else "#f6ad55"
            st.markdown(f"""
            <div style='background:rgba(99,179,237,0.05); border:1px solid rgba(99,179,237,0.1); border-radius:8px; padding:10px 14px; margin-bottom:6px;'>
                <div style='font-weight:600; color:#e8eaf0; font-size:0.88rem;'>{absence['employe']}</div>
                <div style='color:#7fb3d3; font-size:0.78rem;'>{absence['date']} · {absence['type']}</div>
                <div style='color:{couleur}; font-size:0.75rem; margin-top:3px;'>● {absence['statut']}</div>
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════
# TAB 4 — ALERTES
# ══════════════════════════════════════════════
with tab4:
    st.markdown("<div class='section-title'>⚠️ Alertes & Anticipation</div>", unsafe_allow_html=True)
    col_a1, col_a2 = st.columns([3, 2])
    with col_a1:
        st.markdown("<p style='color:#7fb3d3; font-size:0.82rem; margin-bottom:16px;'>Alertes actives nécessitant une action</p>", unsafe_allow_html=True)
        for alerte in ALERTES:
            css_class = "alerte-rouge" if alerte["niveau"] == "rouge" else "alerte-orange"
            icon = "🚨" if alerte["niveau"] == "rouge" else "⚠️"
            st.markdown(f"<div class='{css_class}'><div class='alerte-title'>{icon} {alerte['type']} — {alerte['semaine']}</div><div class='alerte-message'>{alerte['message']}</div></div>", unsafe_allow_html=True)
    with col_a2:
        st.markdown("<div class='section-title' style='font-size:1rem;'>📊 Prévision d'activité</div>", unsafe_allow_html=True)
        mois = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun', 'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
        charge = [75, 70, 90, 72, 68, 65, 60, 55, 78, 82, 88, 95]
        couleurs = ['rgba(252,129,129,0.7)' if c >= 85 else 'rgba(246,173,85,0.7)' if c >= 75 else 'rgba(99,179,237,0.7)' for c in charge]
        fig4 = go.Figure(go.Bar(x=mois, y=charge, marker_color=couleurs, marker_line_width=1))
        fig4.add_hline(y=85, line_dash="dash", line_color="rgba(252,129,129,0.6)", annotation_text="Seuil critique", annotation_font_color="#fc8181")
        fig4.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#7fb3d3'), margin=dict(l=20, r=20, t=20, b=20), height=250, xaxis=dict(gridcolor='rgba(99,179,237,0.1)'), yaxis=dict(gridcolor='rgba(99,179,237,0.1)', title=dict(text='Indice de charge', font=dict(color='#7fb3d3'))))
        st.plotly_chart(fig4, use_container_width=True)
        st.markdown("<div style='font-size:0.78rem; color:#4a6080; line-height:1.6;'>🔴 Rouge : surcharge critique (≥85)<br>🟠 Orange : charge élevée (≥75)<br>🔵 Bleu : activité normale</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════
# TAB 5 — CONFORMITÉ (nouveau)
# ══════════════════════════════════════════════
with tab5:
    st.markdown("<div class='section-title'>✅ Rapport de Conformité — Convention IDCC 1996</div>", unsafe_allow_html=True)

    r = rapport["rapport"]
    score_color_hex = "#68d391" if r["score_conformite"] >= 90 else "#f6ad55" if r["score_conformite"] >= 75 else "#fc8181"
    border_color = "rgba(104,211,145,0.4)" if r["score_conformite"] >= 90 else "rgba(246,173,85,0.4)" if r["score_conformite"] >= 75 else "rgba(252,129,129,0.4)"

    # Score global + compteurs
    col_score, col_stats = st.columns([1, 3])
    with col_score:
        st.markdown(f"""
        <div style='background: rgba(13,31,60,0.8); border: 2px solid {border_color};
             border-radius: 16px; padding: 30px 20px; text-align: center;'>
            <div style='font-family: DM Serif Display, serif; font-size: 3.5rem;
                 color: {score_color_hex}; line-height:1;'>{r["score_conformite"]}%</div>
            <div style='color:#7fb3d3; font-size:0.8rem; text-transform:uppercase;
                 letter-spacing:0.8px; margin-top:8px;'>Score de conformité</div>
            <div style='color:#4a6080; font-size:0.72rem; margin-top:6px;'>{r["date_analyse"]}</div>
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
        # Violations critiques
        if rapport["violations_critiques"]:
            st.markdown("<p style='color:#fc8181; font-weight:600; font-size:0.85rem; text-transform:uppercase; letter-spacing:0.8px;'>🔴 Violations Critiques</p>", unsafe_allow_html=True)
            for v in rapport["violations_critiques"]:
                st.markdown(f"""
                <div class='alerte-rouge'>
                    <div class='alerte-title'>{v['code']}</div>
                    <div class='alerte-message'>{v['message']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class='alerte-vert'>
                <div class='alerte-title'>✅ Aucune violation critique</div>
                <div class='alerte-message'>Toutes les règles obligatoires sont respectées.</div>
            </div>
            """, unsafe_allow_html=True)

        # Violations mineures
        if rapport["violations_mineures"]:
            st.markdown("<p style='color:#f6ad55; font-weight:600; font-size:0.85rem; text-transform:uppercase; letter-spacing:0.8px; margin-top:16px;'>🟠 Violations Mineures</p>", unsafe_allow_html=True)
            for v in rapport["violations_mineures"]:
                st.markdown(f"""
                <div class='alerte-orange'>
                    <div class='alerte-title'>{v['code']}</div>
                    <div class='alerte-message'>{v['message']}</div>
                </div>
                """, unsafe_allow_html=True)

    with col_v2:
        # Points conformes (résumé)
        st.markdown("<p style='color:#68d391; font-weight:600; font-size:0.85rem; text-transform:uppercase; letter-spacing:0.8px;'>✅ Points Conformes</p>", unsafe_allow_html=True)
        conformes_uniques = {}
        for v in rapport["points_conformes"]:
            code = v["code"]
            if code not in conformes_uniques:
                conformes_uniques[code] = {"message": v["message"], "count": 1}
            else:
                conformes_uniques[code]["count"] += 1

        for code, info in conformes_uniques.items():
            count_badge = f" <span style='color:#4a6080;'>×{info['count']}</span>" if info["count"] > 1 else ""
            st.markdown(f"""
            <div class='alerte-vert' style='padding: 10px 14px; margin-bottom: 6px;'>
                <div style='font-size:0.82rem; color:#68d391; font-weight:600;'>{code}{count_badge}</div>
                <div style='font-size:0.8rem; color:#c4d4e3; margin-top:2px;'>{info["message"]}</div>
            </div>
            """, unsafe_allow_html=True)

        # Graphique camembert violations vs conformes
        st.markdown("<div style='margin-top: 16px;'>", unsafe_allow_html=True)
        fig5 = go.Figure(data=[go.Pie(
            labels=['Conformes', 'Violations critiques', 'Violations mineures'],
            values=[r["conformes"], r["violations_critiques"], r["violations_mineures"]],
            hole=0.55,
            marker=dict(
                colors=['rgba(104,211,145,0.8)', 'rgba(252,129,129,0.8)', 'rgba(246,173,85,0.8)'],
                line=dict(color=['#68d391', '#fc8181', '#f6ad55'], width=2)
            ),
            textfont=dict(color='white', size=11)
        )])
        fig5.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#7fb3d3'), legend=dict(bgcolor='rgba(0,0,0,0)'),
            margin=dict(l=10, r=10, t=10, b=10), height=220,
            annotations=[dict(text='Bilan', x=0.5, y=0.5, font_size=14, font_color='#e8eaf0', showarrow=False)]
        )
        st.plotly_chart(fig5, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)