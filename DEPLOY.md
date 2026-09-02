# SatVLALab 前端演示（精简版）— 部署说明

> 精简版：**只包含代码**（约 37MB），不带 Python 环境和模型权重。环境和权重由目标机器联网自行安装/下载。适合网络条件好的接收方或需要小体积传输的场景。
> 完整版（约 5.1GB，开箱即用，无需联网下载权重）见 `satvla-demo.tar`。

## 一、架构总览

与完整版相同：React 前端 (:5174) → api_bridge 桥接 (:8000) → 五阶段推理流水线（感知 → 检测 → 逐目标分析 → RAG 检索 → SOAP 报告），产物写入 `multiagent/workspace/task_*/`。

## 二、接收方环境要求

| 项 | 要求 | 检查命令 |
|---|---|---|
| 操作系统 | Linux x86_64（Ubuntu 20.04+） | `uname -m` |
| GPU | NVIDIA 显卡，显存 ≥ 16GB | `nvidia-smi` |
| 驱动 | ≥ 525（支持 CUDA 11.8） | `nvidia-smi` |
| Python | 需要 conda（Miniconda 即可） | `conda --version` |
| Node.js | ≥ 18 | `node -v` |
| 网络 | 能访问互联网（下载依赖/权重/模型，总计约 12GB 下载量） | — |
| 磁盘 | ≥ 30GB 可用 | `df -h` |

## 三、部署包内容

```
satvla-demo-lite/
├── multiagent/           # 推理流水线 + 桥接服务（代码，不含权重，含预编译 _C.so）
├── frontend-demo/        # React 前端源码
├── requirements.txt      # Python 依赖清单（含版本锁定说明）
├── download_weights.sh   # 权重下载脚本（自动放到位）
├── setup.sh              # 一键安装（conda 环境 + 依赖 + 权重 + Ollama + npm）
├── start.sh / stop.sh    # 一键启动 / 停止
├── docs/                 # 项目详细文档
├── README.md             # 项目说明
└── DEPLOY.md             # 本文件
```

## 四、快速开始

```bash
tar -xzf satvla-demo-lite.tar.gz && cd satvla-demo-lite

# 第 1 步：一键安装（约 12GB 下载，耗时取决于网速）
bash setup.sh
#   ├─ 创建 conda 环境 satvla（python 3.10）
#   ├─ pip 安装 torch 2.0.1+cu118（约 2.4GB）+ 其余依赖
#   ├─ 下载模型权重（GroundingDINO 662MB / Real-ESRGAN / Restormer / DehazeFormer）
#   ├─ 安装 Ollama + 拉取 qwen3.5:9b（6.6GB）
#   └─ npm install 前端依赖

# 第 2 步：一键启动
bash start.sh
# → 浏览器打开 http://localhost:5174
```

首次推理时 GroundingDINO 会自动从 hf-mirror 拉取 bert-base-uncased（约 440MB，start.sh 已设置 `HF_ENDPOINT=https://hf-mirror.com`）。

## 五、手动安装（不用 setup.sh 时）

```bash
# 1. conda 环境
conda create -n satvla python=3.10 -y && conda activate satvla

# 2. PyTorch（CUDA 11.8，与预编译 _C.so 匹配，勿换版本）
pip install torch==2.0.1+cu118 torchvision==0.15.2+cu118 --index-url https://download.pytorch.org/whl/cu118

# 3. 其余依赖
pip install -r requirements.txt

# 4. 权重
bash download_weights.sh

# 5. Ollama 模型
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3.5:9b

# 6. 前端
cd frontend-demo && npm install && cd ..
```

手动启动：
```bash
conda activate satvla
export LD_LIBRARY_PATH="$(python -c 'import os,torch;print(os.path.join(os.path.dirname(torch.__file__),"lib"))')"
export HF_ENDPOINT=https://hf-mirror.com
python multiagent/api_bridge.py          # 终端 1
cd frontend-demo && npm run dev -- --host # 终端 2
```

## 六、验证部署是否成功

1. `curl http://localhost:8000/latest-report` 返回 JSON；浏览器打开 5174 见三栏界面。
2. 点「执行」后中间栏五阶段进度条依次高亮，约 5~15 分钟完成。
3. 任务完成后 `multiagent/workspace/task_*/` 应有 `*_detected.png`、`*_crop*.png`、`Doc1~4.json`、`FINAL_SOAP_REPORT.txt`。

## 七、常见问题（FAQ）

**Q1：`import groundingdino._C` 报 `libc10.so` 找不到**
LD_LIBRARY_PATH 未指向 torch 动态库目录。start.sh 已自动设置；手动运行时按「五」中命令设置。

**Q2：GroundingDINO 报错 `Undefined symbol` 或加载失败**
版本不匹配：预编译的 `_C.so` 要求 **Python 3.10 + torch 2.0.1+cu118**。改了版本需重新编译：
```bash
cd multiagent/tools/GroundingDINO
conda activate satvla
pip install -e .   # 需要 CUDA toolkit 11.8 + gcc
```

**Q3：权重下载失败（GitHub 上不去）**
- GroundingDINO / Real-ESRGAN 权重脚本已优先走 hf-mirror（国内可用）。
- DehazeFormer / Restormer 权重需访问 GitHub；如失败，手动下载后放到 `multiagent/tools/<工具>/weights/` 下（文件名见 download_weights.sh），Restormer 官方 README 另提供 Google Drive 链接：https://github.com/swz30/Restormer

**Q4：pip 安装慢**
加清华镜像：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`
（torch 的 cu118 包仍必须用 pytorch.org 的 index，已在 setup.sh 处理）

**Q5：CUDA out of memory**
前端一次只点一次「执行」，等任务完成再点下一次。

**Q6：点执行无反应**
查看 `logs/bridge.log`；确认 8000 端口未被占用。

**Q7：Ollama 安装需要 sudo**
手动安装：https://ollama.com/download ，再 `ollama pull qwen3.5:9b`。

**Q8：huggingface 拉取 bert-base-uncased 卡住**
确认启动时设置了 `HF_ENDPOINT=https://hf-mirror.com`（start.sh 已内置）。

其余问题见 docs/ 下详细文档。
