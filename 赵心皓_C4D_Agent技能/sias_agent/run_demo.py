# -*- coding: utf-8 -*-
"""
端到端演示：用本地模型完成 Level1(对话) / Level2(结构化JSON->地图) / Level3(函数调用Agent)。

用法（先确保 `ollama serve` 已启动且模型已下载）：
    cd 赵心皓_C4D_agent-skill
    python3 -m sias_agent.run_demo
环境变量：
    C4D_MODEL   覆盖模型标签（默认 gemma3:4b）
    OLLAMA_HOST 覆盖本地服务地址
"""
import json
import os
import platform
import time

from . import config, ollama_client
from .agent import run_agent
from .map_renderer import render_map

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE, "logs")
DATA_DIR = os.path.join(BASE, "data")
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


def hr(t=""):
    print("\n" + "=" * 60)
    if t:
        print(t)
        print("=" * 60)


def device_info() -> dict:
    return {
        "os": f"{platform.system()} {platform.mac_ver()[0] if platform.system()=='Darwin' else platform.release()}",
        "machine": platform.machine(),
        "processor": platform.processor() or "Apple Silicon",
        "python": platform.python_version(),
    }


def main():
    hr("C4D 本地 Agent 演示")
    dev = device_info()
    print("设备:", json.dumps(dev, ensure_ascii=False))

    # 0) 自检：本地模型
    models = ollama_client.list_models()
    print("本地已下载模型:", [m.get("name") for m in models] or "（未检测到）")
    print("本次使用模型:", config.MODEL)
    if not models:
        print("\n[!] 未检测到本地模型。请先运行: ollama pull", config.MODEL)
        return

    # ---------- Level 1：基本对话 ----------
    hr("Level 1：本地模型生成 SIAS 介绍")
    t0 = time.time()
    r1 = ollama_client.chat(
        messages=[
            {"role": "system", "content": "你是校园讲解员，用中文回答。"},
            {"role": "user", "content": "请用3~4句话介绍郑州西亚斯学院（SIAS University）。"},
        ],
        temperature=0.4,
    )
    intro = r1["choices"][0]["message"]["content"]
    print(intro)
    print(f"\n[耗时 {r1.get('_wall_time',0):.1f}s] usage={r1.get('usage')}")
    with open(os.path.join(LOG_DIR, "level1_intro.json"), "w", encoding="utf-8") as f:
        json.dump({"intro": intro, "usage": r1.get("usage"),
                   "wall_time_s": r1.get("_wall_time")}, f, ensure_ascii=False, indent=2)

    # ---------- Level 2：结构化 JSON -> 地图 ----------
    hr("Level 2：结构化 JSON 输出 -> 交互式地图")
    from .tools import _search_nearby_locations
    geo = _search_nearby_locations("SIAS 校园地标与周边美食、景点、交通", count=8)
    print("模型原始 JSON 输出（前 600 字）:\n", geo["raw_model_json"][:600])
    print(f"\n解析到 {len(geo['locations'])} 个地点；模型耗时 {geo['model_timing']['wall_time_s']}s")
    map2 = render_map(geo["locations"],
                      out_path=os.path.join(DATA_DIR, "sias_map_level2.html"),
                      title="SIAS 周边地图（Level2 · 结构化输出）",
                      model_label=f"本地模型 {config.MODEL}")
    with open(os.path.join(LOG_DIR, "level2_locations.json"), "w", encoding="utf-8") as f:
        json.dump(geo, f, ensure_ascii=False, indent=2)
    print("地图已生成:", map2)

    # ---------- Level 3：函数调用 Agent ----------
    hr("Level 3：函数调用 Agent（多工具/多步）")
    agent = run_agent(
        "给我生成一个 SIAS University 周边的地图，包含校园地标和周边好吃的地方，"
        "并顺手给其中几个地点补一下天气。",
        log_path=os.path.join(LOG_DIR, "level3_agent_trace.json"),
    )
    print("Agent 最终答复:\n", agent["final_text"])
    print(f"\nAgent 共收集 {len(agent['locations'])} 个地点")
    map3 = render_map(agent["locations"],
                      out_path=os.path.join(DATA_DIR, "sias_map.html"),
                      title="SIAS University 周边地图（本地 Agent 生成）",
                      model_label=f"本地模型 {config.MODEL}")
    print("最终地图已生成:", map3)

    hr("完成")
    print("最终地图:", map3)


if __name__ == "__main__":
    main()
