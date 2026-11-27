# -*- coding: utf-8 -*-
"""智能匹配算法：失物/拾获信息的文本相似度 + 类别 + 地点 + 日期新鲜度综合评分"""
import json
import re
from datetime import datetime
from pathlib import Path

import jieba
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA = Path(__file__).resolve().parent / "data" / "items.json"


def load_items():
    items = json.loads(Path(DATA).read_text(encoding="utf-8"))
    for it in items:
        it.setdefault("resolved", False)
    return items


def save_items(items):
    Path(DATA).write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def tokenize(text):
    words = jieba.lcut(text or "")
    kept = [w for w in words if w.strip() and re.match(r"^[\u4e00-\u9fa5A-Za-z0-9]+$", w)]
    # 语义增强：同义词归一化扩展（水杯/杯子、平板/平板电脑、自行车/单车……）
    out = list(kept)
    for w in kept:
        if w in SYNONYMS:
            out.append(SYNONYMS[w])
    return " ".join(out)


SYNONYMS = {
    "水杯": "杯子", "保温杯": "杯子", "杯子": "水杯",
    "平板": "平板电脑", "ipad": "平板电脑",
    "自行车": "单车", "单车": "自行车",
    "书包": "背包", "背包": "书包",
    "雨伞": "伞", "伞": "雨伞",
    "蓝牙耳机": "耳机", "耳机": "蓝牙耳机",
    "手机": "电话", "钥匙扣": "钥匙",
    "校园卡": "卡证", "学生证": "证件", "身份证": "证件",
    "充电宝": "电源", "笔记本": "电脑",
}


def common_words(text_a, text_b, min_len=2):
    """两边描述中重合的词（用于关键词高亮）"""
    wa = set(tokenize(text_a).split())
    wb = set(tokenize(text_b).split())
    return {w for w in wa & wb if len(w) >= min_len}


def _date(text):
    try:
        return datetime.strptime(text, "%Y-%m-%d")
    except Exception:
        return None


def score_pair(a, b):
    """两条记录的匹配度评分（0~100）
    文本相似度 70 分 + 类别一致 20 分 + 地点重合 10 分 + 日期新鲜度最多 5 分
    """
    ta = tokenize(f"{a['title']} {a['desc']}")
    tb = tokenize(f"{b['title']} {b['desc']}")
    if not ta or not tb:
        sim = 0.0
    else:
        vec = TfidfVectorizer()
        m = vec.fit_transform([ta, tb])
        sim = float(cosine_similarity(m[0], m[1])[0][0])
    score = sim * 70

    if a.get("category") == b.get("category"):
        score += 20

    la, lb = a.get("location", ""), b.get("location", "")
    if la and lb and (la in lb or lb in la):
        score += 10

    da, db = _date(a.get("date", "")), _date(b.get("date", ""))
    if da and db:
        gap = abs((da - db).days)
        if gap <= 7:
            score += 5 - gap * 0.5

    return round(min(score, 100), 1)


def find_matches(target_id, items=None, top_n=3):
    """为 target_id 找另一个类型中最匹配的未解决记录，返回 Top-N
    每条结果附带 common_words（双方重合关键词，供高亮）"""
    items = items or load_items()
    target = next((x for x in items if x["id"] == target_id), None)
    if target is None:
        return []
    others = [x for x in items
              if x["type"] != target["type"] and not x.get("resolved", False)]
    ranked = []
    for other in others:
        s = score_pair(target, other)
        if s > 0:
            ranked.append({"item": other, "score": s,
                           "common": sorted(common_words(
                               f"{target['title']} {target['desc']}",
                               f"{other['title']} {other['desc']}"))})
    ranked.sort(key=lambda x: -x["score"])
    return ranked[:top_n]
