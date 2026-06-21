# FoodMart Local Database Setup

This FoodMart app already includes a Python backend server (`server.py`) that syncs browser state to a real database.

## Supported databases
- SQLite (default)
- PostgreSQL (optional)

## Setup
1. Install Python 3.11+.
2. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

3. Start the server:

```powershell
python server.py
```

4. Open the app in a browser:

```text
http://127.0.0.1:8000
```

## How it works
- The browser stores data in `localStorage`.
- `db-sync.js` sends the current app state to `POST /api/sync` whenever storage changes.
- `GET /api/state` loads saved state from the database when the page opens.
- The server stores data in `foodmart.db` by default.

## Using Supabase PostgreSQL
1. Create a `.env` file in the same folder as `server.py`.
2. In Supabase, open your project and select **Connect**.
3. Copy the PostgreSQL URI. For local networks without IPv6, choose the **Session pooler** URI.
4. Put the exact URI in `.env`:

```dotenv
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/postgres?sslmode=require
```

5. Replace the password placeholder if Supabase did not insert it, then restart the server.

Do not use the public project URL (`https://PROJECT_REF.supabase.co`) or an anon/service key here. `psycopg` needs the PostgreSQL connection URI. If the database password contains reserved URL characters such as `@`, `:`, `/`, or `#`, use the URI provided by the Supabase dashboard or URL-encode the password.

You can alternatively name the same value `SUPABASE_DB_URL`; `DATABASE_URL` is recommended.

Verify the connection at:

```text
http://127.0.0.1:8000/api/health
```

The response should report `"backend": "postgresql"`.

## Notes
- Do not open the HTML files directly with `file://`; run the server and use `http://127.0.0.1:8000`.
- The app already includes support for syncing cart, wishlist, account, and order history to the database.
- Keep `.env` private. Never put its database password in browser JavaScript or commit it to source control.
