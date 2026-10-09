# -*- coding: utf-8 -*-
"""
Agent 工具集（function calling 的“可执行函数”）。

每个工具：
  1) 在 TOOL_SPECS 里给出 OpenAI 格式的 JSON Schema（供本地模型选择调用）；
  2) 在 EXECUTORS 里给出真实的 Python 实现。

注意：search_nearby_locations 的数据来自“本地模型的 JSON 结构化生成”，
     不是硬编码；get_weather 是一个离线可复现的演示工具（不依赖外网），
     返回内容会明确标注为 demo 数据。
"""
import datetime
import json

from . import config, ollama_client

# ----------------------------------------------------------------------------
# 1) 工具的 JSON Schema（告诉本地模型有哪些工具、参数是什么）
# ----------------------------------------------------------------------------
TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "search_nearby_locations",
            "description": "查询 SIAS University（郑州西亚斯学院，位于河南新郑）周边的有意义地点，"
                           "返回结构化的地点列表（名称、经纬度、类别、简介）。当用户要求生成校园周边地图时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "地点主题，如“校园地标与周边美食/景点”"},
                    "count": {"type": "integer", "description": "期望地点数量，默认 8", "default": 8}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "根据经纬度查询某地的（演示用）天气描述。离线、可复现。",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number"},
                    "lon": {"type": "number"},
                    "place_name": {"type": "string"}
                },
                "required": ["lat", "lon"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sias_fact",
            "description": "获取一段关于 SIAS University 郑州西亚斯学院的简介（由本地模型生成）。",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
]

# ----------------------------------------------------------------------------
# 2) 工具实现
# ----------------------------------------------------------------------------
_LANDMARK_SYSTEM = (
    "你是一名熟悉郑州新郑地理的校园导览助手。"
    "只输出合法 JSON，不要输出任何多余文字、不要 markdown 代码块。"
    "输出为一个 JSON 对象：{\"locations\":[ ... ]}，"
    "数组每项包含字段："
    "name(英文/拼音名), name_zh(中文名), category(类别：campus/food/scenic/transport/shopping/sports),"
    "latitude(纬度, float), longitude(经度, float), description(一句中文简介, 20~40字)。"
    "所有地点必须真实位于郑州西亚斯学院(约 34.4027N, 113.7489E) 方圆约 3 公里内，"
    "经纬度给 WGS-84 GPS 坐标，小数点后 4 位。"
)


def _parse_keep_duplicates(s: str):
    """解析 JSON，但保留对象里的重复键（小模型偶尔会输出 {"locations":[...],"locations":[]}，
    标准 json.loads 会用后者覆盖前者导致数据丢失）。
    返回：对象 -> [(key,value), ...]（重复键保留为多个 pair）；数组 -> list。"""
    return json.loads(s, object_pairs_hook=lambda pairs: pairs)


def _obj_keys(node) -> set:
    if isinstance(node, list) and node and all(isinstance(p, tuple) and len(p) == 2 for p in node):
        return {str(k).lower() for k, _ in node}
    return set()


def _is_location_obj(node) -> bool:
    keys = _obj_keys(node)
    if not keys:
        return False
    has_lat = ("latitude" in keys) or ("lat" in keys)
    has_lon = ("longitude" in keys) or ("lon" in keys) or ("lng" in keys)
    return has_lat and has_lon


def _extract_locations(node, out: list):
    """递归遍历（保留重复键的）JSON 树，把所有"看起来像地点"的对象收集出来。"""
    if _is_location_obj(node):
        out.append(dict(node))  # 展示用，重复键取最后一个即可
        return
    if isinstance(node, list):
        if node and all(isinstance(p, tuple) and len(p) == 2 for p in node):
            # 这是一个对象（pair 列表），向下钻每个 value
            for _, v in node:
                _extract_locations(v, out)
        else:
            for item in node:
                _extract_locations(item, out)


def _search_nearby_locations(query: str, count: int = 8) -> dict:
    """让本地模型以结构化 JSON 方式生成地点数据（核心：数据来自本地模型）。"""
    user = (f"主题：{query}。请给出 {count} 个有意义的地点，"
            f"其中务必包含 SIAS University 主校区本身作为第一个点。"
            f"严格输出 {{\"locations\":[ ... ]}} 一层对象，数组直接放地点对象，不要再嵌套、不要重复键。")
    resp = ollama_client.chat(
        messages=[
            {"role": "system", "content": _LANDMARK_SYSTEM},
            {"role": "user", "content": user},
        ],
        json_mode=True,
        temperature=0.3,
    )
    content = resp["choices"][0]["message"]["content"]
    tree = _parse_keep_duplicates(content)
    locations = []
    _extract_locations(tree, locations)
    return {
        "raw_model_json": content,
        "locations": locations,
        "model_timing": {
            "wall_time_s": round(resp.get("_wall_time", 0), 2),
            "usage": resp.get("usage", {}),
        },
    }


def _get_weather(lat: float, lon: float, place_name: str = "") -> dict:
    """离线演示天气：由坐标+日期确定性生成，避免依赖外网天气 API。"""
    rng_seed = int(abs(lat) * 1000 + abs(lon) * 100) + datetime.date.today().toordinal()
    skies = ["晴", "多云", "阴", "多云转晴", "晴间多云"]
    sky = skies[rng_seed % len(skies)]
    temp = 14 + (rng_seed % 12)
    return {
        "place": place_name or f"({lat:.4f},{lon:.4f})",
        "sky": sky,
        "temperature_c": temp,
        "note": "离线演示数据（基于坐标与日期本地生成，非真实气象站观测）",
    }


def _get_sias_fact() -> dict:
    resp = ollama_client.chat(
        messages=[
            {"role": "system", "content": "你是校园讲解员，用中文，80~120 字介绍郑州西亚斯学院(SIAS)。"},
            {"role": "user", "content": "介绍一下郑州西亚斯学院。"},
        ],
        temperature=0.4,
    )
    return {"fact": resp["choices"][0]["message"]["content"].strip()}


EXECUTORS = {
    "search_nearby_locations": _search_nearby_locations,
    "get_weather": _get_weather,
    "get_sias_fact": _get_sias_fact,
}


def dispatch(name: str, arguments: str) -> str:
    """根据模型给出的工具名与参数(JSON字符串)执行工具，返回结果(JSON字符串)。"""
    try:
        args = json.loads(arguments) if arguments else {}
    except json.JSONDecodeError:
        args = {}
    fn = EXECUTORS.get(name)
    if fn is None:
        return json.dumps({"error": f"unknown tool: {name}"}, ensure_ascii=False)
    try:
        result = fn(**args)
    except TypeError as e:
        # 参数不对时，宽松重试（忽略多余参数）
        try:
            import inspect
            sig = inspect.signature(fn)
            filtered = {k: v for k, v in args.items() if k in sig.parameters}
            result = fn(**filtered)
        except Exception as e2:
            result = {"error": f"tool {name} failed: {e2}"}
    except Exception as e:
        result = {"error": f"tool {name} failed: {e}"}
    return json.dumps(result, ensure_ascii=False)
