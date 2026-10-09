# 赵心皓_C4D_验证报告

> 每一项都给出「怎么验的、结果是什么、证据在哪」。

## 1. 本地模型真实运行

| 检查项 | 方法 | 结果 | 证据 |
|---|---|---|---|
| Ollama 已安装 | `ollama --version` | ollama version is **0.40.2** | 截图01 |
| 模型已下载 | `ollama list` | **gemma4:e4b**，ID eb2177adf764，9.5 GB | 截图01 |
| 模型规格 | `ollama show gemma4:e4b` | architecture=gemma4，parameters=**8.1B**，context=131072，quant=**nvfp4**，tools，Apache-2.0 | 截图01 |
| 设备 | `sw_vers` | macOS 26.3，Apple M4，16GB，arm64 | 截图01 |
| 离线推理 | 打 `127.0.0.1:11434/v1/chat/completions` | 正常返回中文 | 截图01 |

## 2. 推理速度

proof.sh 实测：**710 tokens / 24.4s = 29.1 tok/s**（另一次 476/14.6 ≈ 32.6 tok/s）。
内存峰值 9.94 GiB，16GB 机器跑满但不爆。证据：截图01 + ollama_serve.log。

## 3. Agent / 函数调用

| 检查项 | 结果 | 证据 |
|---|---|---|
| 模型是否真调了工具 | step1 `search_nearby_locations`；step2 连调 3 次 `get_weather` | `logs/level3_agent_trace.json` |
| 调用次数 | 共 **4 次工具调用**，3 步推理 | 同上 |
| 收集地点 | **8 个**（校园/交通/美食/购物/公园/寺庙/学校） | 同上 + `logs/level2_locations.json` |
| 是否本地完成 | 全程 127.0.0.1，无云端 API | console_run.log |

## 4. 交互地图

| 检查项 | 结果 | 证据 |
|---|---|---|
| 能在浏览器打开 | 双击 `赵心皓_C4D_map.html` 即开 | 截图02 |
| 底图正常渲染 | 高德底图正确显示郑州西亚斯学院周边路网 | 截图02 |
| 标题/来源标注 | 顶部横幅「本地 Agent 生成 · gemma4:e4b」 | 截图02 |
| 三底图切换 | CartoDB / OSM / 高德（右上角图层控件） | HTML 源码 |
| 坐标纠偏 | WGS-84 点同时渲染到高德(GCJ)层 | coordinate.py |

## 5. 已知限制（如实说明）

- CARTO 底图现已需 API key，默认改用高德；国内打开地图需联网取瓦片（模型推理本身仍离线）。
- 小模型生成的地点坐标是「围绕 SIAS 的示意坐标」，不是测绘级精确定位；弹窗中已标注 WGS-84 坐标。
- 公众号文章尚未真正发布（需本人公众号后台权限），交付草稿 + 链接占位。
