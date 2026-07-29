# 🛡️ Commander Tracker

A lightweight, mobile-responsive web application built with **Streamlit**, **Python**, and **Supabase (PostgreSQL)** to log, track, and analyze Magic: The Gathering (EDH/Commander) match stats across your playgroup.

---

## ✨ Features

- **Match Logging:** Easily record game details including total turns, game duration, win condition, seat positions, mulligan counts, and match winners.
- **Deck Management:** Import decklists and commanders directly via Moxfield URLs or add custom decks manually.
- **Playgroup Analytics:** Aggregate win rates, games played, and performance statistics by player and by deck.
- **Cloud Database Integration:** Real-time persistence using Supabase PostgreSQL with secure connection pooling.
- **Mobile Friendly:** Clean, streamlined UI designed for quick input at the game table.

---

## 🛠️ Tech Stack

- **Frontend / UI:** Streamlit
- **Backend:** Python 3.10+
- **Database:** PostgreSQL via Supabase (`psycopg2-binary`)
- **Environment Management:** `python-dotenv`
- **Hosting:** Streamlit Community Cloud

---

## 🚀 Local Development Setup

### 1. Prerequisites
Ensure you have **Python 3.10+** installed on your machine.

### 2. Clone the Repository
```bash
git clone [https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git](https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git)
cd YOUR_REPOSITORY_NAME