# SatVLALab Frontend 3.0 Demo

面向 **SatVLALab / multiagent** 的可视化演示前端：三栏战术工作台、节点工作流图、RAG 与 SOAP 展示。默认 UI 与部分选项来自 `mockData.ts`；**在 `multiagent` 推理真实运行时**，通过 **`api_bridge.py`（FastAPI，默认端口 8000）** 拉取日志与任务产物，与纯静态演示混合使用。

---

## 技术栈

| 类别 | 选用 |
|------|------|
| 构建 | Vite 5、TypeScript |
| UI | React 18、Tailwind CSS |
| 状态 | Zustand（`useWorkflowStore`：WebSocket + 日志解析） |
| 流程图 | React Flow、Dagre（自动布局） |

---

## 与后端如何协作（必读）

| 通道 | 地址（默认） | 作用 |
|------|----------------|------|
| 开发服务器 | `http://localhost:5174` | 仅提供页面与静态资源（Vite） |
| API 桥 | `http://localhost:8000` | 挂载 `workspace`、默认测试图等；**同源 HTTP 拉图片 / `Doc*.json`** |
| WebSocket | `ws://localhost:8000/ws/mission` | 点击执行后推送 `run.py` 日志流，驱动阶段节点、任务 ID、主图与胶片条等 |

**结论**：浏览器从 **5174** 加载前端；**真实推理数据**来自 **8000** 上的 `api_bridge`（需先在同一机器启动 `python api_bridge.py`，并保证 `multiagent` 能正常跑任务）。未启动桥接时，界面仍可打开，但无法得到完整实时结果。

更细的架构与消息类型见仓库内文档：`../docs/frontend-demo架构与数据流详解.md`。

---

## 运行

```bash
cd frontend-demo
npm install
npm run dev
```

- 开发地址：**http://localhost:5174**（与常见 5173 端口错开，避免与 Frontend 1.0 冲突）
- 联调后端：在 `multiagent` 目录启动 **`python api_bridge.py`**（监听 `0.0.0.0:8000`）

生产构建：

```bash
npm run build
npm run preview   # 本地预览 dist
```

---

## 源码结构（摘要）

```
src/
├── App.tsx                    # 根布局（全屏三栏，overflow 锁滚动）
├── store/useWorkflowStore.ts  # 任务状态、WS、日志解析、SOAP/图片 URL 等
├── mockData.ts                # 演示用默认配置与部分静态文案（与后端解耦）
├── components/
│   ├── Panel.tsx / TacticalPanel.tsx   # 左/右栏与中间「节点工作流」统一标题栏
│   ├── CyberControls.tsx               # 战术风下拉等
│   ├── LeftPanel/                    # 推理引擎示意、RAG 配置、技能库、动作模块
│   ├── CenterPanel/                  # 主监视器、Dagre 工作流图、指令输入、节点弹窗
│   └── RightPanel/                   # RAG 检索结果、SOAP 报告、任务执行结果
└── utils/                         # 日志分段、阶段摘要等
```

---

## 功能要点（3.0）

- **三栏布局**：左配置 / 中主视觉与流程图 / 右情报与报告。
- **节点工作流链路**：五阶段 + 动作节点；固定节点尺寸；日志驱动高亮与完成态（含 0 目标跳过中段时的 SKIPPED）。
- **主监视器与胶片条**：按日志中的图片路径更新；裁剪链文件名推导 SUPER-RES / GREYSCALE / BINARIZED 等标签。
- **RAG 区**：阶段四可轮询 `Doc4_Search.json`；新任务通过 `runId` 清空上一轮展示。
- **SOAP**：中文版块标题【S/O/A/P】；有真实报告后解析展示（非全程静态 mock）。
- **任务执行结果**：仅在流水线产生真实数据后展示「已执行」类状态（避免一进来就显示完成）。

详细设计说明与常见问题仍以 **`../docs/`** 下 Markdown 为准（如 `frontend-demo启动指南与常见问题.md`、`multiagent与frontend-demo项目详细介绍.md` 等）。

---

## 版本

- **3.0**：README 与项目现状对齐；明确 **5174 + 8000** 双端口联调模型、真实数据与 mock 的边界、目录与功能列表。
- 历史：**2.0** 曾侧重「纯前端 mock」表述；当前实现已深度依赖 `api_bridge` 做演示级联调。
