# -*- coding: utf-8 -*-
"""
重复键 JSON 踩坑与修复 —— 可复现证据。

背景：小模型（gemma4:e4b）在 function calling 时，偶发输出**重复键**：
    {"locations":[...8个地点...],"locations":[]}
标准 json.loads 对重复键"保留最后一个"，于是 8 个地点被静默吞成空数组。
本脚本复现：左（标准解析，错误）vs 右（object_pairs_hook，修复）。

运行：python3 logs/duplicate_key_fix_demo.py
"""
import json

# 模拟模型真实输出：8 个地点在前、空数组在后（重复键 locations）
BROKEN = (
    '{"locations":['
    '{"name":"郑州西亚斯学院"},'
    '{"name":"新郑客运站"},'
    '{"name":"新郑美食街"},'
    '{"name":"附近购物中心"},'
    '{"name":"附近公园"},'
    '{"name":"主要交叉口"},'
    '{"name":"附近寺庙"},'
    '{"name":"周边学校"}'
    '],"locations":[]}'
)

print("=== 模型原始输出（含重复键 locations）===")
print(BROKEN[:80], "...\n")

# 修复前：标准 json.loads —— 重复键保留最后一个（空数组），8 个点全丢
bad = json.loads(BROKEN)
print("[修复前] 标准 json.loads -> 解析到地点数:", len(bad["locations"]), "(错误！应为 8)")

# 修复后：object_pairs_hook 把每个 JSON 对象都保留为 (key,value) 列表，不丢重复键
pairs = json.loads(BROKEN, object_pairs_hook=lambda p: p)

def is_object(node):
    """object_pairs_hook 下，JSON 对象是 list[(key,value)]。"""
    return isinstance(node, list) and node and isinstance(node[0], (tuple, list)) and len(node[0]) == 2

def extract_locations(node):
    """递归找到任意名为 locations 且值为非空地点数组。"""
    if is_object(node):                      # 这是一个对象（pairs）
        for key, val in node:
            if key == "locations" and isinstance(val, list) and val and is_object(val[0]):
                return val
            found = extract_locations(val)
            if found:
                return found
    elif isinstance(node, list):              # 这是一个数组
        for item in node:
            found = extract_locations(item)
            if found:
                return found
    return None

good = extract_locations(pairs)
# 把 pairs 形式的地点对象转回普通 dict 方便打印
good_dicts = [dict(p) for p in good]
print("[修复后] object_pairs_hook + 递归 -> 解析到地点数:", len(good_dicts), "(正确)")
print("         地点:", [x["name"] for x in good_dicts])
