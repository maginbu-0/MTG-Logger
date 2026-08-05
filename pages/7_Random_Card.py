import streamlit as st
import requests
import re
from datetime import datetime, timezone
import db

st.subheader("🃏 Scryfall Card of the Day")

def format_mana_symbols(text: str) -> str:
    if not text:
        return ""
    def symbol_replacer(match):
        raw_symbol = match.group(1).replace("/", "")
        svg_url = f"https://svgs.scryfall.io/card-symbols/{raw_symbol.upper()}.svg"
        return (
            f'<img src="{svg_url}" '
            f'style="height: 1.1em; width: 1.1em; vertical-align: -0.15em; margin: 0 1px; display: inline-block;" '
            f'alt="{{{raw_symbol}}}"/>'
        )
    return re.sub(r'\{([A-Za-z0-9/]+)\}', symbol_replacer, text)

def parse_scryfall_payload(data):
    image_url = None
    if "image_uris" in data:
        image_url = data["image_uris"].get("normal") or data["image_uris"].get("large")
    elif "card_faces" in data and "image_uris" in data["card_faces"][0]:
        image_url = data["card_faces"][0]["image_uris"].get("normal")

    oracle_text = data.get("oracle_text", "")
    if not oracle_text and "card_faces" in data:
        oracle_text = "\n\n---\n\n".join([f.get("oracle_text", "") for f in data["card_faces"] if f.get("oracle_text")])

    type_line = data.get("type_line", "")
    if not type_line and "card_faces" in data:
        type_line = " // ".join([f.get("type_line", "") for f in data["card_faces"] if f.get("type_line")])

    artist = data.get("artist", "")
    if not artist and "card_faces" in data:
        artist = " / ".join([f.get("artist", "") for f in data["card_faces"] if f.get("artist")])

    set_name = data.get("set_name") or data.get("set", "").upper()
    prices = data.get("prices", {})
    usd_price = prices.get("usd") or prices.get("usd_foil") or "N/A"

    return {
        "name": data.get("name", "Unknown Card"),
        "type_line": type_line if type_line else "N/A",
        "mana_cost": data.get("mana_cost", ""),
        "oracle_text": oracle_text if oracle_text else "*No card text.*",
        "flavor_text": data.get("flavor_text", ""),
        "artist": artist if artist else "Unknown Artist",
        "set_name": set_name if set_name else "N/A",
        "image_url": image_url,
        "scryfall_uri": data.get("scryfall_uri", "https://scryfall.com"),
        "prices": usd_price
    }

def get_or_fetch_daily_card():
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    cached_card = db.fetch_daily_card_from_db(today_str)
    if cached_card and isinstance(cached_card, dict):
        if not cached_card.get("date"): cached_card["date"] = today_str
        if not cached_card.get("source"): cached_card["source"] = "Supabase DB"
        return {"success": True, "card": cached_card}

    url = "https://api.scryfall.com/cards/random"
    headers = {
        "User-Agent": "MTGCommanderTracker/1.0 (Streamlit App)",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            card_payload = parse_scryfall_payload(data)
            db.save_daily_card_to_db(today_str, card_payload)
            card_payload["date"] = today_str
            card_payload["source"] = "Scryfall API (Fresh)"
            return {"success": True, "card": card_payload}
        else:
            return {"success": False, "error": f"Scryfall HTTP {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@st.fragment
def render_daily_card_fragment():
    res = get_or_fetch_daily_card()

    if not res or not res.get("success"):
        err_msg = res.get("error", "Unknown error")
        st.error(f"⚠️ Failed to load Card of the Day: {err_msg}")
    else:
        card = res["card"]
        date_display = card.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        source_display = card.get("source", "Supabase DB")
        
        st.caption(f"🗓️ Fixed Card for **{date_display}** (Rotates daily at 00:00 UTC | Source: {source_display})")
        
        col_img, col_info = st.columns([1, 1.2])
        
        with col_img:
            if card.get("image_url"):
                st.image(card["image_url"], use_container_width=True)
            else:
                st.info("No card image available for this print.")

        with col_info:
            st.title(card.get("name", "Unknown Card"))
            
            formatted_cost = format_mana_symbols(card.get("mana_cost", ""))
            st.markdown(f"**Mana Cost:** {formatted_cost}", unsafe_allow_html=True)
            st.markdown(f"**Type:** {card.get('type_line', 'N/A')}")
            st.markdown(f"**Set:** {card.get('set_name', 'N/A')}")
            st.markdown(f"**Est. Price (USD):** `${card.get('prices', 'N/A')}`")
            
            st.divider()
            st.markdown("#### 📜 Card Text / Description")
            
            formatted_oracle = format_mana_symbols(card.get("oracle_text", "*No oracle text.*"))
            st.markdown(
                f'<div style="background-color: #1e293b; padding: 15px; border-radius: 8px; line-height: 1.6; border: 1px solid #334155;">'
                f'{formatted_oracle}'
                f'</div>',
                unsafe_allow_html=True
            )
            
            if card.get("flavor_text"):
                st.caption(f"*\"{card['flavor_text']}\"*")
                
            st.markdown(f"🎨 **Artist:** {card.get('artist', 'Unknown')}")
            st.markdown(f"[View on Scryfall]({card.get('scryfall_uri', '#')})")

        st.divider()
        if st.button("🔄 Clear Today's DB Cache & Fetch New Card", type="secondary"):
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            db.save_daily_card_to_db(today_str, {})
            st.toast("Cleared DB cache for today!", icon="🧹")
            st.rerun()

render_daily_card_fragment()