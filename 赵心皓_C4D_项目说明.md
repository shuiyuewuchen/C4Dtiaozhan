# 赵心皓_C4D 项目说明

> 本文件是仓库的**技术向项目说明**。想看叙事型的制作过程，请看根目录 `README.md`（= 公众号文章）。
> 公众号已发布版：见 `赵心皓_C4D_公众号链接.txt`。

## 1. 这是什么

在一台 **Mac mini M4 / 16GB / macOS 26.3** 上，**完全离线**跑一个开源大模型（`gemma4:e4b`，8.1B，nvfp4 量化），
让它具备 **Agent / 函数调用**能力，并自主生成一张 **郑州西亚斯学院（SIAS）周边交互式地图**。

全程不调用任何云端模型 API。

## 2. 目录结构

```
C4Dtiaozhan/
├── README.md                        # 公众号文章（叙事版，本仓首页）
├── 赵心皓_C4D_项目说明.md             # 本文件（技术版说明）
├── 赵心皓_C4D_方案设计.md             # 架构、选型理由、工程护栏、Non-goals
├── 赵心皓_C4D_验证报告.md             # 验证项、复现步骤、期望输出
├── 赵心皓_C4D_AAR.md                 # 复盘：预期 vs 实际、踩坑与改进
├── 赵心皓_C4D_教学说明.md             # 教学用法与学生常见误区
├── 赵心皓_C4D_公众号文章草稿.md        # 文章草稿留档
├── 赵心皓_C4D_公众号链接.txt           # 已发布的公众号文章地址
├── 赵心皓_C4D_拿来说明.md              # 交付物清单与拿取指引
├── 赵心皓_C4D_map.html               # 最终交互地图（根目录入口）
├── 赵心皓_C4D_output_screenshots/    # 运行证明与地图截图
│   ├── 01_本地运行证明_模型版本设备速度.png
│   └── 02_SIAS交互式地图_全景.png
└── 赵心皓_C4D_agent-skill/           # 完整可复跑技能包
    ├── README.md                     # 技能包运行说明
    ├── requirements.txt              # 依赖（零第三方依赖）
    ├── data/
    │   ├── sias_map.html             # Level 2/3 生成的地图
    │   └── sias_map_level2.html      # Level 2 单独产出
    ├── logs/                         # 各档运行日志与留档
    └── sias_agent/                   # 源码
        ├── run_demo.py               # 入口（三档）
        ├── agent.py                  # 多步循环
        ├── tools.py                  # 3 个工具函数
        ├── ollama_client.py          # urllib 零依赖客户端
        ├── map_renderer.py           # 渲染自包含 Leaflet HTML
        ├── coordinate.py             # WGS-84 ↔ GCJ-02 纠偏
        └── config.py                 # 服务地址 / 模型名 / 基准点
```

## 3. 快速开始

环境要求：macOS，本地装有 **Ollama**，内存 ≥ 16GB。

```bash
# 1) 拉取模型（标签必须与 config.py 中一致）
ollama pull gemma4:e4b

# 2) 启动本地推理服务
ollama serve

# 3) 进入技能包并运行
cd 赵心皓_C4D_agent-skill
python3 -m sias_agent.run_demo
```

运行后：
- 地图写入 `data/sias_map.html`
- 三档日志写入 `logs/`

看地图：双击根目录 `赵心皓_C4D_map.html`（或 `data/sias_map.html`），右上角可切换
CartoDB / OpenStreetMap / 高德 三种底图（国内建议高德，默认）。

> 完整验证步骤与期望输出见 `赵心皓_C4D_验证报告.md` 第 5 节「一键复现」。

## 4. 模型与设备

| 项目 | 值 |
|---|---|
| 设备 | Mac mini M4 / 16GB / macOS 26.3 |
| 运行时 | Ollama 0.40.2 |
| 模型标签 | `gemma4:e4b`（可用环境变量 `C4D_MODEL` 覆盖） |
| 参数量 / 量化 | 8.1B / nvfp4，约 9.5GB |
| 客户端 | Python 标准库 `urllib`（无第三方依赖） |
| 服务地址 | `http://127.0.0.1:11434`（OpenAI 兼容 API） |
| 地图渲染 | Leaflet 单文件 HTML（自包含，双击即开） |
| 坐标系 | WGS-84 生成 + GCJ-02 纠偏（避免高德底图偏移约 500m） |

## 5. 三档能力

| 档位 | 做什么 | 产物 |
|---|---|---|
| Level 1 | 模型直接生成 SIAS 中文介绍 | `logs/level1_intro.json` |
| Level 2 | 按结构化 schema 输出周边地点 JSON | `logs/level2_locations.json` + `data/sias_map_level2.html` |
| Level 3 | **函数调用 Agent**：自主决定查地点 → 补天气 → 总结 | `logs/level3_agent_trace.json` + `data/sias_map.html` |

## 6. 边界说明

- 天气为**离线演示数据**，地点坐标为围绕 SIAS 的示意坐标，**非**测绘级或权威数据。
- 推理全程本地；仅地图瓦片需联网获取，不向云端模型 API 发送任何内容。
- 详细非目标（Non-goals）见 `赵心皓_C4D_方案设计.md` 第 6 节。
