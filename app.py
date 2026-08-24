import streamlit as st
import db

st.set_page_config(
    page_title="EDH Tracker",
    page_icon="⚔️",
    layout="centered"
)

# --- JAVASCRIPT LOCALSTORAGE PERSISTENCE BRIDGE ---
# Intercepts mobile/desktop reloads and syncs localStorage token to Streamlit query params
st.components.v1.html(
    """
    <script>
        (function() {
            const STORAGE_KEY = 'edh_tracker_session_token';
            const urlParams = new URLSearchParams(window.parent.location.search);
            const urlToken = urlParams.get('session_token');
            const localToken = localStorage.getItem(STORAGE_KEY);

            // 1. If stored token exists on phone/PC but missing from URL (e.g. fresh refresh/PWA launch)
            if (localToken && !urlToken) {
                urlParams.set('session_token', localToken);
                window.parent.location.search = urlParams.toString();
            }
            // 2. If token present in URL, ensure device localStorage matches
            else if (urlToken && urlToken !== localToken) {
                localStorage.setItem(STORAGE_KEY, urlToken);
            }
        })();
    </script>
    """,
    height=0,
)

st.title("🛡️ Commander Tracker")

# --- PIN AUTHENTICATION (SUPABASE + DEVICE LOCALSTORAGE) ---
ADMIN_PIN = st.secrets.get("ADMIN_PIN", "1234")
LOGGER_PIN = st.secrets.get("LOGGER_PIN", "5678")

# Fetch persistent device token (restored via JS bridge above)
device_token = st.query_params.get("session_token", None)

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
                # 1. Generate persistent session in Supabase
                new_token = db.create_device_session(target_role)
                st.session_state.user_role = target_role
                st.query_params["session_token"] = new_token
                
                # 2. Save token into phone/PC permanent localStorage
                st.components.v1.html(
                    f"""
                    <script>
                        localStorage.setItem('edh_tracker_session_token', '{new_token}');
                    </script>
                    """,
                    height=0,
                )
                st.toast(f"Unlocked {target_role} Access (Saved to Device)!", icon="🔑")
                st.rerun()
    else:
        st.success(f"Current Role: **{st.session_state.user_role}**")
        if st.button("Lock / Log Out"):
            if device_token:
                db.revoke_device_session(device_token)
            st.session_state.user_role = "Viewer"
            if "session_token" in st.query_params:
                del st.query_params["session_token"]
            
            # Wipe token from device storage
            st.components.v1.html(
                """
                <script>
                    localStorage.removeItem('edh_tracker_session_token');
                </script>
                """,
                height=0,
            )
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