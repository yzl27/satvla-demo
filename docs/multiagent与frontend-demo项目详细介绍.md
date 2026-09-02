# `multiagent` 与 `frontend-demo` 项目详细介绍

本文面向开发者与项目维护者，系统介绍以下两个项目的定位、架构、目录、运行方式和协作关系：

- `@ljy/multiagent`
- `@ljy/SatLab/SatVLALab/SatVLALab/frontend-demo`

---

## 1. 两个项目的整体关系

可以把这两个项目理解为同一套业务链路的不同层：

- `multiagent`：后端/算法工作流侧，负责真正的图像分析、工具调用、检索和报告生成。
- `frontend-demo`：前端演示侧；联调时在 `**api_bridge.py`（默认 8000）** 上通过 **WebSocket** 接收 `run.py` 日志流，并用 **HTTP** 拉取 `workspace` 下图片与 `Doc*.json`。**左栏大量配置仍为 Mock**，不反向驱动 `run.py`。

一句话总结：

- `multiagent` 负责“做事”
- `frontend-demo` 负责“展示做事过程与结果”（日志 + 静态产物为真，配置类 UI 多为占位）

---

## 2. `multiagent` 项目介绍

### 2.1 项目定位

`multiagent` 是一个以“多阶段智能体 + 可调用视觉工具 + 检索增强”为核心的图像情报流水线系统。它的典型输入是单张遥感/监控图像，输出是结构化中间档案与最终 SOAP 文本报告。

典型能力包括：

- 图像质量增强（去雾/去噪/去雨/去模糊）
- 开放词表目标检测（GroundingDINO）
- 目标局部裁剪与增强分析（crop + 超分 + 灰度/二值化）
- 关键词提炼与外部检索（RAG）
- 综合生成最终情报报告（SOAP）

### 2.2 主入口与执行方式

主入口文件是 `@ljy/multiagent/run.py`，注释中定义了直接运行方式：

- `python run.py <图片路径>`

执行逻辑概要：

1. 校验输入图片格式和存在性
2. 将输入图复制到 `workspace/task_xxx/` 并按时间戳重命名
3. 调用 `engine/state_machine.py` 的 `run_agent_workflow()`
4. 最终输出 `FINAL_SOAP_REPORT.txt` 路径

### 2.3 五阶段工作流（核心）

核心编排在 `@ljy/multiagent/engine/state_machine.py`，包含五阶段：

1. 阶段一（全局质检员）
  图像预处理 + 检测，输出 `Doc1_Global.json`
2. 阶段二（战术指挥官）
  目标优先级排序、裁剪队列生成，输出 `Doc2_Queue.json`
3. 阶段三（局部特种兵）
  针对 Top 目标循环调用局部工具提取细节，输出 `Doc3_Details.json`
4. 阶段四（情报提炼官）
  从阶段一/三结果提炼关键词并检索，输出 `Doc4_Search.json`
5. 阶段五（首席报告官）
  汇总所有文档生成 `FINAL_SOAP_REPORT.txt`

该实现带有较完整的容错机制（如工具调用上限、无目标跳过、幻觉工具名兜底、bbox 越界裁剪等）。

### 2.4 核心目录结构与职责

`@ljy/multiagent` 中建议重点关注：

- `run.py`：总入口
- `engine/`
  - `state_machine.py`：五阶段主控逻辑
  - `tool_use.py`：工具调度、参数构建、权重映射
- `vlm/`
  - `vlm_utils.py`：VLM 调用、图像预处理、JSON 解析重试
- `memory/`
  - `prompt_global.txt`
  - `prompt_commander.txt`
  - `prompt_specialist.txt`
  - `prompt_extractor.txt`
  - `prompt_reporter.txt`
- `tools/`
  - `DehazeFormer/`
  - `Restormer/`
  - `GroundingDINO/`
  - `Real-ESRGAN/`
  - `OpenCV/`
  - `RAG/`
- `workspace/`：按任务 ID 存放所有中间/最终结果
- `rc_test/`：评估脚本、smoke test 与样例输出

### 2.5 技术栈与依赖特点

主要技术栈：

- Python
- PyTorch / torchvision
- OpenCV / Pillow / numpy
- requests（调用本地模型服务）

依赖管理特点：

- 各视觉工具目录有各自 `requirements.txt` 或 `setup.py`
- 项目根目录不是单一统一依赖管理（整合部署时需要额外治理）

### 2.6 配置、模型和路径管理

核心配置来源：

- Prompt：`memory/*.txt`
- 模型与工具执行：`engine/tool_use.py`
- VLM 基础参数（如模型名、服务地址）：`vlm/vlm_utils.py`

本次迁移后，工具脚本中的默认权重路径已改为“相对脚本目录计算”，例如：

- `tools/Restormer/run_denoise.py`
- `tools/DehazeFormer/run_dehaze.py`
- `tools/Real-ESRGAN/run_sr.py`
- `tools/GroundingDINO/run_detect.py`

这能显著降低项目跨目录复制后的路径问题。

### 2.7 输出产物与数据形态

每次任务都会在 `workspace/task_时间戳/` 下生成：

- `Doc1_Global.json`
- `Doc2_Queue.json`
- `Doc3_Details.json`
- `Doc4_Search.json`
- `FINAL_SOAP_REPORT.txt`

这套产物既可用于追溯，也可作为前端展示或离线评估数据源。

### 2.8 测试与验证方式

`rc_test/` 提供两类验证：

- `smoke_run_pipeline.py`：主流程冒烟测试（看能否端到端跑通）
- `run_eval.py`：基于清单进行批量评估并输出指标

常见输出包括 `predictions.json/csv`、`metrics.json`、`summary.txt`。

### 2.9 风险与注意事项

建议重点关注以下问题：

- 强依赖本地模型服务可用性（如 Ollama）
- 多工具默认优先使用 CUDA，GPU 不可用时会失败
- 各子工具依赖版本存在潜在冲突
- RAG 外部检索结果可信度需要人工复核
- 生产环境应避免明文密钥与硬编码敏感配置

---

## 3. `frontend-demo` 项目介绍

### 3.1 项目定位

`frontend-demo` 是 SatVLALab 的 **Frontend 3.0 Demo**：联调时需要 `**multiagent/api_bridge.py`** 在 **8000** 端口运行；前端开发服务默认 **5174**（Vite）。**进度、主图、胶片、Doc 拉取、SOAP 报告**等与日志/产物联动；**左栏下拉、技能开关、右下动作数值**等仍为 UI 占位或 `mockData`，与后端无契约。

定位关键词：

- 产品形态与流程可视化优先
- 与 `run.py` 通过 **WebSocket + 静态挂载** 对齐，非“纯离线静态页”

### 3.2 技术栈

来自 `@ljy/SatLab/SatVLALab/SatVLALab/frontend-demo/package.json`：

- React 18 + TypeScript
- Vite 5
- Tailwind CSS + PostCSS + Autoprefixer
- React Flow（流程图）
- Dagre（自动布局）

### 3.3 启动与构建

项目 README 给出的标准命令：

- `npm install`
- `npm run dev`
- `npm run build`
- `npm run preview`

开发端口：

- `5174`（与其他前端工程端口错开）

### 3.4 页面结构与组件分工

核心入口：

- `src/main.tsx`
- `src/App.tsx`

应用采用三栏布局：

- 左栏（参数配置）：`src/components/LeftPanel/`
  - `LLaVAControlPanel.tsx`
  - `RAGConfiguration.tsx`
  - `SkillLibrary.tsx`
  - `ActionModule.tsx`
- 中栏（图像与流程）：`src/components/CenterPanel/`
  - `ImageViewer.tsx`
  - `WorkflowGraph.tsx`
  - `PromptInput.tsx`
  - 节点展示与弹窗组件
- 右栏（输出结果）：`src/components/RightPanel/`
  - `IntermediateOutput.tsx`
  - `SOAPOutput.tsx`
  - `FinalActionResult.tsx`

### 3.5 数据与交互模式

**真实数据路径（需 `api_bridge` + `multiagent` 正常运行）**

- `src/store/useWorkflowStore.ts`：**WebSocket** `ws://localhost:8000/ws/mission`，解析日志中的阶段、`task_id`、图片路径、SOAP `report` 等。
- **HTTP**：`fetch` 拉取 `http://localhost:8000/workspace/<task_id>/Doc1~Doc4.json` 及主图 URL；**RAG 面板**轮询 `Doc4_Search.json`；新任务用 `**runId`** 清空上一轮本地展示。

**仍来自 Mock / 本地状态**

- `src/mockData.ts`：左栏 LLaVA/RAG/技能等选项、流程图弹窗 fallback、右下动作数值等；**SOAP 面板**在无报告时不再使用 `soapOutput` 填充正文。

因此它适合：

- 端到端演示（同机起桥接后）
- 与 `workspace` 产物对照联调

也意味着：

- 左栏配置**不会**改变 Tavily/Ollama/工具选择（除非改 `multiagent` 源码）
- 异常与超时路径以后端与日志为准，前端仅做展示

### 3.6 配置与部署

关键配置文件：

- `vite.config.ts`
- `tailwind.config.js`
- `postcss.config.js`
- `tsconfig.json`

部署方式：

- 标准静态站点部署（`npm run build` 后托管 `dist/`）

### 3.7 测试现状

当前未看到完整自动化测试脚本（如 `test/lint/e2e`），项目偏演示用途。若后续转生产，建议补充：

- 单元测试（组件渲染和状态）
- E2E（流程链路）
- 接口契约测试（接入真实后端后）

---

## 4. 结论

这两个项目已经具备“算法流程 + 可视化表达”的完整雏形：

- `multiagent` 偏“能力中台”
- `frontend-demo` 偏“体验外壳”，且**在 `api_bridge` 联调模式下**已与 `run.py` 输出**实质对齐**（日志 + 产物）

后续若要进入生产形态，重点是把**左栏与运行参数**通过稳定契约与后端打通，并补足测试与可观测性；**展示主链路**已不再是“纯 Mock 静态页”。