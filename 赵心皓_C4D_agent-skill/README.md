# 赵心皓_C4D_agent-skill —— 本地 Gemma 地图 Agent

> 在你自己的 Mac / PC 上，用本地开源大模型（Gemma）驱动一个会"自己决定调用工具、生成结构化数据、再渲染交互地图"的 Agent。
> 全程不花一分钱 API 费用，数据不离开本机。

## 它能做什么

一条用户指令："给我生成 SIAS University 周边的地图"，Agent 自动完成：

1. **本地模型对话**（Level 1）—— 生成一段西亚斯学院介绍；
2. **结构化 JSON 输出**（Level 2）—— 模型以 `json_object` 模式吐出地点数组（名称/经纬度/类别/简介）；
3. **原生函数调用**（Level 3）—— 模型自己决策调用 `search_nearby_locations` / `get_weather` / `get_sias_fact`，
   Python 侧真实执行工具并把结果回喂，多步推理直到给出总结；
4. **渲染 Leaflet 交互地图** —— 可缩放、可点击、多底图切换（CartoDB / OSM / 高德），按类别着色。

## 目录结构

```
sias_agent/
  config.py        # 模型名/服务地址/SIAS 坐标（改这里适配你的机器）
  ollama_client.py # 仅用标准库的 OpenAI 兼容客户端
  tools.py         # 工具的 JSON Schema + 本地实现（地点数据由本地模型生成）
  agent.py         # function-calling 多步 Agent 主循环
  map_renderer.py  # 地点数据 -> 自包含 Leaflet HTML
  coordinate.py    # WGS-84 <-> GCJ-02 坐标纠偏
  run_demo.py      # 端到端入口（Level1->2->3）
logs/              # 每次运行的模型原始输出与 Agent trace（证据，见 logs/README.md）
data/              # 生成的地图 HTML
```

## 三张地图文件的区别

| 文件 | 是什么 |
|---|---|
| `../赵心皓_C4D_map.html`（根目录） | **最终交付入口**，双击这个即可；内容等于 `data/sias_map.html` |
| `data/sias_map.html` | Level 3 最终地图：8 个地点 + 天气，三底图切换 |
| `data/sias_map_level2.html` | Level 2 早期版：只有地点、无天气，留作过程对照 |

## 快速事实

- 模型：gemma4:e4b（8.1B / nvfp4 量化 / 9.5GB，支持 function calling）
- 设备：Mac mini M4 / 16GB / macOS arm64，实测约 29 tok/s
- 依赖：Python 3.9+ 标准库，零 pip 安装

## 如何复现

```bash
# 1) 安装并启动 Ollama（见同级《教学说明》）
ollama serve

# 2) 拉取一个本地模型（按你的设备选）
ollama pull gemma4:e4b        # 16GB 内存笔记本推荐
# ollama pull gemma4:e2b     # 8GB 内存
# ollama pull qwen2.5:7b     # 任何你喜欢的开源模型都能跑

# 3) 设置本次使用的模型（必须与上面 pull 的标签一致）
export C4D_MODEL=gemma4:e4b

# 4) 运行端到端演示（零第三方 pip 依赖，Python 3.9+ 即可）
cd 赵心皓_C4D_agent-skill
python3 -m sias_agent.run_demo
```

跑完后打开 `sias_agent/data/sias_map.html` 即可看到交互式地图。

## 设计要点 / 为什么这么写

- **零 pip 依赖**：HTTP 用 `urllib`，地图手写 Leaflet，别人 `python3` 直接能跑，降低复现门槛。
- **数据确由本地模型生成**：`tools._search_nearby_locations` 把地点 prompt 发给本地模型并强制 JSON，
  不手写地点 JSON；`logs/level2_locations.json` 里保留了模型原始输出作为证据。
- **坐标兜底而非伪造**：模型可能幻觉出离谱坐标，`map_renderer` 做了范围校验并吸附到 SIAS 附近，
  既保证地图可用，又不"替模型编造"。
- **坐标纠偏**：国内高德底图用 GCJ-02，模型输出是 WGS-84，渲染高德层时做了公开公式转换，避免标记点偏移。
