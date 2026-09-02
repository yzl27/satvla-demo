/**
 * useWorkflowStore.ts
 * ──────────────────────────────────────────────────────
 * Zustand 全局状态 + WebSocket 连接 + 日志解析引擎
 *
 * 日志 → UI 映射规则（来自 multiagent/engine/state_machine.py）：
 *   🟢 阶段一 → activeNode: 'fast_check'   (全局质检员)
 *   🟡 阶段二 → activeNode: 'perception'   (战术指挥官)
 *   🟠 阶段三 → activeNode: 'specialist'   (局部特种兵)
 *   🔵 阶段四 → activeNode: 'retrieval'    (情报提炼官 + RAG)
 *   🟣 阶段五 → activeNode: 'reasoning'    (首席报告官)
 *   🎉 任务圆满结束 → activeNode: 'action', isExecuting: false
 *   成功 → <path>  → mainImageSrc + imageHistory 更新
 *   检测完成       → 推导 _detected.png 进入 imageHistory
 *   BBox={...}    → cropBoxes 追加
 * ──────────────────────────────────────────────────────
 */

import { create } from 'zustand';

import { getDefaultImageUrl, getHttpApiBase, getWsMissionUrl } from '../utils/apiBase';
import { deriveImageInfo, workspaceRelFromHttpUrl } from '../utils/imageLabels';
import { useCoTStore, type CoTEdgePayload, type CoTNodePayload } from './useCoTStore';

export interface CropBox {
  id: string;
  label: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

/** 胶片条中每一帧的元数据 */
export interface ImageRecord {
  src: string;      // 完整 URL
  label: string;    // 'SRC' | 'DEHAZED' | 'DETECTED' | 'ROI-1' | 'SUPER-RES' | 'GREYSCALE' | 'BINARIZED'
  stageTag: string; // 'S0' | 'S1' | 'S2' | 'S3'
}

// 与 SciFiNode 状态对齐（图内使用）
export type NodeStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'SKIPPED';

export interface ParsedSOAP {
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
}

interface WorkflowState {
  activeNode: string | null;
  /** state_machine 工作区 task_YYYYMMDD_HHMMSS，用于拉取 Doc*.json */
  workflowTaskId: string | null;
  /** 每次点击执行递增，用于右侧 RAG 等本地状态与上一轮彻底脱钩 */
  runId: number;
  /** 容错①：0 目标时跳过二～四语义，结束时节点显示 SKIPPED */
  bypassMidPipeline: boolean;
  mainImageSrc: string;
  /** 全流程处理链图片记录（胶片条数据源） */
  imageHistory: ImageRecord[];
  cropBoxes: CropBox[];
  parsedSOAP: ParsedSOAP | null;
  soapRawText: string;
  logs: string[];
  isExecuting: boolean;
  hasRealData: boolean;

  startMission: (imagePath?: string) => void;
  reset: () => void;
}

function freshInitialHistory(): ImageRecord[] {
  return [{ src: getDefaultImageUrl(), label: 'SRC', stageTag: 'S0' }];
}

function extractTaskIdFromText(text: string): string | null {
  const m = text.match(/task_\d{8}_\d{6}/);
  return m ? m[0] : null;
}

/** 从 FINAL_SOAP_REPORT.txt 格式解析 S/O/A/P 四段 */
export function parseSOAPReport(text: string): ParsedSOAP {
  const extract = (tag: string): string => {
    const re = new RegExp(`【${tag}[^】]*】\\s*([\\s\\S]*?)(?=【[SOAP]|$)`);
    const m = text.match(re);
    return m ? m[1].trim() : '';
  };
  return {
    subjective: extract('S'),
    objective:  extract('O'),
    assessment: extract('A'),
    plan:       extract('P'),
  };
}

const INITIAL_IMAGE_HISTORY: ImageRecord[] = freshInitialHistory();

export const useWorkflowStore = create<WorkflowState>((set, get) => ({
  activeNode:        null,
  workflowTaskId:    null,
  runId:               0,
  bypassMidPipeline: false,
  mainImageSrc:      getDefaultImageUrl(),
  imageHistory:      INITIAL_IMAGE_HISTORY,
  cropBoxes:         [],
  parsedSOAP:        null,
  soapRawText:       '',
  logs:              [],
  isExecuting:       false,
  hasRealData:       false,

  reset: () => {
    useCoTStore.getState().reset();
    set({
      activeNode:        null,
      workflowTaskId:    null,
      runId:               0,
      bypassMidPipeline: false,
      cropBoxes:         [],
      parsedSOAP:        null,
      soapRawText:       '',
      logs:              [],
      isExecuting:       false,
      hasRealData:       false,
      mainImageSrc:      getDefaultImageUrl(),
      imageHistory:      freshInitialHistory(),
    });
  },

  startMission: (imagePath) => {
    get().reset();
    set({ isExecuting: true, runId: Date.now() });

    // 预置思维链 SRC 头节点：点击执行后立即可见。
    const seedRelFromArg = imagePath ? imagePath.replace(/^.*\/workspace\//, '').replace(/^\//, '') : null;
    const seedRelFromMain = workspaceRelFromHttpUrl(get().mainImageSrc);
    const seedRel = (seedRelFromArg && seedRelFromArg.length > 0) ? seedRelFromArg : seedRelFromMain;
    if (seedRel) {
      useCoTStore.getState().setGraph({
        revision: 1,
        task_id: null,
        nodes: [
          {
            id: 'seed_src',
            kind: 'step',
            phase: 0,
            phase_label: '输入',
            action_label: '输入',
            label: '输入图像',
            subtitle: 'SRC',
            image_path: seedRel,
            thumb_source: '输入图像（启动即显示）',
            film_label: 'SRC',
            stage_tag: 'S0',
            status: 'running',
          },
        ],
        edges: [],
      });
    }

    const ws = new WebSocket(getWsMissionUrl());

    ws.onopen = () => {
      ws.send(JSON.stringify({ action: 'start', image_path: imagePath ?? '' }));
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as {
          type: string;
          content?: string;
          task_id?: string;
          revision?: number;
          nodes?: unknown[];
          edges?: unknown[];
        };

        if (msg.type === 'cot_graph') {
          // 后端尚未产出任何节点时，保留预置 SRC 头节点，避免“点击后空白”。
          const cur = useCoTStore.getState();
          if ((msg.nodes ?? []).length === 0 && cur.nodes.length > 0) {
            return;
          }
          useCoTStore.getState().setGraph({
            revision: msg.revision ?? 0,
            task_id: msg.task_id,
            nodes: (msg.nodes ?? []) as CoTNodePayload[],
            edges: (msg.edges ?? []) as CoTEdgePayload[],
          });
          return;
        }

        if (msg.type === 'log' && msg.content !== undefined) {
          const log = msg.content;

          // 保留最近 300 条日志
          set((state) => ({ logs: [...state.logs.slice(-299), log] }));

          const tid = extractTaskIdFromText(log);
          if (tid) {
            set((state) =>
              state.workflowTaskId === tid ? {} : { workflowTaskId: tid },
            );
          }
          if (log.includes('0 个目标，直接跳转阶段五')) {
            set({ bypassMidPipeline: true });
          }

          // ── 阶段转换 ──────────────────────────────
          if (log.includes('🟢 阶段一')) {
            set({ activeNode: 'fast_check' });
          } else if (log.includes('🟡 阶段二')) {
            set({ activeNode: 'perception' });
          } else if (log.includes('🟠 阶段三')) {
            set({ activeNode: 'specialist' });
          } else if (log.includes('🔵 阶段四')) {
            set({ activeNode: 'retrieval' });
          } else if (log.includes('🟣 阶段五')) {
            set({ activeNode: 'reasoning' });
          } else if (log.includes('🎉 任务圆满结束')) {
            set({ activeNode: 'action', isExecuting: false });
          }

          // ── 工具产出图片：统一捕获 ─────────────────
          // 匹配所有"成功 → [新图:] /abs/path.png" 格式
          // 覆盖：复原/裁剪/超分/灰度/二值化
          const toolSuccessRe = /成功\s*→\s*(?:新图:\s*)?(\S+\.(?:png|jpg|jpeg))/i;
          const toolMatch = log.match(toolSuccessRe);
          if (toolMatch) {
            const absPath = toolMatch[1].trim();
            const relPart = absPath.replace(/^.*\/workspace\//, '');
            const url = `${getHttpApiBase()}/workspace/${relPart}`;
            const info = deriveImageInfo(absPath);
            set((state) => ({
              mainImageSrc: url,
              imageHistory: state.imageHistory.some((r) => r.src === url)
                ? state.imageHistory
                : [...state.imageHistory, { src: url, ...info }],
            }));
          }

          // ── 检测完成：推导 _detected.png（已含标注框的可视化图）──
          if (log.includes('检测完成') || log.includes('强制检测完成')) {
            const curSrc = get().mainImageSrc;
            // 若当前图是 _dehazed.png → 推导为 _dehazed_detected.png
            const detectedUrl = curSrc.replace(/(\.\w+)$/, '_detected$1');
            if (detectedUrl !== curSrc) {
              set((state) => ({
                mainImageSrc: detectedUrl,
                imageHistory: state.imageHistory.some((r) => r.src === detectedUrl)
                  ? state.imageHistory
                  : [...state.imageHistory, { src: detectedUrl, label: 'DETECTED', stageTag: 'S1' }],
              }));
            }
          }

          // ── 裁剪框解析 ────────────────────────────
          const boxMatch = log.match(
            /BBox=\{'id': '([^']+)', 'label': '([^']+)'.*?'x1': (\d+), 'y1': (\d+), 'x2': (\d+), 'y2': (\d+)\}/,
          );
          if (boxMatch) {
            const newBox: CropBox = {
              id:    boxMatch[1],
              label: boxMatch[2],
              x1:    parseInt(boxMatch[3]),
              y1:    parseInt(boxMatch[4]),
              x2:    parseInt(boxMatch[5]),
              y2:    parseInt(boxMatch[6]),
            };
            set((state) => ({ cropBoxes: [...state.cropBoxes, newBox] }));
          }
        } else if (msg.type === 'report' && msg.content !== undefined) {
          const parsed = parseSOAPReport(msg.content);
          set((state) => ({
            soapRawText: msg.content,
            parsedSOAP: parsed,
            hasRealData: true,
            workflowTaskId: msg.task_id ?? state.workflowTaskId,
          }));
        } else if (msg.type === 'system' && msg.content === 'MISSION_COMPLETED') {
          set({ isExecuting: false });
        } else if (msg.type === 'error') {
          set({ isExecuting: false });
          console.error('[useWorkflowStore] Mission error:', msg.content);
        }
      } catch (err) {
        console.error('[useWorkflowStore] Failed to parse WS message', err);
      }
    };

    ws.onclose = () => set((s) => (s.isExecuting ? { isExecuting: false } : {}));
    ws.onerror = () => set({ isExecuting: false });
  },
}));
