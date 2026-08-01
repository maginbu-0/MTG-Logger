import streamlit as st
import requests
from datetime import datetime, timezone
import db

st.subheader("🃏 Scryfall Card of the Day")

def get_or_fetch_daily_card():
    """
    1. Checks Supabase for today's card (YYYY-MM-DD UTC).
    2. If found, returns the exact stored card.
    3. If missing (first visit after 00:00 UTC), fetches a random card from Scryfall,
       saves it to Supabase, and serves it for the rest of the day.
    """
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # 1. Try DB first
    cached_card = db.fetch_daily_card_from_db(today_str)
    if cached_card:
        cached_card["date"] = today_str
        cached_card["source"] = "Supabase DB"
        return {"success": True, "card": cached_card}

    # 2. Not in DB yet — fetch a fresh random card from Scryfall
    url = "https://api.scryfall.com/cards/random"
    headers = {
        "User-Agent": "MTGCommanderTracker/1.0 (Streamlit App)",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            # Resolve image URI (handles single and dual-faced cards)
            image_url = None
            if "image_uris" in data:
                image_url = data["image_uris"].get("normal") or data["image_uris"].get("large")
            elif "card_faces" in data and "image_uris" in data["card_faces"][0]:
                image_url = data["card_faces"][0]["image_uris"].get("normal")

            # Resolve oracle text
            oracle_text = data.get("oracle_text", "")
            if not oracle_text and "card_faces" in data:
                oracle_text = "\n\n---\n\n".join([f.get("oracle_text", "") for f in data["card_faces"]])

            card_payload = {
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
            
            # Save to Supabase so all users & sessions get this exact card today
            db.save_daily_card_to_db(today_str, card_payload)
            
            card_payload["date"] = today_str
            card_payload["source"] = "Scryfall API (Fresh)"
            return {"success": True, "card": card_payload}
            
        else:
            return {"success": False, "error": f"Scryfall HTTP {response.status_code}"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

res = get_or_fetch_daily_card()

if not res or not res.get("success"):
    err_msg = res.get("error", "Unknown error")
    st.error(f"⚠️ Failed to load Card of the Day: {err_msg}")
else:
    card = res["card"]
    st.caption(f"🗓️ Fixed Card for ** (Rotates daily at 00:00 UTC | Source: {card['source']})")
    
    col_img, col_info = st.columns([1, 1.2])
    
    with col_img:
        if card["image_url"]:
            st.image(card["image_url"], use_container_width=True)
        else:
            st.info("No card image available for this print.")

    with col_info:
        st.title(card["name"])
        st.markdown(f"**Mana Cost:** `{card['mana_cost']}`")
        st.markdown(f"Type:")
        st.markdown(f"Set:")
        st.markdown(f"**Est. Price (USD):** `${card['prices']}`")
        
        st.divider()
        st.markdown("#### 📜 Card Text / Description")
        st.info(card["oracle_text"] if card["oracle_text"] else "*No oracle text.*")
        
        if card["flavor_text"]:
            st.caption(f"*\"{card['flavor_text']}\"*")
            
        st.markdown(f"🎨 Artist:")
        st.markdown(f"[View on Scryfall]({card['scryfall_uri']})")