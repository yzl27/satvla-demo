# SatVLALab 演示系统

> 面向卫星影像情报分析的多智能体系统演示项目：三栏战术工作台前端 + FastAPI 桥接 + 五阶段推理流水线。本仓库只含代码，Python 环境与模型权重按 `environment.yaml` / `requirements.txt` + `download_weights.sh` 联网安装。

## 项目简介

输入一张遥感/监控图像，系统自动完成**图像质量增强 → 开放词表目标检测 → 目标局部精细分析 → 情报检索 → SOAP 报告生成**的完整链路，并通过前端实时展示每个阶段的推理过程与产物。

核心能力：

- **图像质量增强**：去雾（DehazeFormer）/ 去噪、去雨、去模糊（Restormer）
- **开放词表目标检测**：GroundingDINO（舰船/建筑/车辆/飞机等类别可配）
- **目标精细分析**：裁剪 + Real-ESRGAN 超分 + 灰度/二值化
- **情报检索**：阶段四提炼关键词，Tavily 联网检索（RAG）
- **SOAP 报告**：五阶段汇总生成结构化情报报告
- **实时可视化**：前端工作流图逐阶段高亮、日志流、产物图片展示

## 系统架构

```
浏览器 (:5174) ── 三栏战术工作台（React + Vite + ReactFlow）
      │  WebSocket /ws/mission（日志流、工作流图、报告）
      │  HTTP 静态资源（workspace 产物图片、Doc*.json）
      ▼
api_bridge.py (:8000, FastAPI) ──── 桥接层
      │  收到"执行"指令 → 启动 run.py 子进程 → 逐行解析推送
      ▼
run.py → engine/state_machine.py ──── 推理层（五阶段流水线）
      ├─ 阶段一 全局质检员：图像预处理 + 检测 → Doc1_Global.json
      ├─ 阶段二 战术指挥官：目标优先级排序、裁剪队列 → Doc2_Queue.json
      ├─ 阶段三 局部特种兵：Top 目标裁剪/超分/二值化 → Doc3_Details.json
      ├─ 阶段四 情报提炼官：关键词提炼 + 联网检索 → Doc4_Search.json
      └─ 阶段五 首席报告官：汇总生成 → FINAL_SOAP_REPORT.txt
      ▼
workspace/task_<时间戳>/（全部中间与最终产物）
```

技术栈：Python 3.10 + PyTorch 2.0.1 (CUDA 11.8) + GroundingDINO + Real-ESRGAN + Restormer + DehazeFormer + Ollama (Qwen3.5:9b) | React 18 + Vite 5 + TypeScript + Tailwind + React Flow + Zustand

## 目录结构

```
satvla-demo/
├── multiagent/           # 推理流水线 + 桥接服务（代码；权重需 download_weights.sh 下载）
│   ├── run.py            # 流水线总入口
│   ├── api_bridge.py     # FastAPI 桥接（WebSocket + 静态资源）
│   ├── engine/           # state_machine.py 五阶段主控 / tool_use.py 工具调度
│   ├── vlm/              # VLM 调用与 JSON 解析（Ollama）
│   ├── memory/           # 各阶段提示词
│   ├── tools/            # DehazeFormer / Restormer / GroundingDINO / Real-ESRGAN / OpenCV / RAG
│   │                     #   （含预编译 GroundingDINO CUDA 扩展 _C.so，要求 Python 3.10 + torch 2.0.1+cu118）
│   └── workspace/        # 运行时任务产物（自动生成）
├── frontend-demo/        # React 前端（三栏工作台）
├── environment.yaml      # conda 环境清单（含 CUDA 版 torch）
├── requirements.txt      # Python pip 依赖清单（版本已锁定）
├── download_weights.sh   # 模型权重下载脚本（自动放到位）
├── docs/                 # 项目详细文档（架构/数据流/后端流程/启动指南）
├── setup.sh / start.sh / stop.sh   # 一键安装 / 启动 / 停止
├── DEPLOY.md             # 部署说明（环境要求、FAQ 排查）
└── README.md             # 本文件
```

## 快速开始

```bash
git clone https://github.com/yzl27/satvla-demo.git && cd satvla-demo
bash setup.sh      # 仅一次：建 conda 环境 + 装依赖 + 下权重 + 装 Ollama/模型 + npm install
                   # （联网下载约 12GB，耗时取决于网速）
bash start.sh      # 启动 → 浏览器打开 http://localhost:5174
```

不想用 setup.sh 时，也可手动按环境清单安装：`conda env create -f environment.yaml && bash download_weights.sh`。

界面操作：左栏选推理引擎架构 → 上传图片或使用默认测试图 → 点「执行」→ 中间栏实时显示五阶段工作流进度 → 完成后右栏展示 RAG 检索结果与 SOAP 报告。

> 硬件要求：Linux x86_64、NVIDIA 显卡（显存 ≥16GB、驱动 ≥525）、conda、Node ≥18、能联网。详见 DEPLOY.md。

## 文档索引

| 文档 | 内容 |
|---|---|
| [DEPLOY.md](DEPLOY.md) | 部署说明：环境要求、安装步骤、FAQ 排查（9 条常见问题） |
| [docs/multiagent与frontend-demo项目详细介绍.md](docs/multiagent与frontend-demo项目详细介绍.md) | 项目定位、五阶段工作流、目录结构、技术栈详解 |
| [docs/frontend-demo架构与数据流详解.md](docs/frontend-demo架构与数据流详解.md) | 前端三栏布局、WebSocket 数据流、消息类型、阶段高亮逻辑 |
| [docs/multiagent后端流程与数据流详解.md](docs/multiagent后端流程与数据流详解.md) | 后端五阶段内部流程、工具调度、日志格式解析 |
| [docs/前端启动指南与常见问题.md](docs/前端启动指南与常见问题.md) | 前端启动步骤与常见问题 |
| [frontend-demo/README.md](frontend-demo/README.md) | 前端 3.0 功能要点与源码结构 |

## 常用自定义

- **检测类别**（阶段二）：`multiagent/tools/GroundingDINO/run_detect.py` 中 `TEXT_PROMPT`
- **VLM 模型**：`multiagent/vlm/vlm_utils.py` 中 `MODEL_NAME`（换模型需先 `ollama pull`）
- **RAG 搜索**：环境变量 `TAVILY_API_KEY`（未配置时返回占位结果）；申请地址 https://tavily.com
- **默认测试图**：`multiagent/data/100000007.png`
