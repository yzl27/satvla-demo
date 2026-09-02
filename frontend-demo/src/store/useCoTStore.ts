/**
 * 思维树 CoT：仅消费 WebSocket 的 cot_graph 快照，与 useWorkflowStore 解耦。
 */
import { create } from 'zustand';

export type CoTNodePayload = {
  id: string;
  kind: string;
  label: string;
  subtitle?: string | null;
  /** 阶段序号 0–5 */
  phase?: number;
  phase_label?: string | null;
  /** 操作说明（如：输入、全局观察与决策） */
  action_label?: string | null;
  thought?: string | null;
  details?: Record<string, unknown> | null;
  tool_name?: string | null;
  tool_args?: unknown;
  image_path?: string | null;
  /** SOAP / 完成等不展示缩略图 */
  hide_thumbnail?: boolean;
  /** 小图下方：该图由何种工具/步骤得到 */
  thumb_source?: string | null;
  /** 与 ImageViewer 胶片条 rec.label 一致，如 SRC / DEHAZED / DETECTED / ROI-1 / RAG / SOAP */
  film_label?: string | null;
  /** 与 ImageViewer 胶片条 rec.stageTag 一致，如 S0–S5 */
  stage_tag?: string | null;
  status?: string;
  raw_ref?: string | null;
};

export type CoTEdgePayload = {
  id: string;
  source: string;
  target: string;
};

type CoTGraphMsg = {
  revision: number;
  task_id?: string | null;
  nodes: CoTNodePayload[];
  edges: CoTEdgePayload[];
};

interface CoTState {
  revision: number;
  taskId: string | null;
  nodes: CoTNodePayload[];
  edges: CoTEdgePayload[];
  reset: () => void;
  setGraph: (msg: CoTGraphMsg) => void;
}

export const useCoTStore = create<CoTState>((set) => ({
  revision: 0,
  taskId: null,
  nodes: [],
  edges: [],

  reset: () =>
    set({
      revision: 0,
      taskId: null,
      nodes: [],
      edges: [],
    }),

  setGraph: (msg) =>
    set({
      revision: msg.revision,
      taskId: msg.task_id ?? null,
      nodes: msg.nodes ?? [],
      edges: msg.edges ?? [],
    }),
}));
