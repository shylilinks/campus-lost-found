# -*- coding: utf-8 -*-
"""校园失物招领智能匹配平台 - Flask 应用"""
import json
import re
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, url_for

from matcher import find_matches, load_items, save_items

app = Flask(__name__)
DATA = Path(__file__).resolve().parent / "data"
MSG_FILE = DATA / "messages.json"
GUARD = {"org": "学校保卫处", "room": "大学生活动中心一层 110 值班室", "phone": "8888-1110"}

CATEGORY_EMOJI = {"电子产品": "📱", "证件卡片": "🪪", "钥匙": "🔑", "日用品": "🧴",
                  "书籍资料": "📚", "其他": "📦"}


def rel_time(date_str):
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return date_str
    days = (datetime.now() - d).days
    if days <= 0:
        return "今天"
    if days == 1:
        return "昨天"
    if days < 30:
        return f"{days} 天前"
    return date_str


app.add_template_filter(rel_time, "reltime")
app.jinja_env.globals.update(EMOJI=CATEGORY_EMOJI)


def mask_contact(contact):
    if not contact:
        return "未留"
    digits = "".join(ch for ch in contact if ch.isdigit())
    if len(digits) >= 7:
        return contact[:3] + "****" + contact[-2:]
    return contact[:2] + "**"


def load_messages():
    if MSG_FILE.exists():
        return json.loads(MSG_FILE.read_text(encoding="utf-8"))
    return {}


def save_messages(data):
    MSG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@app.route("/")
def index():
    items = load_items()
    ftype = request.args.get("type", "all")
    q = request.args.get("q", "").strip()

    pool = [x for x in items if not x.get("resolved")]
    resolved = [x for x in items if x.get("resolved")]

    if ftype == "lost":
        shown = [x for x in pool if x["type"] == "lost"]
    elif ftype == "found":
        shown = [x for x in pool if x["type"] == "found"]
    elif ftype == "resolved":
        shown = resolved
    else:
        shown = pool

    if q:
        ql = q.lower()
        shown = [x for x in shown if ql in (x["title"] + x["desc"] + x["location"] +
                                            x["category"]).lower()]

    for x in shown:
        x["masked"] = mask_contact(x.get("contact", ""))
        x["emoji"] = CATEGORY_EMOJI.get(x["category"], "📦")

    cats = {}
    for x in pool:
        cats[x["category"]] = cats.get(x["category"], 0) + 1
    cat_stats = sorted(cats.items(), key=lambda kv: -kv[1])
    max_cat = cat_stats[0][1] if cat_stats else 1

    counts = {"lost": sum(1 for x in pool if x["type"] == "lost"),
              "found": sum(1 for x in pool if x["type"] == "found"),
              "resolved": len(resolved)}
    return render_template("index.html", items=shown, counts=counts, ftype=ftype,
                           q=q, cat_stats=cat_stats, max_cat=max_cat, total_pool=len(pool))


@app.route("/publish", methods=["GET", "POST"])
def publish():
    if request.method == "POST":
        items = load_items()
        new_id = max((x["id"] for x in items), default=0) + 1
        items.append({
            "id": new_id,
            "type": request.form.get("type", "lost"),
            "title": request.form.get("title", "").strip(),
            "category": request.form.get("category", "其他"),
            "desc": request.form.get("desc", "").strip(),
            "location": request.form.get("location", "").strip(),
            "date": request.form.get("date", ""),
            "contact": request.form.get("contact", "").strip(),
            "resolved": False,
        })
        save_items(items)
        return redirect(url_for("item_detail", item_id=new_id))
    return render_template("publish.html")


@app.route("/item/<int:item_id>")
def item_detail(item_id):
    items = load_items()
    item = next((x for x in items if x["id"] == item_id), None)
    if item is None:
        return "记录不存在", 404
    return render_template("item.html", item=item, guard=GUARD,
                           emoji=CATEGORY_EMOJI.get(item["category"], "📦"))


@app.route("/resolve/<int:item_id>", methods=["POST"])
def resolve(item_id):
    items = load_items()
    for x in items:
        if x["id"] == item_id:
            x["resolved"] = True
            x["resolved_as"] = request.form.get("as", "已找回")
    save_items(items)
    return redirect(url_for("index"))


@app.route("/matches/<int:item_id>")
def matches(item_id):
    items = load_items()
    item = next((x for x in items if x["id"] == item_id), None)
    if item is None:
        return "记录不存在", 404
    results = find_matches(item_id, items)
    for r in results:
        r["stars"] = max(1, min(5, round(r["score"] / 20)))
    return render_template("matches.html", item=item, results=results, guard=GUARD,
                           emoji=CATEGORY_EMOJI.get(item["category"], "📦"))


@app.route("/chat/<int:item_id>", methods=["GET"])
def chat(item_id):
    items = load_items()
    item = next((x for x in items if x["id"] == item_id), None)
    if item is None:
        return "记录不存在", 404
    msgs = load_messages().get(str(item_id), [])
    return render_template("chat.html", item=item, messages=msgs)


@app.route("/api/messages/<int:item_id>", methods=["GET", "POST"])
def api_messages(item_id):
    data = load_messages()
    key = str(item_id)
    if request.method == "POST":
        body = request.get_json(force=True)
        name = (body.get("name") or "匿名同学").strip()[:12]
        text = (body.get("text") or "").strip()[:200]
        if text:
            data.setdefault(key, []).append({
                "name": name, "text": text,
                "time": datetime.now().strftime("%m-%d %H:%M"),
            })
            save_messages(data)
        return jsonify({"ok": True})
    return jsonify({"messages": data.get(key, [])})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
