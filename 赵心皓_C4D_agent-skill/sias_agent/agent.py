# -*- coding: utf-8 -*-
"""
Agent 主循环：展示本地模型的 function calling 与多步推理能力。

流程（以“生成 SIAS 周边地图”为例）：
  用户指令
    -> 本地模型决定调用哪个工具（search_nearby_locations / get_weather / get_sias_fact）
    -> Python 侧执行工具（其中地点数据由本地模型 JSON 生成）
    -> 把工具结果回喂给模型，模型继续决策/总结
    -> 循环直到模型给出最终自然语言答复
全程 trace 落盘，作为“Agent 能力”证据。
"""
import json

from . import config, ollama_client
from .tools import TOOL_SPECS, dispatch


def run_agent(user_query: str, max_steps: int = 6, log_path: str = None) -> dict:
    messages = [
        {"role": "system",
         "content": "你是一个地图助手 Agent。当用户要生成地图时，先调用 search_nearby_locations 取得地点，"
                    "可对若干地点调用 get_weather 补充天气，必要时调用 get_sias_fact。"
                    "拿到足够信息后，用中文给出简短总结，不要编造坐标。"},
        {"role": "user", "content": user_query},
    ]
    trace = []
    final_text = ""
    collected_locations = []
    collected_weather = {}

    for step in range(1, max_steps + 1):
        resp = ollama_client.chat(messages, tools=TOOL_SPECS)
        msg = resp["choices"][0]["message"]
        messages.append(msg)
        tool_calls = msg.get("tool_calls") or []

        step_log = {"step": step,
                    "assistant_content": msg.get("content", ""),
                    "tool_calls": [],
                    "wall_time_s": round(resp.get("_wall_time", 0), 2)}
        trace.append(step_log)

        if not tool_calls:
            final_text = msg.get("content", "")
            break

        for call in tool_calls:
            fn = call["function"]["name"]
            args = call["function"].get("arguments", "{}")
            result_str = dispatch(fn, args)
            step_log["tool_calls"].append({"name": fn, "arguments": args, "result": json.loads(result_str)})

            # 从工具结果中收集地点与天气
            try:
                result_obj = json.loads(result_str)
            except Exception:
                result_obj = {}
            if fn == "search_nearby_locations":
                collected_locations = result_obj.get("locations", collected_locations)
            if fn == "get_weather":
                collected_weather[result_obj.get("place", "")] = result_obj

            messages.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "name": fn,
                "content": result_str,
            })

    # 把天气合并进地点
    for loc in collected_locations:
        key = loc.get("name_zh", loc.get("name", ""))
        for place, w in collected_weather.items():
            if place and (place in key or key in place):
                loc["weather"] = f"{w['sky']} {w['temperature_c']}°C"

    if log_path:
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump({"user_query": user_query, "trace": trace,
                       "final_text": final_text,
                       "locations": collected_locations}, f, ensure_ascii=False, indent=2)

    return {"final_text": final_text, "locations": collected_locations, "trace": trace}
