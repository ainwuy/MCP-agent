# 智能出行 Agent（LangGraph + MCP + 高德地图）

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一个基于 **LangGraph ReAct Agent** + **MCP（Model Context Protocol）** 的智能出行助手。
接入高德开放平台，支持地点搜索、周边查询、多模式路径规划、天气实况与预报、行程存档。

用自然语言提问（如「故宫附近 500 米有什么酒店」「从北京西站到故宫坐地铁怎么走」），
Agent 会自主判断该调用哪些工具、按什么顺序调用，最后用人话给出答案。

---

## ✨ 功能特性

| 能力 | 说明 |
|---|---|
| 🗺 地理编码 | 中文地址 → 经纬度坐标 |
| 🔍 地点搜索 | 按关键词找景点 / 酒店 / 餐厅 / 车站等 |
| 📍 周边搜索 | 查某个坐标点附近 N 米内有什么 |
| 🚗 路径规划 | 驾车 / 步行 / 公交地铁 / 骑行，含距离与耗时 |
| 🌤 天气实况 | 当前温度、天气状况、湿度、风力风向 |
| 📅 天气预报 | 未来 3-4 天，白天与夜间分开 |
| 💾 行程存档 | 把规划结果写入本地文件 |
| 🧠 ReAct 推理 | LLM 自主编排多步工具调用 |
| 💬 多轮记忆 | 基于 `thread_id` 的会话上下文 |

---

## 🏗 技术架构

```
   用户 ──▶ Vue3 前端 (:5173)
              │ POST /chat {message}
              ▼
        FastAPI 后端 (:8000)
              │
              │ LangGraph ReAct Agent
              │ create_agent(model, tools, system_prompt, checkpointer)
              │ InMemorySaver 负责多轮记忆
              ▼
        MultiServerMCPClient  ←── 读 servers_config.json
              │
              │  stdio 传输（每个 server 一个子进程）
      ┌───────┼───────────┐
      ▼       ▼           ▼
  amap_server  weather_server  write_server
  (高德地图)    (高德天气)      (本地文件)
   5 个工具      3 个工具        1 个工具
```

**关键点**：三个 MCP Server 各自是独立的子进程，通过 stdio 与客户端通信。
新增工具只需在对应 server 里加一个 `@mcp.tool()` 函数 + 在配置里注册，
**Agent 主逻辑一行都不用改**。

---

## 📦 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + Vite + markdown-it |
| 后端 | FastAPI + Uvicorn |
| Agent | LangGraph `create_agent`（ReAct 范式）|
| 工具协议 | MCP (Model Context Protocol) + stdio 传输 |
| LLM | 通义千问（`qwen-plus` / `qwen3-max`）|
| 数据源 | 高德开放平台（地图 API + 天气 API）|

---

## 🚀 快速开始

### 1. 申请 API Key

**通义千问（必需）**
1. 打开 https://bailian.console.aliyun.com/
2. 右上角头像 → API-KEY → 创建
3. 得到形如 `sk-xxxxxx` 的 Key

**高德开放平台（必需）**
1. 打开 https://console.amap.com/
2. 完成**个人认证**（不认证只能拿测试 Key，调不通）
3. 应用管理 → 创建新应用 → 添加 Key
4. ⚠️ **服务平台必须选「Web 服务」**（选成「Web端(JS API)」会报 `INVALID_USER_KEY`）

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填入你的 Key：

```bash
# Windows
copy .env.example .env
# Linux / macOS
cp .env.example .env
```

```env
MODEL=qwen-plus
DASHSCOPE_API_KEY=sk-你的通义千问Key
AMAP_API_KEY=你的高德Web服务Key
```

> `.env` 含密钥，已被 `.gitignore` 排除，**不要提交到版本库**。

> `MODEL` 可选项：`qwen-plus`（推荐，性价比好）/ `qwen-turbo`（最快最省，但工具调用偏弱）
> / `qwen3-max`（最强，复杂任务用）。不确定哪个可用就跑 `python check_models.py` 实测。

### 3. 安装依赖

```bash
# 后端
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 前端
cd front/mcp_agent
npm install
```

### 4. 启动

```bash
# 终端 1：后端（务必先激活 venv，见下方"已知坑"）
.venv\Scripts\python.exe api_server.py     # 监听 :8000

# 终端 2：前端
cd front/mcp_agent && npm run dev           # 监听 :5173
```

打开 http://localhost:5173/ 开始对话。

---

## 🛠 MCP 工具清单（共 9 个）

| 工具 | Server | 功能 | 关键参数 |
|---|---|---|---|
| `geocode` | amap | 地址 → 经纬度 | `address`, `city` |
| `poi_search` | amap | 关键词搜地点 | `keyword`, `city`, `types` |
| `poi_around` | amap | 周边搜地点 | `location`(坐标), `keyword`, `radius` |
| `route` | amap | 路径规划（需坐标）| `origin`, `destination`, `mode` |
| `route_by_address` | amap | 路径规划（直接给地名）| `origin_name`, `destination_name`, `mode` |
| `query_weather` | weather | 当前实况天气 | `city`（支持中文）|
| `query_weather_forecast` | weather | 未来 3-4 天预报 | `city`（支持中文）|
| `get_weather_tips` | weather | 季节养生贴士 | `season` |
| `write_file` | write | 写入本地文件 | `content` |

**交通方式**：`driving`(驾车) / `walking`(步行) / `transit`(公交地铁) / `bicycling`(骑行)

**常用 POI 类型码**：`050000`=餐饮 `100000`=住宿 `110000`=风景名胜 `150000`=交通设施

---

## 📁 项目结构

```
mcp_agent/
├── api_server.py          # FastAPI 后端，Agent 入口（前端用这个）
├── client.py              # CLI 聊天版（不起 HTTP 服务）
├── client_simple.py       # 单次函数调用示例
├── servers_config.json    # MCP 服务器注册表
├── agent_prompts.txt      # System Prompt（工具使用规则）
├── .env                   # 环境变量（不要提交到 git）
├── requirements.txt
│
├── amap_server.py         # 🆕 自建：高德地图 MCP Server（5 工具）
├── weather_server.py      # 天气 MCP Server（高德天气 API，3 工具）
├── write_server.py        # 文件写入 MCP Server（1 工具）
│
├── check_models.py        # 模型可用性诊断（换 Key 后跑一次）
├── test_amap.py           # 高德工具的函数级测试
│
├── output/                # write_file 的落盘目录
└── front/mcp_agent/       # Vue3 前端
    └── src/components/ChatBox.vue
```

---

## 🎯 使用示例

| 提问 | Agent 的调用链 |
|---|---|
| 故宫附近 500 米有什么酒店 | `geocode` → `poi_around` |
| 北京有哪些值得去的景点 | `poi_search` |
| 从北京西站到故宫怎么走 | `route_by_address` |
| 从北京西站到故宫坐地铁 | `route_by_address(mode=transit)` |
| 北京今天天气怎么样 | `query_weather` |
| 明天去故宫玩天气如何 | `query_weather_forecast` |
| 把这趟行程写进文件 | `write_file` |
| 查天气 + 找酒店 + 存行程 | 三个工具串联（复合任务）|

---

## 🔑 设计要点

### 1. 工具粒度的权衡

同时提供两种粒度，让 Agent 在「自主编排」和「一次成功」之间取得平衡：

| 类型 | 工具 | 优点 | 缺点 |
|---|---|---|---|
| **细粒度** | `geocode` + `route` | 体现 ReAct 多步规划能力 | LLM 可能调错，成功率略低 |
| **粗粒度** | `route_by_address` | 内部自动串联，一次调用成功 | 不够「Agent」 |

### 2. Prompt 工程

`agent_prompts.txt` 里的关键约束（每一条都是踩坑后加的）：

- **立即调用工具**，不要先追问
- **合理默认值直接用**（用户说"附近 500 米"就传 500，别反问"要多大范围"）
- **禁止编造**景点 / 酒店 / 天气数据
- **明确能力边界**：用户问"能不能订…"时，如实说明无法代替下单

### 3. 自建 MCP Server 的四条铁律

1. **docstring 是给 LLM 看的**——要写清「适用于什么场景」，写得含糊工具永远不会被选中
2. **出错返回错误文本，不要抛异常**——抛异常会中断 ReAct 循环；
   返回 `⚠️ xxx` 让 LLM 能看到错误并自我纠错
3. **stdio 模式下不能用 `print()`**——stdout 是 MCP 协议通道，
   `print` 会污染协议流导致服务崩溃，日志必须走 stderr
4. **未实现的占位用 `raise NotImplementedError`，不要用 `...`**——
   `...` 是合法的 Ellipsis 对象，不报错但函数会**隐式返回 None**，极难排查

### 4. 天气数据源选型

早期用 OpenWeather，后迁移到高德天气 API：

| 维度 | OpenWeather | 高德天气 |
|---|---|---|
| 城市名 | 仅英文（LLM 要自己翻译）| ✅ 支持中文 |
| 免费额度 | 60 次/分钟 | ✅ 30 万次/天 |
| 预报 | 需额外接口 | ✅ 同接口 `extensions=all` |
| 精度 | 整数 | ✅ 有 `temperature_float` 等 |

---

## 🐛 踩坑记录

按「报错信息 → 真实原因」排列，**每一条都是报错指向的方向 ≠ 真正的故障点**：

| # | 报错 | 真实原因 | 修法 |
|---|---|---|---|
| 1 | `Failed to fetch` | 跑的是 CLI 版 `client.py`，没监听 8000 端口 | 前端场景要用 `api_server.py` |
| 2 | `401 InvalidApiKey` | Key 在控制台轮换后忘记回填 `.env` | 拿新 Key 写到 `.env` 并**重启** |
| 3 | `400 InvalidParameter: url error` | **模型名不存在**（如 `qwen3.8-max`），DashScope 伪装成 URL 错误 | 跑 `check_models.py` 实测可用模型名 |
| 4 | `MCP 连接失败: TaskGroup` | `if __name__ == "&#8203;main__"` 里混入了 **HTML 实体字面字符**（从网页复制代码带入），`mcp.run()` 永不执行 | 删掉 `&#8203;` 这 7 个字符 |
| 5 | 工具调用了但 AI 答非所问 | 函数末尾的 `...` 占位符**不报错但隐式返回 None** | 补完实现，或改用 `raise NotImplementedError` |
| 6 | MCP 子进程 `ModuleNotFoundError` | `servers_config.json` 里 `"command": "python"` 依赖 PATH，未激活 venv 时解析到系统 Python | 激活 venv 后启动，或把 command 改成 venv 的绝对路径 |
| 7 | `LangGraphDeprecatedSinceV10` | `create_react_agent` 已迁移到 `langchain.agents.create_agent` | 改 import **和参数名** `prompt=` → `system_prompt=` |

### 关于第 4 条（最隐蔽的一个）

从网页复制 Python 代码时，页面上的零宽空格可能被渲染成 HTML 实体 `&#8203;` 显示，
Ctrl+C 拿到的是**这 7 个 ASCII 字符本身**（`& # 8 2 0 3 ;`），不是真正的零宽字符。

落到文件里变成 `if __name__ == "&#8203;main__":`，这个字符串永远不等于 `__main__`，
`if` 永不成立 → `mcp.run()` 永不执行 → 子进程启动后什么都不做直接退出 →
客户端读到 EOF 报 `Connection closed`。

⚠️ **常规「扫非 ASCII 字符」检测不到它**，因为这 7 个字符的 `ord()` 都 < 128。
正确检测方式：`grep '_name__\s*==\s*"_'` 看能否精确匹配。

---

## 🔧 实用脚本

```bash
# 模型可用性诊断（换 Key / 换环境后跑一次）
.venv\Scripts\python.exe check_models.py

# 高德工具的函数级测试（脱离 MCP，直接测 HTTP + 解析逻辑）
.venv\Scripts\python.exe test_amap.py
```

---

## 📄 说明

- 本项目为**学习 / 演示用途**，数据源均使用各平台的免费额度
- `.env` 含 API Key，**不要提交到版本库**
- Agent **不具备下单能力**（订机票、订酒店等需真实支付与合规授权），
  它的定位是「行程参谋」而非「代办」

---

## 🙏 数据源

- [高德开放平台](https://lbs.amap.com/) — 地图 API + 天气 API
- [阿里云百炼](https://bailian.console.aliyun.com/) — 通义千问大模型

## 📜 License

[MIT](LICENSE) © 2026 [ainwuy](https://github.com/ainwuy)
