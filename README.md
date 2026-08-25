# 🛡️ EDH Tracker — Streamlit Commander Companion & Analytics App

A full-stack web application designed to track, log, analyze, and manage Magic: The Gathering Commander (EDH) games. Built specifically for casual and competitive gaming pods, the app bridges live game companion tracking with post-game performance analytics, player statistics, and deck management.

---

## ⚡ Key Features

### ⚔️ Live Match Companion & Logger
* **Real-Time Match Timer:** Live timer fragment that tracks total playtime during matches.
* **Turn Counter:** Interactive turn counter allowing players to update current turns on the fly.
* **Auto-Fill Integration:** Automatically pushes final game duration and turn counts straight into the logging form when a match ends.
* **Live Form Auto-Saving:** Saves in-progress pod details and draft states to the database so game inputs survive accidental reloads or page refreshes.
* **Timezone Alignment:** Normalizes all match dates and timestamps to local time (`America/Santo_Domingo`).

### 📊 Analytics & Reporting Dashboards
* **Player Leaderboards:** Win rates, total games played, and victory conditions categorized per player.
* **Deck Analytics:** Performance summaries, color identity presence, deck bracket performance, and ownership stats.
* **Daily & Monthly Recaps:** Dedicated session summaries aggregating overall pod trends, top performing players, and standout decks across specific days or calendar months.
* **Random Card of the Day:** Integrates daily card highlights for your playgroup.

### 🛠️ Deck & Player Management
* **Moxfield Integration:** Pulls and syncs Commander decks directly from public Moxfield URLs.
* **Color Identity & Bracket Tracking:** Automatically assigns commander color identities and tracks power levels / game brackets.
* **Global Deck Borrowing:** Accounts for players borrowing decks from other members of the pod during game logging.

### 🔒 Security & Multi-User Access
* **Salted PIN Encryption:** Secure PIN verification protecting administrative and logging capabilities.
* **Role-Based Permissions:** Granular access controls dividing features between **Admin**, **Logger**, and **Viewer** roles.
* **Persistent Mobile Shortcuts:** Device token authentication allowing users to stay logged into their accounts permanently without typing passwords repeatedly.

---

## 👥 Access Roles & Permission Levels

| Role | Access Description | Available Pages |
| :--- | :--- | :--- |
| **Admin** | Full system administration and data management | Log Match, Analytics, Add Deck, Daily Recap, Deck & Player Admin, Match Admin, Random Card, Monthly Recap |
| **Logger** | Standard player access for logging and tracking | Log Match, Analytics, Add Deck, Daily Recap, Random Card, Monthly Recap |
| **Viewer** | Read-only mode for guests or passive viewers | Analytics, Daily Recap, Random Card, Monthly Recap |

---

## 📱 User Onboarding & Mobile Shortcut Setup

To ensure persistent login on mobile devices without browser session timeouts, users are assigned device-specific tokens.

### Adding New Users
1. **User Creation:** The Admin creates a new username, sets their role (**Admin** or **Logger**), and assigns a PIN. The system automatically hashes the PIN for storage.
2. **Link Generation:** A unique 30-year device token is created and tied to that user's account.
3. **Magic Link:** The Admin sends the user their personalized direct URL containing their device token.

### Mobile App Installation
* **iOS (Apple Shortcuts Method):** Create a shortcut using the **Show Web Page** action pointing to the personalized link, then tap **Add to Home Screen**. This prevents Safari from stripping persistent URL parameters.
* **Android (Chrome Method):** Open the personalized link in Chrome and select **Add to Home Screen** from the browser menu.

---

## 📜 Development & Milestones Progress Log

### 🗓️ July 29 – August 5, 2026
* **Infrastructure Setup:** Configured Streamlit deployment environment, established PostgreSQL database connection pools, and registered deployment SSH keys.

### 🗓️ August 9 – August 22, 2026
* **Uptime Monitoring:** Configured automated ping services to maintain continuous app responsiveness and eliminate container cold starts.

### 🗓️ August 24, 2026
* **Form Deserialization Guard:** Resolved data serialization conflicts on date components, ensuring smooth form state recovery across sessions.
* **iOS WebKit Workaround:** Developed path-based and shortcut-based workarounds to bypass iOS Safari's automatic URL parameter stripping on standalone WebApps.
* **Cryptographic PIN Authentication:** Upgraded access security to SHA-256 salted PIN hashing paired with PostgreSQL database functions.
* **Unified Multi-User Architecture:** Tied persistent device tokens directly to user profiles, allowing multiple distinct Admin and Logger accounts.
* **Session Deduplication & 30-Year Retention:** Configured device tokens to reuse existing active sessions upon manual login and extended persistence lifetimes to 30 years.