# -*- coding: utf-8 -*-
"""感知哈希（aHash）与汉明距离：用于以图搜物"""
from PIL import Image, ImageOps


def ahash(path):
    """8x8 平均哈希，返回 64 位整数值哈希"""
    img = Image.open(path).convert("L").resize((8, 8), Image.LANCZOS)
    pixels = list(img.getdata())
    avg = sum(pixels) / len(pixels)
    bits = 0
    for p in pixels:
        bits = (bits << 1) | (1 if p > avg else 0)
    return bits


def hamming(h1, h2):
    return bin(h1 ^ h2).count("1")
