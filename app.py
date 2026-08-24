import streamlit as st
import extra_streamlit_components as stx

st.set_page_config(
    page_title="EDH Tracker",
    page_icon="⚔️",
    layout="centered"
)

# Initialize Cookie Manager
cookie_manager = stx.CookieManager()

st.title("🛡️ Commander Tracker")

# --- PIN AUTHENTICATION (WITH COOKIE PERSISTENCE) ---
ADMIN_PIN = st.secrets.get("ADMIN_PIN", "1234")
LOGGER_PIN = st.secrets.get("LOGGER_PIN", "5678")

# Fetch saved role from browser cookie if session state is empty
saved_role_cookie = cookie_manager.get("edh_user_role")

if "user_role" not in st.session_state:
    if saved_role_cookie in ["Admin", "Logger"]:
        st.session_state.user_role = saved_role_cookie
    else:
        st.session_state.user_role = "Viewer"

with st.sidebar:
    st.header("🔒 Access Control")
    if st.session_state.user_role == "Viewer":
        entered_pin = st.text_input("Enter PIN to unlock features", type="password")
        if st.button("Unlock"):
            if entered_pin == ADMIN_PIN:
                st.session_state.user_role = "Admin"
                # Set cookie valid for 12 hours (43200 seconds)
                cookie_manager.set("edh_user_role", "Admin", max_age=43200, key="set_admin_cookie")
                st.toast("Unlocked Admin Access (Saved to Device)!", icon="🔑")
                st.rerun()
            elif entered_pin == LOGGER_PIN:
                st.session_state.user_role = "Logger"
                cookie_manager.set("edh_user_role", "Logger", max_age=43200, key="set_logger_cookie")
                st.toast("Unlocked Logger Access (Saved to Device)!", icon="⚔️")
                st.rerun()
            else:
                st.error("Invalid PIN")
    else:
        st.success(f"Current Role: **{st.session_state.user_role}**")
        if st.button("Lock / Log Out"):
            st.session_state.user_role = "Viewer"
            cookie_manager.delete("edh_user_role", key="delete_role_cookie")
            st.toast("Logged out and removed device key.", icon="🔒")
            st.rerun()

role = st.session_state.user_role

# Page definitions - ENSURE THESE FILENAMES MATCH YOUR EXACT GITHUB PAGE FILES
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