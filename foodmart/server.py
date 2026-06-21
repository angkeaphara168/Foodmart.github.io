from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import json
import os
import sqlite3
import sys


try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None
    dict_row = None

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
    RealDictCursor = None


BASE_DIR = Path(__file__).resolve().parent
SQLITE_DB_PATH = BASE_DIR / "foodmart.db"


def load_env_file():
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


load_env_file()

HOST = os.environ.get("FOODMART_HOST", "127.0.0.1")
PORT = int(os.environ.get("FOODMART_PORT", "8000"))

STATE_KEYS = {
    "account": "account",
    "cart": "cart",
    "wishlist": "wishlist",
    "orderStatus": "order_status",
    "currentOrderId": "current_order_id",
    "orderHistory": "order_history",
}

POSTGRES_ENV_KEYS = ("DATABASE_URL", "PGDATABASE", "SUPABASE_DB_URL")


def wants_postgres():
    return any(os.environ.get(key) for key in POSTGRES_ENV_KEYS)


def db_backend():
    return "postgresql" if wants_postgres() else "sqlite"


def postgres_connect_kwargs():
    keys = {
        "PGHOST": "host",
        "PGPORT": "port",
        "PGDATABASE": "dbname",
        "PGUSER": "user",
        "PGPASSWORD": "password",
    }
    return {target: os.environ[source] for source, target in keys.items() if os.environ.get(source)}


def postgres_driver_name():
    if psycopg:
        return "psycopg"
    if psycopg2:
        return "psycopg2"
    return None


def postgres_database_url():
    return os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")


def db():
    if not wants_postgres():
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    if psycopg:
        database_url = postgres_database_url()
        if database_url:
            return psycopg.connect(database_url, row_factory=dict_row)
        return psycopg.connect(**postgres_connect_kwargs(), row_factory=dict_row)

    if psycopg2:
        database_url = postgres_database_url()
        if database_url:
            return psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        return psycopg2.connect(**postgres_connect_kwargs(), cursor_factory=RealDictCursor)

    raise RuntimeError(
        "PostgreSQL is configured, but no Python PostgreSQL driver is installed. "
        "Install one with: python -m pip install -r requirements.txt"
    )


def sql(sqlite_sql):
    if wants_postgres():
        return sqlite_sql.replace("?", "%s")
    return sqlite_sql


def execute(conn, query, params=()):
    query = sql(query)
    if isinstance(conn, sqlite3.Connection) or hasattr(conn, "execute"):
        return conn.execute(query, params)

    cursor = conn.cursor()
    cursor.execute(query, params)
    return cursor


SQLITE_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS app_state (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL,
      updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS accounts (
      id INTEGER PRIMARY KEY CHECK (id = 1),
      name TEXT,
      email TEXT,
      phone TEXT,
      address TEXT,
      joined TEXT,
      updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS cart_items (
      product_id INTEGER PRIMARY KEY,
      name TEXT NOT NULL,
      category TEXT,
      price REAL NOT NULL DEFAULT 0,
      image_url TEXT,
      fallback_image_url TEXT,
      weight TEXT,
      quantity INTEGER NOT NULL DEFAULT 1,
      updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS wishlist_items (
      product_id INTEGER PRIMARY KEY,
      name TEXT NOT NULL,
      category TEXT,
      price REAL NOT NULL DEFAULT 0,
      image_url TEXT,
      fallback_image_url TEXT,
      weight TEXT,
      updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS orders (
      order_id TEXT PRIMARY KEY,
      customer TEXT,
      email TEXT,
      order_date TEXT,
      created_at TEXT,
      total REAL NOT NULL DEFAULT 0,
      status INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS order_items (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      order_id TEXT NOT NULL,
      product_id INTEGER,
      name TEXT NOT NULL,
      quantity INTEGER NOT NULL DEFAULT 1,
      price REAL NOT NULL DEFAULT 0,
      weight TEXT,
      FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS order_state (
      id INTEGER PRIMARY KEY CHECK (id = 1),
      status INTEGER,
      current_order_id TEXT,
      updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
]

POSTGRES_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS app_state (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS accounts (
      id INTEGER PRIMARY KEY CHECK (id = 1),
      name TEXT,
      email TEXT,
      phone TEXT,
      address TEXT,
      joined TEXT,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS cart_items (
      product_id INTEGER PRIMARY KEY,
      name TEXT NOT NULL,
      category TEXT,
      price DOUBLE PRECISION NOT NULL DEFAULT 0,
      image_url TEXT,
      fallback_image_url TEXT,
      weight TEXT,
      quantity INTEGER NOT NULL DEFAULT 1,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS wishlist_items (
      product_id INTEGER PRIMARY KEY,
      name TEXT NOT NULL,
      category TEXT,
      price DOUBLE PRECISION NOT NULL DEFAULT 0,
      image_url TEXT,
      fallback_image_url TEXT,
      weight TEXT,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS orders (
      order_id TEXT PRIMARY KEY,
      customer TEXT,
      email TEXT,
      order_date TEXT,
      created_at TEXT,
      total DOUBLE PRECISION NOT NULL DEFAULT 0,
      status INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS order_items (
      id SERIAL PRIMARY KEY,
      order_id TEXT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
      product_id INTEGER,
      name TEXT NOT NULL,
      quantity INTEGER NOT NULL DEFAULT 1,
      price DOUBLE PRECISION NOT NULL DEFAULT 0,
      weight TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS order_state (
      id INTEGER PRIMARY KEY CHECK (id = 1),
      status INTEGER,
      current_order_id TEXT,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
]


def init_db():
    schema = POSTGRES_SCHEMA if wants_postgres() else SQLITE_SCHEMA
    with db() as conn:
        for statement in schema:
            execute(conn, statement)


def read_json_value(conn, state_name, fallback):
    key = STATE_KEYS[state_name]
    row = execute(conn, "SELECT value FROM app_state WHERE key = ?", (key,)).fetchone()
    if not row:
        return fallback

    try:
        return json.loads(row["value"])
    except json.JSONDecodeError:
        return fallback


def write_json_value(conn, state_name, value):
    key = STATE_KEYS[state_name]
    execute(
        conn,
        """
        INSERT INTO app_state (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET
          value = excluded.value,
          updated_at = CURRENT_TIMESTAMP
        """,
        (key, json.dumps(value, separators=(",", ":"))),
    )


def read_state():
    with db() as conn:
        state = {
            "account": read_json_value(conn, "account", None),
            "cart": read_json_value(conn, "cart", []),
            "wishlist": read_json_value(conn, "wishlist", []),
            "orderStatus": read_json_value(conn, "orderStatus", None),
            "currentOrderId": read_json_value(conn, "currentOrderId", None),
            "orderHistory": read_json_value(conn, "orderHistory", []),
        }

    state["hasData"] = bool(
        state["account"]
        or state["cart"]
        or state["wishlist"]
        or state["orderStatus"] is not None
        or state["currentOrderId"]
        or state["orderHistory"]
    )
    return state


def as_list(value):
    return value if isinstance(value, list) else []


def as_dict(value):
    return value if isinstance(value, dict) else None


def to_int(value, fallback=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def to_float(value, fallback=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def normalize_item(item):
    if not isinstance(item, dict):
        return None

    product_id = to_int(item.get("id"), None)
    name = str(item.get("name") or "").strip()
    if product_id is None or not name:
        return None

    return {
        "id": product_id,
        "name": name,
        "cat": str(item.get("cat") or ""),
        "price": to_float(item.get("price")),
        "img": str(item.get("img") or ""),
        "fallbackImg": str(item.get("fallbackImg") or ""),
        "weight": str(item.get("weight") or ""),
        "qty": max(1, to_int(item.get("qty"), 1)),
    }


def sync_account(conn, account):
    execute(conn, "DELETE FROM accounts")
    account = as_dict(account)
    if not account:
        return

    execute(
        conn,
        """
        INSERT INTO accounts (id, name, email, phone, address, joined, updated_at)
        VALUES (1, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            account.get("name"),
            account.get("email"),
            account.get("phone"),
            account.get("address"),
            account.get("joined"),
        ),
    )


def sync_items(conn, table, items, include_qty):
    execute(conn, f"DELETE FROM {table}")
    for raw_item in as_list(items):
        item = normalize_item(raw_item)
        if not item:
            continue

        if include_qty:
            execute(
                conn,
                """
                INSERT INTO cart_items
                  (product_id, name, category, price, image_url, fallback_image_url, weight, quantity, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    item["id"],
                    item["name"],
                    item["cat"],
                    item["price"],
                    item["img"],
                    item["fallbackImg"],
                    item["weight"],
                    item["qty"],
                ),
            )
        else:
            execute(
                conn,
                """
                INSERT INTO wishlist_items
                  (product_id, name, category, price, image_url, fallback_image_url, weight, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    item["id"],
                    item["name"],
                    item["cat"],
                    item["price"],
                    item["img"],
                    item["fallbackImg"],
                    item["weight"],
                ),
            )


def sync_orders(conn, orders):
    execute(conn, "DELETE FROM order_items")
    execute(conn, "DELETE FROM orders")

    for order in as_list(orders):
        if not isinstance(order, dict):
            continue

        order_id = str(order.get("id") or "").strip()
        if not order_id:
            continue

        execute(
            conn,
            """
            INSERT INTO orders
              (order_id, customer, email, order_date, created_at, total, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order_id,
                order.get("customer"),
                order.get("email"),
                order.get("date"),
                order.get("createdAt"),
                to_float(order.get("total")),
                to_int(order.get("status"), 0),
            ),
        )

        for raw_item in as_list(order.get("items")):
            item = normalize_item(raw_item)
            if not item:
                continue

            execute(
                conn,
                """
                INSERT INTO order_items
                  (order_id, product_id, name, quantity, price, weight)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    item["id"],
                    item["name"],
                    item["qty"],
                    item["price"],
                    item["weight"],
                ),
            )


def sync_order_state(conn, status, current_order_id):
    normalized_status = None if status is None else to_int(status, None)
    normalized_order_id = current_order_id if current_order_id else None
    execute(conn, "DELETE FROM order_state")
    execute(
        conn,
        """
        INSERT INTO order_state (id, status, current_order_id, updated_at)
        VALUES (1, ?, ?, CURRENT_TIMESTAMP)
        """,
        (normalized_status, normalized_order_id),
    )


def save_state(payload):
    state = {
        "account": as_dict(payload.get("account")),
        "cart": as_list(payload.get("cart")),
        "wishlist": as_list(payload.get("wishlist")),
        "orderStatus": payload.get("orderStatus"),
        "currentOrderId": payload.get("currentOrderId"),
        "orderHistory": as_list(payload.get("orderHistory")),
    }

    with db() as conn:
        for state_name, value in state.items():
            write_json_value(conn, state_name, value)

        sync_account(conn, state["account"])
        sync_items(conn, "cart_items", state["cart"], include_qty=True)
        sync_items(conn, "wishlist_items", state["wishlist"], include_qty=False)
        sync_orders(conn, state["orderHistory"])
        sync_order_state(conn, state["orderStatus"], state["currentOrderId"])

    return read_state()


def database_info():
    if wants_postgres():
        database_url = postgres_database_url()
        parsed_url = urlparse(database_url) if database_url else None
        database_name = parsed_url.path.lstrip("/") if parsed_url else postgres_connect_kwargs().get("dbname")
        database_host = parsed_url.hostname if parsed_url else postgres_connect_kwargs().get("host")
        return {
            "backend": "postgresql",
            "driver": postgres_driver_name(),
            "configured": True,
            "database": database_name,
            "host": database_host,
        }

    return {
        "backend": "sqlite",
        "driver": "sqlite3",
        "configured": True,
        "database": str(SQLITE_DB_PATH),
    }


class FoodMartHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}

        raw_body = self.rfile.read(length)
        try:
            return json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            return None

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            self.send_json(200, {"ok": True, **database_info()})
            return
        if path == "/api/state":
            self.send_json(200, read_state())
            return
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/api/sync":
            self.send_error(404, "API endpoint not found")
            return

        payload = self.read_json_body()
        if payload is None:
            self.send_json(400, {"ok": False, "error": "Invalid JSON body"})
            return

        self.send_json(200, {"ok": True, "state": save_state(payload)})

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()


def main():
    init_db()
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT

    server = ThreadingHTTPServer((HOST, port), FoodMartHandler)
    info = database_info()
    print(f"FoodMart server running at http://{HOST}:{port}/")
    print(f"Database backend: {info['backend']}")
    print(f"Database: {info['database']}")
    server.serve_forever()


if __name__ == "__main__":
    main()
