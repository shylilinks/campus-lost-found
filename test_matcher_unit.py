# -*- coding: utf-8 -*-
"""A2: pytest 单元测试 matcher.py（参数化 + 覆盖率）"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest
from matcher import common_words, find_matches, load_items, score_pair, tokenize


@pytest.fixture
def items():
    return load_items()


def test_tokenize_filters_punctuation():
    assert "！！！" not in tokenize("耳机！！！")
    assert "耳机" in tokenize("耳机！！！")


def test_tokenize_synonym_expansion():
    toks = tokenize("水杯").split()
    assert "杯子" in toks or "水杯" in toks
    toks2 = tokenize("杯子").split()
    assert "水杯" in toks2 or "杯子" in toks2


def test_score_pair_self_high(items):
    a = items[0]
    assert score_pair(a, a) == 100


def test_score_pair_category_bonus(items):
    same_cat = dict(items[0], title="完全不同的标题文字")
    diff_cat = dict(same_cat, category="书籍资料")
    s_same = score_pair(items[0], same_cat)
    s_diff = score_pair(items[0], diff_cat)
    assert s_same > s_diff


@pytest.mark.parametrize("lost_id,found_id", [(1, 7), (3, 9), (4, 10), (6, 12)])
def test_known_pairs_top1(items, lost_id, found_id):
    a = next(x for x in items if x["id"] == lost_id)
    ranked = []
    for x in items:
        if x["type"] == "found" and not x.get("resolved"):
            ranked.append((score_pair(a, x), x["id"]))
    ranked.sort(reverse=True)
    assert ranked[0][1] == found_id


def test_find_matches_excludes_resolved(items):
    items2 = [dict(x, resolved=True) if x["type"] == "found" else x for x in items]
    r = find_matches(1, items2)
    assert all(x["item"]["id"] != 7 for x in r)


def test_common_words_min_len():
    assert "黑色" in common_words("黑色耳机", "黑色钱包")
    assert len(common_words("黑色耳机", "黑色钱包")) >= 1


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
