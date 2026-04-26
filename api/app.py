"""API Flask — Phase 1 walking skeleton.

Endpoints :
- GET /api/offers       liste simple
"""

from __future__ import annotations

from flask import Flask, jsonify

from api.db import get_connection

app = Flask(__name__)


@app.get("/api/offers")
def list_offers():
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT
                o.id,
                op.name AS operator,
                o.type,
                o.name,
                o.monthly_price,
                o.promo_price,
                o.score
            FROM offers o
            JOIN operators op ON op.id = o.operator_id
            WHERE o.is_active = TRUE
            ORDER BY o.id
            """
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    for row in rows:
        row["monthly_price"] = float(row["monthly_price"])
        if row["promo_price"] is not None:
            row["promo_price"] = float(row["promo_price"])
        if row["score"] is not None:
            row["score"] = float(row["score"])

    return jsonify(rows)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
