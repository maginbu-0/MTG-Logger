import streamlit as st

st.set_page_config(
    page_title="EDH Tracker",
    page_icon="⚔️",
    layout="centered"
)

st.title("🛡️ Commander Tracker")

# --- PIN AUTHENTICATION (SIDEBAR) ---
ADMIN_PIN = st.secrets.get("ADMIN_PIN", "1234")
LOGGER_PIN = st.secrets.get("LOGGER_PIN", "5678")

if "user_role" not in st.session_state:
    st.session_state.user_role = "Viewer"

with st.sidebar:
    st.header("🔒 Access Control")
    
    if st.session_state.user_role == "Viewer":
        entered_pin = st.text_input("Enter PIN to unlock features", type="password")
        if st.button("Unlock"):
            if entered_pin == ADMIN_PIN:
                st.session_state.user_role = "Admin"
                st.toast("Unlocked Admin Access!", icon="🔑")
                st.rerun()
            elif entered_pin == LOGGER_PIN:
                st.session_state.user_role = "Logger"
                st.toast("Unlocked Logger Access!", icon="⚔️")
                st.rerun()
            else:
                st.error("Invalid PIN")
    else:
        st.success(f"Current Role: **{st.session_state.user_role}**")
        if st.button("Lock / Log Out"):
            st.session_state.user_role = "Viewer"
            st.rerun()

# --- PAGE ROUTING BASED ON ROLE ---
role = st.session_state.user_role

log_page = st.Page("pages/1_Log_Match.py", title="Log Match", icon="⚔️")
add_deck_page = st.Page("pages/2_Add_Deck.py", title="Add Deck", icon="➕")
recap_page = st.Page("pages/3_Daily_Recap.py", title="Daily Recap", icon="📋")
analytics_page = st.Page("pages/4_Analytics.py", title="Analytics", icon="📊")
deck_admin_page = st.Page("pages/5_Deck_Admin.py", title="Deck & Player Admin", icon="🛠️")
match_admin_page = st.Page("pages/6_Match_Admin.py", title="Match Admin", icon="✏️")

if role == "Admin":
    pg = st.navigation([log_page, add_deck_page, recap_page, analytics_page, deck_admin_page, match_admin_page])
elif role == "Logger":
    pg = st.navigation([log_page, add_deck_page, recap_page, analytics_page])
else:
    st.info("ℹ️ You are in Read-Only mode. Enter a PIN in the sidebar to log games or add decks.")
    pg = st.navigation([recap_page, analytics_page])

pg.run()