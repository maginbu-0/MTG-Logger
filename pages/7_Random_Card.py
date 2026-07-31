import streamlit as st
import requests
from datetime import datetime, timezone

st.subheader("🃏 Scryfall Card of the Day")

@st.cache_data(ttl=3600)
def fetch_daily_card(date_str: str):
    """
    Fetches a random card from Scryfall API with a custom User-Agent.
    Uses the current date string as the cache key so the same card
    is returned all day until 00:00 UTC triggers a new date key.
    """
    url = "https://api.scryfall.com/cards/random"
    headers = {
        "User-Agent": "MTGCommanderTracker/1.0 (Streamlit App)",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Resolve image URI (handling dual-faced cards like Flip/Transform commanders)
            image_url = None
            if "image_uris" in data:
                image_url = data["image_uris"].get("normal") or data["image_uris"].get("large")
            elif "card_faces" in data and "image_uris" in data["card_faces"][0]:
                image_url = data["card_faces"][0]["image_uris"].get("normal")

            # Resolve oracle text / description
            oracle_text = data.get("oracle_text", "")
            if not oracle_text and "card_faces" in data:
                oracle_text = "\n\n---\n\n".join([face.get("oracle_text", "") for face in data["card_faces"]])

            return {
                "success": True,
                "name": data.get("name", "Unknown Card"),
                "type_line": data.get("type_line", ""),
                "mana_cost": data.get("mana_cost", ""),
                "oracle_text": oracle_text,
                "flavor_text": data.get("flavor_text", ""),
                "artist": data.get("artist", ""),
                "set_name": data.get("set_name", ""),
                "image_url": image_url,
                "scryfall_uri": data.get("scryfall_uri", ""),
                "prices": data.get("prices", {}).get("usd", "N/A")
            }
        else:
            return {"success": False, "error": f"Scryfall HTTP {response.status_code}"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

# Current UTC date string for 00:00 UTC midnight rollover
today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

res = fetch_daily_card(today_str)

if not res or not res.get("success"):
    err_msg = res.get("error") if res else "Unknown error"
    st.error(f"⚠️ Failed to load Card of the Day from Scryfall API: {err_msg}")
else:
    st.caption(f"🗓️ Card for **{today_str}** (Rotates daily at 00:00 UTC)")
    
    col_img, col_info = st.columns([1, 1.2])
    
    with col_img:
        if res["image_url"]:
            st.image(res["image_url"], use_container_width=True)
        else:
            st.info("No card image available for this print.")

    with col_info:
        st.title(res["name"])
        st.markdown(f"**Mana Cost:** `{res['mana_cost']}`")
        st.markdown(f"**Type:** {res['type_line']}")
        st.markdown(f"**Set:** {res['set_name']}")
        st.markdown(f"**Est. Price (USD):** `${res['prices']}`")
        
        st.divider()
        st.markdown("#### 📜 Card Text / Description")
        st.info(res["oracle_text"] if res["oracle_text"] else "*No oracle text.*")
        
        if res["flavor_text"]:
            st.caption(f"*\"{res['flavor_text']}\"*")
            
        st.markdown(f"🎨 **Artist:** {res['artist']}")
        st.markdown(f"[View on Scryfall]({res['scryfall_uri']})")

    st.divider()
    if st.button("🔀 Test Random Fetch (Bypass Today's Cache)", type="secondary"):
        fetch_daily_card.clear()
        st.rerun()