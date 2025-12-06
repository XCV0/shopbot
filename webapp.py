import json
from flask import Flask, render_template
from db.db_controller import get_shops, init_db

app = Flask(__name__)


init_db()

@app.route("/")
def index():
    shops = get_shops(active_only=True)
    cafes = {}

    for s in shops:
        shop_id, name, address, menu_json, time_available, day_available, report_time, active = s
        try:
            menu = json.loads(menu_json) if menu_json else []
        except Exception:
            menu = []

        items = []
        for idx, item in enumerate(menu):
            title = item.get("title") or "Блюдо"
            price = item.get("price") or 0
            items.append({
                "id": f"{shop_id}_{idx}",
                "name": title,
                "price": price,
                "description": ""
            })

        cafes[str(shop_id)] = {
            "id": shop_id,
            "title": name,
            "subtitle": address,
            "items": items,
        }

    cafes_json = json.dumps(cafes, ensure_ascii=False)
    return render_template("index.html", cafes_json=cafes_json)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=443, debug=True)