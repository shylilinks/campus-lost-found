# -*- coding: utf-8 -*-
"""校园失物招领智能匹配平台 - Flask 应用"""
import json
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, url_for

from matcher import find_matches, load_items, save_items

app = Flask(__name__)
DATA = Path(__file__).resolve().parent / "data"
MSG_FILE = DATA / "messages.json"
GUARD = {"org": "学校保卫处", "room": "大学生活动中心一层 110 值班室", "phone": "8888-1110"}


def load_messages():
    if MSG_FILE.exists():
        return json.loads(MSG_FILE.read_text(encoding="utf-8"))
    return {}


def save_messages(data):
    MSG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def mask_contact(contact):
    """列表页联系方式脱敏"""
    if not contact:
        return "未留"
    digits = "".join(ch for ch in contact if ch.isdigit())
    if len(digits) >= 7:
        return re.sub(r"\d", "*", contact) if False else contact[:3] + "****" + contact[-2:]
    return contact[:2] + "**"


import re  # noqa: E402


@app.route("/")
def index():
    items = load_items()
    ftype = request.args.get("type", "all")
    shown = [x for x in items if not x.get("resolved") and
             (ftype == "all" or x["type"] == ftype)]
    for x in shown:
        x["masked"] = mask_contact(x.get("contact", ""))
    counts = {
        "lost": sum(1 for x in items if x["type"] == "lost" and not x.get("resolved")),
        "found": sum(1 for x in items if x["type"] == "found" and not x.get("resolved")),
    }
    return render_template("index.html", items=shown, counts=counts, ftype=ftype)


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
    return render_template("item.html", item=item, guard=GUARD)


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
    return render_template("matches.html", item=item, results=results, guard=GUARD)


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
