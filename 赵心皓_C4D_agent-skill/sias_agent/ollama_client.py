# -*- coding: utf-8 -*-
"""
极简 OpenAI 兼容客户端（仅用标准库 urllib，零第三方依赖）。

对接本地 Ollama：
  POST {OLLAMA_HOST}/v1/chat/completions
支持：messages、tools(原生函数调用)、response_format(json_object 结构化输出)、
以及返回 usage / timing 信息用于性能记录。
"""
import json
import time
import urllib.request
import urllib.error

from . import config


class OllamaError(RuntimeError):
    pass


def _post(url: str, payload: dict, timeout: int = 600) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise OllamaError(f"HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:500]}")
    except urllib.error.URLError as e:
        raise OllamaError(
            f"无法连接本地推理服务 {url}：{e.reason}\n"
            f"请先启动 `ollama serve`（或打开 Ollama.app）。"
        )
    dt = time.time() - t0
    out = json.loads(body)
    out["_wall_time"] = dt
    return out


def chat(messages, tools=None, model=None, json_mode=False, temperature=0.2,
         timeout=600) -> dict:
    """一次对话补全。返回完整响应 dict（含 choices / usage / _wall_time）。"""
    model = model or config.MODEL
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    if json_mode:
        # Ollama OpenAI 兼容接口：强制返回合法 JSON
        payload["response_format"] = {"type": "json_object"}
    return _post(config.CHAT_URL, payload, timeout=timeout)


def list_models() -> list:
    """列出本地已下载模型（用于截图与自检）。"""
    try:
        with urllib.request.urlopen(config.TAGS_URL, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("models", [])
    except Exception:
        return []
