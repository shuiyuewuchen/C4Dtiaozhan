# -*- coding: utf-8 -*-
"""全局配置：本地 Ollama 服务地址、模型名、路径。"""
import os

# ---- 本地推理服务（Ollama 自带 OpenAI 兼容 API）----
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
CHAT_URL = f"{OLLAMA_HOST}/v1/chat/completions"
TAGS_URL = f"{OLLAMA_HOST}/api/tags"

# ---- 模型名 ----
# 必须与 `ollama list` 中显示的标签一致。
# 设备：Mac mini M4 / 16GB，推荐 4B~5B 级 4-bit 量化模型。
# 若你的设备跑的是其它标签（如 gemma4:e2b / qwen2.5:7b 等），改这里即可。
MODEL = os.environ.get("C4D_MODEL", "gemma4:e4b")

# ---- SIAS University（郑州西亚斯学院）基准点 ----
# 河南省郑州市新郑市人民路东段，WGS-84 近似中心。
SIAS_LAT = 34.4027
SIAS_LON = 113.7489
MAP_DEFAULT_ZOOM = 14

# 模型生成坐标时允许偏离 SIAS 中心的最大距离（度），用于校验/兜底。
# 1 度纬度 ≈ 111km；0.02 度 ≈ 2.2km，足以覆盖校园及周边。
COORD_TOLERANCE = 0.03
