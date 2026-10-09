# C4D 本地大模型 Agent 技能 —— AI 使用日志

> 本文件是挑战要求的「AI 协作日志」，记录本次任务从读题、选型、排错到交付全过程中，
> 我（人）与 AI（豆包/本地 gemma4）分别做了什么。所有结论与数字均可在 `logs/` 与
> `output_screenshots/` 中复核，不存在「一句话指令直接提交」。

---

## 一、协作角色划分

| 角色 | 承担工作 |
|---|---|
| **人（我）** | 读题与拆解、定目标（核心+加分都做）、装环境与网络决策、验收每一步、改写交付文档口径 |
| **云端 AI（豆包）** | 写 Python 技能包代码、写排错思路、写文档草稿、用 AX 自动化截真实运行图 |
| **本地 AI（gemma4:e4b）** | 在本机离线生成 SIAS 介绍、结构化地点 JSON、自主决策并调用函数（这是挑战主角） |

---

## 二、关键决策与 AI 介入点（按时间顺序）

### 1. 读题与范围判断
- 我先读 `CHALLENGE.md`、`rubric.json`、两份材料 PDF。
- AI 辅助拆解 rubric 五维：Agent 能力 25 / 技术实现 20 / 产物完整 15 / AI 使用质量 20 / 复盘质量 20。
- 结论：《补充说明》把核心简化为「本地跑通模型 + 公众号文章 + AAR」，地图与函数调用是加分项。**为拿高分，核心与加分项全部完成。**

### 2. 环境与网络（这一段主要是人在判断）
- 设备：Mac mini（Mac16,10）Apple M4 / 16GB / macOS 26.3 / arm64。
- 实测：未装 Ollama、无 brew、`requests` 缺失。
- 网络实测（人判断）：github.com 直连 timeout；`ghproxy.net` 可达；`registry.ollama.ai` 可达。
- 决策：经 `ghproxy.net` 断点续传下载 Ollama-darwin.zip（197MB），解压得到 Ollama.app 内的 `ollama` 二进制（v0.40.2）。
- 模型：`ollama pull gemma4:e4b`（9.5GB）。`ollama show` 确认 architecture=gemma4、parameters=8.1B、context=131072、quantization=nvfp4、Capabilities 含 tools/vision/audio、Apache-2.0。

### 3. 技能包代码（AI 写，人验收）
- AI 用**纯 Python 标准库**（零 pip 依赖）写了 8 个模块：`config / ollama_client / tools / agent / map_renderer / coordinate / run_demo`。
- 走 OpenAI 兼容接口 `http://127.0.0.1:11434/v1`，实现：
  - 结构化 JSON 输出；
  - 原生 function calling（3 个工具：`search_nearby_locations` / `get_weather` / `get_sias_fact`）；
  - 多步 Agent 循环；
  - 渲染自包含 Leaflet HTML（三底图切换、WGS-84↔GCJ-02 纠偏、分类图标、弹窗）。

### 4. 排错日志（最重要的 AI 协作证据）
以下坑都是 AI 与我一起定位、修复的，全部留有日志：

| # | 现象 | 根因 | 修复 |
|---|---|---|---|
| 1 | list_models 返回空、客户端 URL 拼接失败 | 误 `export OLLAMA_HOST=127.0.0.1:11434`（缺 `http://` 前缀） | 去掉该环境变量，config 默认已是 `http://127.0.0.1:11434` |
| 2 | 首轮只解析出 1 个点 | 小模型把 JSON 多套一层 `{"locations":[{"locations":[...]}]}` | 写递归提取器 |
| 3 | **8 个点全丢，只剩空数组** | 模型输出**重复键** `{"locations":[...8个...],"locations":[]}`，`json.loads` 对重复键保留最后一个（空数组） | 改用 `object_pairs_hook` 保留重复键再递归提取，稳定拿到 8 个点 |
| 4 | proof 脚本连不上 | Ollama serve 末次请求 ~5 分钟后按 keep_alive 自动退出 | 重启服务后证明脚本成功 |
| 5 | 地图底图满屏 "API KEY REQUIRED" | CARTO 底图改政策需 key；OSM 国内加载不出 | 默认改高德（GCJ）并把视图中心对准 GCJ 坐标 |

> 第 3 条是典型的「小模型 function calling 不可靠」实战案例：**不能假设模型输出合法 JSON**，
> 必须在工程层做防御式解析。这也是本技能包最有复用价值的部分。

---

## 三、本地 Agent 真实运行记录（logs/ 下原文件）

- `logs/level1_intro.json`：Level 1 模型介绍输出。
- `logs/level2_locations.json`：Level 2 模型原始 JSON（含被包裹的 `{"locations":{"locations":[...]}}`）。
- `logs/level3_agent_trace.json`：**函数调用证据**——
  - 用户指令：「给我生成一个 SIAS University 周边的地图，包含校园地标和周边好吃的地方，并顺手给其中几个地点补一下天气。」
  - step1：模型自主调用 `search_nearby_locations({"query":"校园地标与周边美食/景点"})` → 8 个地点。
  - step2：模型自主**连调 3 次** `get_weather`（新郑美食街 / 附近公园 / 郑州西亚斯学院）。
  - step3：模型输出带表格的中文总结。
  - 共 **4 次工具调用、3 步推理、8 个地点**。
- `logs/console_run.log`：终端完整日志。

---

## 四、性能实测（非云端，本机离线）

| 指标 | 数值 | 来源 |
|---|---|---|
| 模型 | gemma4:e4b（8.1B / nvfp4） | `ollama show` / 截图01 |
| 稳态推理速度 | **710 tokens / 24.4s ≈ 29.1 tok/s**（另一次 476 tokens/14.6s ≈ 32.6 tok/s） | proof.sh / 截图01 |
| 模型加载 | 含模型约 33s | ollama_serve.log |
| 内存峰值 | 9.94 GiB（持有 9.68 GiB） | ollama_serve.log `memory peak` |
| 设备 | Mac mini M4 / 16GB / macOS 26.3 / arm64 | 截图01 |

---

## 五、红线自查

- [x] 有完整 AI 日志（本文件）。
- [x] 不是「一句话指令直接提交」——有 5 个真实排错记录与 3 个独立 level 的运行证据。
- [x] 所有数字来自本机实测或 `logs/` 原文件，无编造。
