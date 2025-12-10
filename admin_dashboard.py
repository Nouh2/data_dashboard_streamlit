"""
Streamlit Admin Dashboard - Gaia Chat Database Explorer
=========================================================
Interface administrative pour consulter les utilisateurs et conversations
dans la base de données Cosmos DB.
"""

import streamlit as st
from azure.cosmos import CosmosClient
import pandas as pd
from datetime import datetime
import json
import io

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Gaia Admin Dashboard",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Styles CSS personnalisés
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #3F612D;
        margin-bottom: 1rem;
    }
    .stat-card {
        background: linear-gradient(135deg, #3F612D 0%, #5a8a3d 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .stat-number {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0.5rem 0;
    }
    .stat-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    .conversation-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #3F612D;
        margin-bottom: 1rem;
    }
    .user-message {
        background: #e3f2fd;
        padding: 0.8rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    .ai-message {
        background: #f1f8e9;
        padding: 0.8rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    .stExpander {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Connexion à Cosmos DB
@st.cache_resource
def get_cosmos_client():
    """Initialise et retourne le client Cosmos DB"""
    # Lire depuis les secrets Streamlit (requis pour le déploiement)
    # En local: créer .streamlit/secrets.toml
    # Sur Streamlit Cloud: configurer dans les paramètres de l'app
    connection_string = st.secrets["cosmos"]["connection_string"]
    
    client = CosmosClient.from_connection_string(connection_string)
    database = client.get_database_client("AuthDB")
    return {
        'users': database.get_container_client("users"),
        'conversations': database.get_container_client("conversations")
    }

@st.cache_data(ttl=60)
def load_users():
    """Charge tous les utilisateurs"""
    containers = get_cosmos_client()
    users_container = containers['users']
    
    query = "SELECT * FROM c"
    users = list(users_container.query_items(query=query, enable_cross_partition_query=True))
    return users

@st.cache_data(ttl=60)
def load_conversations():
    """Charge toutes les conversations"""
    containers = get_cosmos_client()
    conversations_container = containers['conversations']
    
    query = "SELECT * FROM c ORDER BY c.createdAt DESC"
    conversations = list(conversations_container.query_items(query=query, enable_cross_partition_query=True))
    return conversations

def get_user_conversations(user_id):
    """Récupère les conversations d'un utilisateur spécifique"""
    containers = get_cosmos_client()
    conversations_container = containers['conversations']
    
    query = "SELECT * FROM c WHERE c.userId = @userId ORDER BY c.createdAt DESC"
    parameters = [{"name": "@userId", "value": user_id}]
    
    conversations = list(conversations_container.query_items(
        query=query,
        parameters=parameters,
        enable_cross_partition_query=True
    ))
    return conversations

def format_date(iso_date):
    """Formate une date ISO en format lisible"""
    try:
        dt = datetime.fromisoformat(iso_date.replace('Z', '+00:00'))
        return dt.strftime("%d/%m/%Y %H:%M")
    except:
        return iso_date

def display_message(message, index, conversation_id=""):
    """Affiche un message de conversation"""
    content = message.get('content', 'N/A')
    
    if message.get('isUser', False):
        # Message utilisateur - fond bleu
        with st.container():
            st.markdown("**👤 Utilisateur:**")
            st.info(content)
    else:
        # Message IA - fond vert
        with st.container():
            if len(content) > 500:
                st.markdown(f"**🤖 IA (Réponse longue - {len(content)} caractères):**")
                st.text_area(
                    label=f"Message {index}",
                    value=content,
                    height=200,
                    disabled=True,
                    label_visibility="collapsed",
                    key=f"msg_{conversation_id}_{index}_{hash(content)}"
                )
            else:
                st.markdown("**🤖 IA:**")
                st.success(content)

# ===== Interface principale =====
st.markdown('<h1 class="main-header">🌿 Gaia Admin Dashboard</h1>', unsafe_allow_html=True)

# Barre latérale de navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Aller à", ["📊 Vue d'ensemble", "👥 Utilisateurs", "💬 Conversations", "🔍 Recherche"])

# Bouton de rafraîchissement
if st.sidebar.button("🔄 Rafraîchir les données"):
    st.cache_data.clear()
    st.rerun()

# ===== PAGE: VUE D'ENSEMBLE =====
if page == "📊 Vue d'ensemble":
    st.header("📊 Statistiques Générales")
    
    try:
        users = load_users()
        conversations = load_conversations()
        
        # Statistiques en colonnes
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">Total Utilisateurs</div>
                <div class="stat-number">{len(users)}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            verified_users = sum(1 for u in users if u.get('is_verified', False))
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">Utilisateurs Vérifiés</div>
                <div class="stat-number">{verified_users}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">Total Conversations</div>
                <div class="stat-number">{len(conversations)}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            total_messages = sum(len(c.get('messages', [])) for c in conversations)
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">Total Messages</div>
                <div class="stat-number">{total_messages}</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Répartition des plans
        st.subheader("📈 Répartition des Plans")
        plan_counts = {}
        for user in users:
            plan = user.get('plan', 'unknown')
            plan_counts[plan] = plan_counts.get(plan, 0) + 1
        
        plan_df = pd.DataFrame(list(plan_counts.items()), columns=['Plan', 'Nombre'])
        st.bar_chart(plan_df.set_index('Plan'))
        
        # Conversations récentes
        st.subheader("💬 Conversations Récentes (10 dernières)")
        recent_conversations = sorted(conversations, key=lambda x: x.get('createdAt', ''), reverse=True)[:10]
        
        for conv in recent_conversations:
            title = conv.get('title', 'Sans titre')
            created_at = format_date(conv.get('createdAt', 'N/A'))
            message_count = len(conv.get('messages', []))
            user_id_short = conv.get('userId', 'N/A')[:12]
            
            with st.container():
                st.markdown(f"**💬 {title}**")
                st.caption(f"📅 {created_at} | 💬 {message_count} messages | 👤 User ID: {user_id_short}...")
                st.markdown("---")
        
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement des données: {str(e)}")

# ===== PAGE: UTILISATEURS =====
elif page == "👥 Utilisateurs":
    st.header("👥 Gestion des Utilisateurs")
    
    try:
        users = load_users()
        
        # Filtres
        col1, col2 = st.columns(2)
        with col1:
            filter_plan = st.selectbox("Filtrer par plan", ["Tous"] + list(set(u.get('plan', 'unknown') for u in users)))
        with col2:
            filter_verified = st.selectbox("Statut de vérification", ["Tous", "Vérifiés", "Non vérifiés"])
        
        # Appliquer les filtres
        filtered_users = users
        if filter_plan != "Tous":
            filtered_users = [u for u in filtered_users if u.get('plan') == filter_plan]
        if filter_verified == "Vérifiés":
            filtered_users = [u for u in filtered_users if u.get('is_verified', False)]
        elif filter_verified == "Non vérifiés":
            filtered_users = [u for u in filtered_users if not u.get('is_verified', False)]
        
        st.info(f"📊 {len(filtered_users)} utilisateur(s) affiché(s)")
        
        # Export Excel
        st.subheader("📥 Exporter les données")
        col_export1, col_export2 = st.columns(2)
        
        with col_export1:
            # Préparer les données pour l'export
            export_data = []
            for user in filtered_users:
                export_data.append({
                    'Email': user.get('email', 'N/A'),
                    'Plan': user.get('plan', 'N/A'),
                    'Prénom': user.get('firstName', 'N/A'),
                    'Nom': user.get('lastName', 'N/A'),
                    'Vérifié': 'Oui' if user.get('is_verified', False) else 'Non',
                    'Créé le': user.get('createdAt', 'N/A'),
                    'Requêtes quotidiennes': user.get('daily_requests', 0)
                })
            
            df_export = pd.DataFrame(export_data)
            
            # Créer le fichier Excel en mémoire
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_export.to_excel(writer, index=False, sheet_name='Utilisateurs')
            buffer.seek(0)
            
            st.download_button(
                label="📊 Télécharger Excel (Complet)",
                data=buffer,
                file_name="gaia_utilisateurs.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        with col_export2:
            # Export simplifié (email + plan seulement)
            simple_data = [{'Email': user.get('email', 'N/A'), 'Plan': user.get('plan', 'N/A')} for user in filtered_users]
            df_simple = pd.DataFrame(simple_data)
            
            buffer_simple = io.BytesIO()
            with pd.ExcelWriter(buffer_simple, engine='openpyxl') as writer:
                df_simple.to_excel(writer, index=False, sheet_name='Emails_Plans')
            buffer_simple.seek(0)
            
            st.download_button(
                label="📧 Télécharger Excel (Email + Plan)",
                data=buffer_simple,
                file_name="gaia_emails_plans.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        st.markdown("---")
        
        # Tableau des utilisateurs
        for user in filtered_users:
            with st.expander(f"📧 {user.get('email', 'N/A')} - Plan: {user.get('plan', 'N/A').upper()}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Informations générales:**")
                    st.write(f"- **ID:** `{user.get('id', 'N/A')}`")
                    st.write(f"- **Email:** {user.get('email', 'N/A')}")
                    st.write(f"- **Prénom:** {user.get('firstName', 'N/A')}")
                    st.write(f"- **Nom:** {user.get('lastName', 'N/A')}")
                    st.write(f"- **Plan:** {user.get('plan', 'N/A')}")
                    st.write(f"- **Vérifié:** {'✅ Oui' if user.get('is_verified', False) else '❌ Non'}")
                    st.write(f"- **Suspendu:** {'⚠️ Oui' if user.get('isSuspended', False) else '✅ Non'}")
                
                with col2:
                    st.write("**Informations de compte:**")
                    st.write(f"- **Créé le:** {format_date(user.get('createdAt', 'N/A'))}")
                    st.write(f"- **Expire le:** {format_date(user.get('accountExpiresAt', 'N/A'))}")
                    st.write(f"- **Requêtes quotidiennes:** {user.get('daily_requests', 0)}")
                    st.write(f"- **Dernière requête:** {user.get('last_request_date', 'N/A')}")
                    st.write(f"- **Stripe ID:** {user.get('stripe_customer_id', 'N/A') or 'Aucun'}")
                
                # Afficher les conversations de cet utilisateur
                user_conversations = get_user_conversations(user.get('id'))
                st.write(f"**💬 Conversations: {len(user_conversations)}**")
                
                if user_conversations:
                    for conv in user_conversations[:5]:  # Limiter à 5 conversations
                        st.write(f"- {conv.get('title', 'Sans titre')} ({len(conv.get('messages', []))} messages) - {format_date(conv.get('createdAt', 'N/A'))}")
                    
                    if len(user_conversations) > 5:
                        st.write(f"... et {len(user_conversations) - 5} autres conversations")
                else:
                    st.write("_Aucune conversation_")
    
    except Exception as e:
        st.error(f"❌ Erreur: {str(e)}")

# ===== PAGE: CONVERSATIONS =====
elif page == "💬 Conversations":
    st.header("💬 Toutes les Conversations")
    
    try:
        conversations = load_conversations()
        
        # Filtres
        col1, col2 = st.columns(2)
        with col1:
            search_term = st.text_input("🔍 Rechercher dans les titres", "")
        with col2:
            min_messages = st.number_input("Nombre minimum de messages", min_value=0, value=0)
        
        # Appliquer les filtres
        filtered_convs = conversations
        if search_term:
            filtered_convs = [c for c in filtered_convs if search_term.lower() in c.get('title', '').lower()]
        if min_messages > 0:
            filtered_convs = [c for c in filtered_convs if len(c.get('messages', [])) >= min_messages]
        
        st.info(f"📊 {len(filtered_convs)} conversation(s) affichée(s)")
        
        # Afficher les conversations
        for conv in filtered_convs:
            title = conv.get('title', 'Sans titre')
            created_at = format_date(conv.get('createdAt', 'N/A'))
            updated_at = format_date(conv.get('updatedAt', 'N/A'))
            messages = conv.get('messages', [])
            
            with st.expander(f"💬 {title} ({len(messages)} messages) - {created_at}"):
                st.write(f"**ID Conversation:** `{conv.get('id', 'N/A')}`")
                st.write(f"**ID Utilisateur:** `{conv.get('userId', 'N/A')}`")
                st.write(f"**Créée le:** {created_at}")
                st.write(f"**Mise à jour le:** {updated_at}")
                
                st.markdown("---")
                st.write("**📜 Messages:**")
                
                for idx, message in enumerate(messages):
                    display_message(message, idx, conv.get('id', 'unknown'))
                
                # Option pour exporter la conversation
                if st.button(f"📥 Exporter JSON", key=f"export_{conv.get('id')}"):
                    st.json(conv)
    
    except Exception as e:
        st.error(f"❌ Erreur: {str(e)}")

# ===== PAGE: RECHERCHE =====
elif page == "🔍 Recherche":
    st.header("🔍 Recherche Avancée")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Rechercher un utilisateur")
        search_email = st.text_input("Par email", "")
        search_user_id = st.text_input("Par ID utilisateur", "")
        
        if st.button("🔍 Rechercher utilisateur"):
            try:
                users = load_users()
                results = []
                
                if search_email:
                    results = [u for u in users if search_email.lower() in u.get('email', '').lower()]
                elif search_user_id:
                    results = [u for u in users if u.get('id') == search_user_id]
                
                if results:
                    st.success(f"✅ {len(results)} résultat(s) trouvé(s)")
                    for user in results:
                        st.json(user)
                else:
                    st.warning("⚠️ Aucun résultat")
            except Exception as e:
                st.error(f"❌ Erreur: {str(e)}")
    
    with col2:
        st.subheader("Rechercher une conversation")
        search_conv_id = st.text_input("Par ID conversation", "")
        search_keyword = st.text_input("Par mot-clé dans le contenu", "")
        
        if st.button("🔍 Rechercher conversation"):
            try:
                conversations = load_conversations()
                results = []
                
                if search_conv_id:
                    results = [c for c in conversations if c.get('id') == search_conv_id]
                elif search_keyword:
                    for conv in conversations:
                        messages = conv.get('messages', [])
                        for msg in messages:
                            if search_keyword.lower() in msg.get('content', '').lower():
                                results.append(conv)
                                break
                
                if results:
                    st.success(f"✅ {len(results)} résultat(s) trouvé(s)")
                    for conv in results:
                        with st.expander(f"💬 {conv.get('title', 'Sans titre')}"):
                            st.json(conv)
                else:
                    st.warning("⚠️ Aucun résultat")
            except Exception as e:
                st.error(f"❌ Erreur: {str(e)}")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem 0;">
    <small>🌿 Gaia Admin Dashboard | Cosmos DB Explorer</small>
</div>
""", unsafe_allow_html=True)
