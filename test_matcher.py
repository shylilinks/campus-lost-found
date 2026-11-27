# -*- coding: utf-8 -*-
"""匹配算法自动化质量测试：准确率 / 边界 / 不变性 / 排序稳定性
直接运行生成 测试报告.md；也可被 pytest 收集（main 受 __main__ 保护）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from matcher import find_matches, load_items, score_pair  # noqa: E402

results = []


def record(case, expect, actual, passed):
    results.append((case, expect, actual, "通过" if passed else "失败"))
    print(("✅" if passed else "❌"), case)


def top1_is(items, target_id, expect_id, case):
    r = find_matches(target_id, items)
    top = r[0]["item"]["id"] if r else None
    record(case, f"Top1 = {expect_id}", f"Top1 = {top}", top == expect_id)


def top3_contains(items, target_id, expect_id, case):
    r = find_matches(target_id, items)
    ids = [x["item"]["id"] for x in r]
    record(case, f"Top3 含 {expect_id}", f"实际 {ids}", expect_id in ids)


def run_all():
    items = load_items()

    # ---------- 一、准确率测试 ----------
    top1_is(items, 1, 7, "准确率：蓝牙耳机丢失 → 拾获蓝牙耳机排 Top1")
    top3_contains(items, 2, 8, "准确率：校园卡丢失 → 拾获校园卡进 Top3")
    top1_is(items, 3, 9, "准确率：教学楼丢伞 → 拾获同教室的伞排 Top1")
    top1_is(items, 4, 10, "准确率：水杯丢失 → 拾获同款水杯排 Top1")
    top1_is(items, 6, 12, "准确率：高数课本丢失 → 拾获课本排 Top1")

    # ---------- 二、边界用例 ----------
    edge_items = load_items()
    edge_items.append({"id": 99, "type": "lost", "title": "", "category": "其他",
                       "desc": "", "location": "", "date": "", "contact": "t"})
    try:
        r = find_matches(99, edge_items)
        record("边界：空标题+空描述不崩溃", "正常返回列表", f"返回 {len(r)} 条",
               isinstance(r, list))
    except Exception as e:
        record("边界：空标题+空描述不崩溃", "正常返回列表", f"崩溃 {e}", False)

    edge_items.append({"id": 98, "type": "lost", "title": "卡", "category": "证件卡片",
                       "desc": "卡", "location": "食堂", "date": "2026-11-21",
                       "contact": "t"})
    try:
        top3_contains(edge_items, 98, 8, "边界：单字描述“卡”能命中校园卡")
    except Exception as e:
        record("边界：单字描述", "不崩溃", f"崩溃 {e}", False)

    # ---------- 三、不变性测试 ----------
    base_desc = "在图书馆三楼自习室丢了一只黑色蓝牙耳机，白色充电盒"
    noisy = base_desc + "！！！  ？？？？"
    noisy_items = load_items()
    for x in noisy_items:
        if x["id"] == 1:
            x["desc"] = noisy
        if x["id"] == 7:
            x["desc"] = x["desc"].replace("三楼", "三楼   ")
    s_clean = score_pair(items[0], items[6])
    s_noisy = score_pair(next(x for x in noisy_items if x["id"] == 1),
                         next(x for x in noisy_items if x["id"] == 7))
    r = find_matches(1, noisy_items)
    top = r[0]["item"]["id"] if r else None
    record("不变性：加标点/空格后推荐结果不变",
           "Top1 = 7（TF-IDF 分数漂移 ≤10 为正常波动）",
           f"Top1 = {top}（{s_clean} → {s_noisy}）",
           top == 7 and abs(s_clean - s_noisy) <= 10)

    # ---------- 四、排序稳定性 ----------
    stable_items = load_items()
    stable_items.append({"id": 97, "type": "found", "title": "白色耳机盒",
                         "category": "日用品", "desc": "捡到白色盒子一个",
                         "location": "操场", "date": "2026-11-10", "contact": "t"})
    r = find_matches(1, stable_items)
    ids = [x["item"]["id"] for x in r]
    record("排序稳定性：加入干扰记录后蓝牙耳机仍 Top1", "Top1 = 7",
           f"Top1 = {ids[0] if ids else None}", ids and ids[0] == 7)

    # ---------- 生成测试报告 ----------
    passed = sum(1 for r in results if r[3] == "通过")
    lines = [
        "# 匹配算法自动化测试报告",
        "",
        "- 测试对象：matcher.py（智能匹配算法）",
        f"- 用例总数：{len(results)}　通过：{passed}　失败：{len(results) - passed}",
        "- 测试类型：准确率 / 边界 / 不变性 / 排序稳定性",
        "",
        "| 编号 | 测试内容 | 预期 | 实际 | 结论 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for idx, (case, expect, actual, verdict) in enumerate(results, 1):
        lines.append(f"| {idx} | {case} | {expect} | {actual} | {verdict} |")
    lines.append("")
    lines.append("结论：" + ("**全部通过**，匹配算法质量达标。" if passed == len(results)
                         else f"存在 {len(results) - passed} 个失败用例，需要修复。"))
    (Path(__file__).resolve().parent / "测试报告.md").write_text(
        "\n".join(lines), encoding="utf-8")
    return passed == len(results)


if __name__ == "__main__":
    ok = run_all()
    print(f"\n测试报告已生成：测试报告.md")
    sys.exit(0 if ok else 1)
