# -*- coding: utf-8 -*-
"""校园失物招领智能匹配平台 v2
新增：用户系统（学号注册登录）、通知红点、图片上传与以图搜物、搜索
"""
import json
import os
import re
import uuid
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import (Flask, abort, flash, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from hash_util import ahash, hamming
from matcher import find_matches, load_items, save_items

app = Flask(__name__)
app.secret_key = "campus-lost-found-demo-key"

DATA = Path(__file__).resolve().parent / "data"
MSG_FILE = DATA / "messages.json"
USER_FILE = DATA / "users.json"
NOTIF_FILE = DATA / "notifications.json"
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
GUARD = {"org": "学校保卫处", "room": "大学生活动中心一层 110 值班室", "phone": "8888-1110"}

CATEGORY_EMOJI = {"电子产品": "📱", "证件卡片": "🪪", "钥匙": "🔑", "日用品": "🧴",
                  "书籍资料": "📚", "其他": "📦"}


# ---------------------------------------------------------------- 存储

def _read(path, default):
    if Path(path).exists():
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return default


def _write(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_items():
    items = _read(DATA / "items.json", [])
    for it in items:
        it.setdefault("resolved", False)
        it.setdefault("owner", None)
        it.setdefault("photo", None)
        it.setdefault("phash", None)
    return items


def save_items(items):
    _write(DATA / "items.json", items)


def load_messages():
    return _read(MSG_FILE, {})


def load_users():
    return _read(USER_FILE, {})


def load_notifs():
    return _read(NOTIF_FILE, {})


def notify(uid, text, link):
    if not uid:
        return
    data = load_notifs()
    data.setdefault(uid, []).insert(0, {
        "text": text, "link": link,
        "time": datetime.now().strftime("%m-%d %H:%M"), "read": False,
    })
    _write(NOTIF_FILE, data)


def unread_count(uid):
    if not uid:
        return 0
    return sum(1 for n in load_notifs().get(uid, []) if not n.get("read"))


# ---------------------------------------------------------------- 会话

def current_user():
    uid = session.get("uid")
    if not uid:
        return None
    return load_users().get(uid)


def login_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if not current_user():
            return redirect(url_for("login", next=request.path))
        return fn(*a, **kw)
    return wrapper


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
app.jinja_env.globals.update(EMOJI=CATEGORY_EMOJI, GUARD=GUARD,
                             unread_count=unread_count, current_user=current_user,
                             guard=GUARD)


# ---------------------------------------------------------------- 匹配通知辅助

def notify_matches_for(new_item):
    """发布后：给发布者通知疑似匹配数；给配对度高且有主人的记录主人发通知"""
    items = load_items()
    matches = find_matches(new_item["id"], items, top_n=5)
    strong = [m for m in matches if m["score"] >= 30]
    if strong:
        top = strong[0]
        notify(new_item.get("owner"),
               f"你的登记《{new_item['title']}》发现 {len(strong)} 条疑似匹配，"
               f"最高 {top['score']} 分：{top['item']['title']}",
               f"/matches/{new_item['id']}")
    for m in matches:
        if m["score"] >= 40 and m["item"].get("owner") and m["item"]["owner"] != new_item.get("owner"):
            notify(m["item"]["owner"],
                   f"有新的“{'寻物' if new_item['type'] == 'lost' else '拾获'}”登记"
                   f"《{new_item['title']}》与你的《{m['item']['title']}》匹配度 {m['score']} 分",
                   f"/item/{m['item']['id']}")


def mask_contact(contact):
    if not contact:
        return "未留"
    digits = "".join(ch for ch in contact if ch.isdigit())
    if len(digits) >= 7:
        return contact[:3] + "****" + contact[-2:]
    return contact[:2] + "**"


# ---------------------------------------------------------------- 用户系统

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        uid = request.form.get("uid", "").strip()
        name = request.form.get("name", "").strip()
        pwd = request.form.get("pwd", "")
        users = load_users()
        if not (uid.isdigit() and len(uid) >= 8) or not name or len(pwd) < 6:
            return render_template("register.html",
                                   error="学号需为 8 位以上数字，密码至少 6 位，姓名不能为空")
        if uid in users:
            return render_template("register.html", error="该学号已注册，请直接登录")
        users[uid] = {"name": name, "pwd": generate_password_hash(pwd)}
        _write(USER_FILE, users)
        session["uid"] = uid
        return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        uid = request.form.get("uid", "").strip()
        pwd = request.form.get("pwd", "")
        users = load_users()
        if uid in users and check_password_hash(users[uid]["pwd"], pwd):
            session["uid"] = uid
            return redirect(request.args.get("next") or url_for("index"))
        return render_template("login.html", error="学号或密码错误")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ---------------------------------------------------------------- 页面

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
        shown = [x for x in shown
                 if ql in (x["title"] + x["desc"] + x["location"] + x["category"]).lower()]

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
                           q=q, cat_stats=cat_stats, max_cat=max_cat,
                           total_pool=len(pool))


@app.route("/publish", methods=["GET", "POST"])
@login_required
def publish():
    user = current_user()
    if request.method == "POST":
        items = load_items()
        new_id = max((x["id"] for x in items), default=0) + 1
        photo, phash = None, None
        f = request.files.get("photo")
        if f and f.filename:
            ext = Path(f.filename).suffix or ".png"
            photo = f"item_{new_id}_{uuid.uuid4().hex[:6]}{ext}"
            fp = UPLOAD_DIR / photo
            f.save(str(fp))
            phash = ahash(fp)
        item = {
            "id": new_id,
            "type": request.form.get("type", "lost"),
            "title": request.form.get("title", "").strip(),
            "category": request.form.get("category", "其他"),
            "desc": request.form.get("desc", "").strip(),
            "location": request.form.get("location", "").strip(),
            "date": request.form.get("date", ""),
            "contact": request.form.get("contact", user.get("name", "")),
            "owner": session.get("uid"),
            "photo": photo, "phash": phash, "resolved": False,
        }
        items.append(item)
        save_items(items)
        notify_matches_for(item)
        return redirect(url_for("item_detail", item_id=new_id))
    today = datetime.now().strftime("%Y-%m-%d")
    return render_template("publish.html", today=today, user=user)


@app.route("/item/<int:item_id>")
def item_detail(item_id):
    items = load_items()
    item = next((x for x in items if x["id"] == item_id), None)
    if item is None:
        return "记录不存在", 404
    return render_template("item.html", item=item,
                           emoji=CATEGORY_EMOJI.get(item["category"], "📦"))


@app.route("/resolve/<int:item_id>", methods=["POST"])
@login_required
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
    return render_template("matches.html", item=item, results=results,
                           emoji=CATEGORY_EMOJI.get(item["category"], "📦"))


@app.route("/photosearch", methods=["GET", "POST"])
def photosearch():
    results, query_img = [], None
    if request.method == "POST":
        f = request.files.get("photo")
        if f and f.filename:
            name = f"query_{uuid.uuid4().hex[:6]}{Path(f.filename).suffix or '.png'}"
            fp = UPLOAD_DIR / name
            f.save(str(fp))
            query_img = name
            qh = ahash(fp)
            items = load_items()
            ranked = []
            for x in items:
                if x.get("phash"):
                    dist = hamming(qh, x["phash"])
                    ranked.append((dist, x))
            ranked.sort(key=lambda t: t[0])
            results = [{"item": x, "dist": dist} for dist, x in ranked[:6] if dist <= 24]
    return render_template("photosearch.html", results=results, query_img=query_img)


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
    user = current_user()
    if request.method == "POST":
        body = request.get_json(force=True)
        name = (body.get("name") or (user["name"] if user else "匿名同学")).strip()[:12]
        text = (body.get("text") or "").strip()[:200]
        if text:
            data.setdefault(key, []).append({
                "name": name, "text": text,
                "time": datetime.now().strftime("%m-%d %H:%M"),
            })
            _write(MSG_FILE, data)
            owner = next((x.get("owner") for x in load_items()
                          if x["id"] == item_id), None)
            if owner and owner != session.get("uid"):
                notify(owner, f"你的登记《{next(x['title'] for x in load_items() if x['id'] == item_id)}》有新留言：{text[:40]}",
                       f"/chat/{item_id}")
        return jsonify({"ok": True})
    return jsonify({"messages": data.get(key, [])})


@app.route("/notifications")
def notifications():
    uid = session.get("uid")
    if not uid:
        return redirect(url_for("login", next="/notifications"))
    data = load_notifs()
    for n in data.get(uid, []):
        n["read"] = True
    _write(NOTIF_FILE, data)
    return render_template("notifications.html", notifs=data.get(uid, []))


@app.route("/uploads/<path:name>")
def uploads(name):
    from flask import send_from_directory
    return send_from_directory(UPLOAD_DIR, name)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=False)
