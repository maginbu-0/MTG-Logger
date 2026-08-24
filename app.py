import streamlit as st
import db

st.set_page_config(
    page_title="EDH Tracker",
    page_icon="⚔️",
    layout="centered"
)

# --- FORCE iOS WEBAPP MANIFEST TO PRESERVE DEVICE KEY ---
device_token = st.query_params.get("device_key") or st.query_params.get("session_token")

if device_token:
    # Injects apple-mobile-web-app-capable meta tag with the active token locked into start_url
    st.components.v1.html(
        f"""
        <script>
            let meta = document.createElement('meta');
            meta.name = 'apple-mobile-web-app-title';
            meta.content = 'Commander Tracker';
            document.getElementsByTagName('head')[0].appendChild(meta);

            let link = document.createElement('link');
            link.rel = 'manifest';
            link.href = 'data:application/manifest+json,' + encodeURIComponent(JSON.stringify({{
                "name": "Commander Tracker",
                "short_name": "EDH Tracker",
                "start_url": "/?device_key={device_token}",
                "display": "standalone"
            }}));
            document.getElementsByTagName('head')[0].appendChild(link);
        </script>
        """,
        height=0,
    )

st.title("🛡️ Commander Tracker")

# --- AUTHENTICATION (PIN + PERMANENT DEVICE KEY) ---
ADMIN_PIN = st.secrets.get("ADMIN_PIN", "1234")
LOGGER_PIN = st.secrets.get("LOGGER_PIN", "5678")

# Fetch persistent token from query params
device_token = st.query_params.get("device_key") or st.query_params.get("session_token")

# Restore role from Supabase DB on load or refresh
if "user_role" not in st.session_state:
    verified_role = db.verify_device_session(device_token) if device_token else None
    if verified_role in ["Admin", "Logger"]:
        st.session_state.user_role = verified_role
    else:
        st.session_state.user_role = "Viewer"

with st.sidebar:
    st.header("🔒 Access Control")
    if st.session_state.user_role == "Viewer":
        entered_pin = st.text_input("Enter PIN to unlock features", type="password")
        if st.button("Unlock"):
            target_role = None
            if entered_pin == ADMIN_PIN:
                target_role = "Admin"
            elif entered_pin == LOGGER_PIN:
                target_role = "Logger"
            else:
                st.error("Invalid PIN")

            if target_role:
                new_token = db.create_device_session(target_role)
                st.session_state.user_role = target_role
                st.query_params["device_key"] = new_token
                st.toast(f"Unlocked {target_role} Access!", icon="🔑")
                st.rerun()
    else:
        st.success(f"Current Role: **{st.session_state.user_role}**")
        if st.button("Lock / Log Out"):
            if device_token:
                db.revoke_device_session(device_token)
            st.session_state.user_role = "Viewer"
            st.query_params.clear()
            st.toast("Logged out!", icon="🔒")
            st.rerun()

role = st.session_state.user_role

# Page definitions
analytics_page = st.Page("pages/4_Analytics.py", title="Analytics", icon="📊")
log_page = st.Page("pages/1_Log_Match.py", title="Log Match", icon="⚔️")
add_deck_page = st.Page("pages/2_Add_Deck.py", title="Add Deck", icon="➕")
recap_page = st.Page("pages/3_Daily_Recap.py", title="Daily Recap", icon="📋")
deck_admin_page = st.Page("pages/5_Deck_Admin.py", title="Deck & Player Admin", icon="🛠️")
match_admin_page = st.Page("pages/6_Match_Admin.py", title="Match Admin", icon="✏️")
random_card_page = st.Page("pages/7_Random_Card.py", title="Random Card of the Day", icon="🎲")
monthly_recap_page = st.Page("pages/8_Monthly_Recap.py", title="Monthly Recap", icon="🏆")

if role == "Admin":
    pg = st.navigation([analytics_page, log_page, add_deck_page, recap_page, deck_admin_page, match_admin_page, random_card_page, monthly_recap_page])
elif role == "Logger":
    pg = st.navigation([analytics_page, log_page, add_deck_page, recap_page, random_card_page, monthly_recap_page])
else:
    st.info("ℹ️ You are in Read-Only mode. Enter a PIN in the sidebar to log games or add decks.")
    pg = st.navigation([analytics_page, recap_page, random_card_page, monthly_recap_page])

pg.run()