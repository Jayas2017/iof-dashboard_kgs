#!/usr/bin/env python3
"""
Upload/download iof-results.csv key-value pairs to Neon Cloud.
Creates table: iof_csv_store(param_key, param_value, param_unit)
"""
import psycopg2
import os
import sys

# Load connection string from .env
_env_path = os.path.join(os.path.dirname(__file__) or '.', '.env')
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _v = _line.split('=', 1)
                os.environ[_k.strip()] = _v.strip()

NEON_URL = os.environ.get('NEON_DATABASE_URL', '')


def get_conn():
    return psycopg2.connect(NEON_URL)


def init_table():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS iof_csv_store (
            id SERIAL PRIMARY KEY,
            param_key VARCHAR(200) NOT NULL,
            param_value TEXT,
            param_unit VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_iof_csv_key ON iof_csv_store(param_key)")
    conn.commit()
    cur.close()
    conn.close()
    print("Table 'iof_csv_store' ready.")


def upload_from_csv():
    """Parse iof-results.csv and store every row in Neon."""
    csv_path = 'iof-results.csv'
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return

    rows = []
    with open(csv_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(',', 2)
            if len(parts) >= 2:
                key = parts[0]
                val = parts[1]
                unit = parts[2] if len(parts) >= 3 else ''
                if key != 'Parameter':  # skip header
                    rows.append((key, val, unit))

    conn = get_conn()
    cur = conn.cursor()
    # Clear old data for fresh upload
    cur.execute("DELETE FROM iof_csv_store")
    for key, val, unit in rows:
        cur.execute(
            "INSERT INTO iof_csv_store (param_key, param_value, param_unit) VALUES (%s, %s, %s)",
            (key, val, unit)
        )
    conn.commit()
    cur.close()
    conn.close()
    print(f"Uploaded {len(rows)} key-value pairs to Neon.")


def get_all():
    """Fetch all key-value pairs as a dict."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT param_key, param_value, param_unit FROM iof_csv_store ORDER BY id")
    pairs = cur.fetchall()
    cur.close()
    conn.close()
    return pairs


def clear_table():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM iof_csv_store")
    conn.commit()
    cur.close()
    conn.close()
    print("Cleared all data from iof_csv_store.")


if __name__ == "__main__":
    init_table()
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "upload":
            upload_from_csv()
        elif cmd == "get":
            pairs = get_all()
            print(f"{len(pairs)} key-value pairs in Neon:")
            for k, v, u in pairs:
                print(f"  {k} = {v} {u}")
        elif cmd == "clear":
            clear_table()
        else:
            print("Usage: python csv_to_neon.py [upload|get|clear]")
    else:
        print("Usage: python csv_to_neon.py [upload|get|clear]")
