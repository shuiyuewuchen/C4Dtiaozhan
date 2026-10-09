# 赵心皓_C4D_教学说明（怎么复现）

> 目标：换一台 Mac，按下面步骤从零跑通。

## 前置
- macOS arm64（Apple Silicon），建议 ≥16GB 内存。
- 已装 Xcode Command Line Tools（自带 python3）。

## 步骤

### 1. 装 Ollama
```bash
# 若 github 直连不通，走镜像下载 Ollama-darwin.zip，解压后取二进制
OLLAMA=/path/to/Ollama.app/Contents/Resources/ollama
"$OLLAMA" --version    # 应输出 0.40.2
```

### 2. 拉模型
```bash
"$OLLAMA" pull gemma4:e4b     # 约 9.5GB
"$OLLAMA" show gemma4:e4b     # 确认 8.1B / nvfp4 / tools
```

### 3. 起服务（另开一个终端，保持运行）
```bash
export OLLAMA_HOST=http://127.0.0.1:11434   # 注意必须带 http://
"$OLLAMA" serve
```

### 4. 跑 Agent 技能包
```bash
cd 赵心皓_C4D_agent-skill
unset OLLAMA_HOST          # 避免旧环境变量干扰（代码里已带 http://）
export C4D_MODEL=gemma4:e4b
python3 -m sias_agent.run_demo
```
运行后会在 `data/` 生成 `sias_map.html`，并在 `logs/` 留下三档日志。

### 5. 看地图
双击 `赵心皓_C4D_map.html`（或 `data/sias_map.html`）。
- 右上角可切 CartoDB / OpenStreetMap / 高德 三种底图。
- 国内建议用高德（默认）。点标记看弹窗详情。

## 常见问题
- **连不上服务**：确认 `ollama serve` 在跑；空闲 5 分钟会自动退出，重起即可。
- **地点解析为空**：小模型偶发输出不合法 JSON，技能包已做重复键/递归兜底；仍失败就重跑一次。
- **地图底图空白**：OSM 国内慢，切高德。
