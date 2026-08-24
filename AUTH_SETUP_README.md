# 🔒 User Authentication & Device Provisioning SOP

This document outlines the procedure for managing user accounts, PIN hashes, persistent device sessions, and mobile shortcuts for the EDH Tracker application.

---

## 🏗️ 1. Architecture Overview

* **Database Engine:** Supabase PostgreSQL with `pgcrypto` extension.
* **Security:** User PINs are stored as SHA-256 hashes inside `app_users`. Raw PINs are never stored.
* **Persistence:** Device tokens inside `user_sessions` are set to expire after **30 years** (`NOW() + INTERVAL '30 years'`).
* **Session Deduplication:** Logging in via PIN reuses a user's existing active token to prevent session clutter.

---

## 👥 2. Roles & Permissions Matrix

| Role | Access Level | Available Pages |
| :--- | :--- | :--- |
| **Admin** | Full Management | Log Match, Analytics, Add Deck, Daily Recap, Deck & Player Admin, Match Admin, Random Card, Monthly Recap |
| **Logger** | Gameplay & Logging | Log Match, Analytics, Add Deck, Daily Recap, Random Card, Monthly Recap |
| **Viewer** | Read-Only | Analytics, Daily Recap, Random Card, Monthly Recap |

---

## 🚀 3. Creating New Accounts & Generating Links

Run these steps inside the **Supabase SQL Editor** whenever onboarding a new player or admin.

### Step 3.1: Create or Update User Credentials
Generates a user entry with a SHA-256 hashed PIN:

```sql
-- Syntax: SELECT upsert_app_user('Username', 'PIN', 'Role');

-- Example: Add an Admin
SELECT upsert_app_user('Caleb', '1234', 'Admin');

-- Example: Add a Logger
SELECT upsert_app_user('Nikki', '5678', 'Logger');