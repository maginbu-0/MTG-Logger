import streamlit as st
from streamlit_cookies_controller import CookieController
import db

st.set_page_config(
    page_title="EDH Tracker",
    page_icon="⚔️",
    layout="centered"
)

# Initialize Client-Side Cookie Controller
controller = CookieController()

st.title("🛡️ Commander Tracker")

# --- PIN AUTHENTICATION (TRUE COOKIE PERSISTENCE) ---
ADMIN_PIN = st.secrets.get("ADMIN_PIN", "1234")
LOGGER_PIN = st.secrets.get("LOGGER_PIN", "5678")

# 1. Fetch persistent cookie token directly from mobile browser
device_token = controller.get("edh_session_token")

# 2. Restore session state from Supabase if uninitialized
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
                # Create token in Supabase
                new_token = db.create_device_session(target_role)
                st.session_state.user_role = target_role
                
                # Write 30-day persistent cookie directly to device storage
                controller.set("edh_session_token", new_token, max_age=2592000)
                st.toast(f"Unlocked {target_role} Access (Saved to Device)!", icon="🔑")
                st.rerun()
    else:
        st.success(f"Current Role: **{st.session_state.user_role}**")
        if st.button("Lock / Log Out"):
            if device_token:
                db.revoke_device_session(device_token)
            st.session_state.user_role = "Viewer"
            controller.remove("edh_session_token")
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