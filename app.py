import streamlit as st
import db

st.set_page_config(
    page_title="EDH Tracker",
    page_icon="⚔️",
    layout="centered"
)

st.title("🛡️ Commander Tracker")

# --- AUTHENTICATION (MAGIC LINK OR MANUAL PIN) ---
device_token = st.query_params.get("device_key") or st.query_params.get("session_token")

# 1. Restore role & username from Supabase DB on load or refresh
if "user_role" not in st.session_state:
    session_data = db.verify_device_session(device_token) if device_token else None
    if session_data and session_data.get("user_role") in ["Admin", "Logger"]:
        st.session_state.user_role = session_data["user_role"]
        st.session_state.user_name = session_data.get("user_name", "User")
    else:
        st.session_state.user_role = "Viewer"
        st.session_state.user_name = "Viewer"

with st.sidebar:
    st.header("🔒 Access Control")
    if st.session_state.user_role == "Viewer":
        available_users = db.fetch_all_active_usernames()
        
        if available_users:
            selected_user = st.selectbox("Select User", options=available_users)
        else:
            selected_user = st.text_input("Username")

        entered_pin = st.text_input("Enter PIN", type="password")
        
        if st.button("Unlock"):
            # Verify against app_users table
            user_info = db.verify_user_credentials(selected_user, entered_pin)
            if user_info:
                target_role = user_info["user_role"]
                target_name = user_info["user_name"]
                
                # Create persistent session in user_sessions mapped to app_users row
                new_token = db.create_session_for_user(target_name)
                
                st.session_state.user_role = target_role
                st.session_state.user_name = target_name
                if new_token:
                    st.query_params["device_key"] = new_token
                
                st.toast(f"Welcome back, {target_name}!", icon="🔑")
                st.rerun()
            else:
                st.error("Invalid Username or PIN")
    else:
        st.success(f"Logged in as: **{st.session_state.user_name}** ({st.session_state.user_role})")
        if device_token:
            st.caption("📱 **Bookmark your shortcut link:**")
            st.code(f"https://edh-logger.streamlit.app/?device_key={device_token}", language="text")

        if st.button("Lock / Log Out"):
            if device_token:
                db.revoke_device_session(device_token)
            st.session_state.user_role = "Viewer"
            st.session_state.user_name = "Viewer"
            st.query_params.clear()
            st.toast("Logged out!", icon="🔒")
            st.rerun()

role = st.session_state.user_role

# Page definitions
log_page = st.Page("pages/1_Log_Match.py", title="Log Match", icon="⚔️")
analytics_page = st.Page("pages/4_Analytics.py", title="Analytics", icon="📊")
add_deck_page = st.Page("pages/2_Add_Deck.py", title="Add Deck", icon="➕")
recap_page = st.Page("pages/3_Daily_Recap.py", title="Daily Recap", icon="📋")
deck_admin_page = st.Page("pages/5_Deck_Admin.py", title="Deck & Player Admin", icon="🛠️")
match_admin_page = st.Page("pages/6_Match_Admin.py", title="Match Admin", icon="✏️")
random_card_page = st.Page("pages/7_Random_Card.py", title="Random Card of the Day", icon="🎲")
monthly_recap_page = st.Page("pages/8_Monthly_Recap.py", title="Monthly Recap", icon="🏆")

if role == "Admin":
    pg = st.navigation([log_page, analytics_page, add_deck_page, recap_page, deck_admin_page, match_admin_page, random_card_page, monthly_recap_page])
elif role == "Logger":
    pg = st.navigation([log_page, analytics_page, add_deck_page, recap_page, random_card_page, monthly_recap_page])
else:
    st.info("ℹ️ You are in Read-Only mode. Select your username and enter your PIN in the sidebar to log games.")
    pg = st.navigation([analytics_page, recap_page, random_card_page, monthly_recap_page])

pg.run()