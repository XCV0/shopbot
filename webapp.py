# webapp.py
import json
from flask import Flask, render_template
from db.db_controller import get_shops, init_db

app = Flask(__name__)


@app.before_first_request
def _init_db():
    # чтобы таблицы точно были созданы
    init_db()


@app.route("/")
def index():
    """
    Отдаём мини-апп и передаём в него список кафе + меню из БД.
    """
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
                "description": ""  # в БД её нет, поэтому пусто
            })

        cafes[str(shop_id)] = {
            "id": shop_id,
            "title": name,
            "subtitle": address,
            "items": items,
        }

    cafes_json = json.dumps(cafes, ensure_ascii=False)
    return render_template("index.html", cafes_json=cafes_json)


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    # В бою лучше запускать через gunicorn/uwsgi за nginx с HTTPS
    app.run(host="0.0.0.0", port=8000, debug=True)