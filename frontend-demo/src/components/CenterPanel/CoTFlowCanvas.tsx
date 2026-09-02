import { useCallback, useEffect, useMemo, useState } from 'react';
import dagre from 'dagre';
import ReactFlow, {
  Background,
  Controls,
  ReactFlowProvider,
  applyEdgeChanges,
  applyNodeChanges,
  useReactFlow,
  type Edge,
  type Node,
  type NodeChange,
  type EdgeChange,
  type NodeMouseHandler,
} from 'reactflow';
import 'reactflow/dist/style.css';

import { CoTGraphNode } from './CoTGraphNode';
import { NodeModal } from './NodeModal';
import { CoTNodeDetailBody } from './CoTNodeDetailBody';
import type { CoTEdgePayload, CoTNodePayload } from '../../store/useCoTStore';
import { useCoTStore } from '../../store/useCoTStore';
import { useWorkflowStore } from '../../store/useWorkflowStore';
import { workspaceRelFromHttpUrl } from '../../utils/imageLabels';

const nodeTypes = { cotNode: CoTGraphNode };

/** 阶段 0–3 无图且非紧凑卡片：不展示（后端偶发或旧快照时避免「等待工具产出图像」占位） */
function shouldDropThinNode(n: CoTNodePayload): boolean {
  const p = n.phase ?? 0;
  if (p >= 4) return false;
  if (n.hide_thumbnail) return false;
  return !n.image_path?.trim();
}

function reachableKeptForward(
  start: string,
  dropIds: Set<string>,
  out: Map<string, string[]>,
): string[] {
  const result: string[] = [];
  const stack = [start];
  const seen = new Set<string>();
  while (stack.length) {
    const x = stack.pop()!;
    if (seen.has(x)) continue;
    seen.add(x);
    if (!dropIds.has(x)) {
      result.push(x);
      continue;
    }
    for (const y of out.get(x) ?? []) stack.push(y);
  }
  return result;
}

function reachableKeptBackward(
  start: string,
  dropIds: Set<string>,
  inc: Map<string, string[]>,
): string[] {
  const result: string[] = [];
  const stack = [start];
  const seen = new Set<string>();
  while (stack.length) {
    const x = stack.pop()!;
    if (seen.has(x)) continue;
    seen.add(x);
    if (!dropIds.has(x)) {
      result.push(x);
      continue;
    }
    for (const y of inc.get(x) ?? []) stack.push(y);
  }
  return result;
}

/** 去掉无图占位节点，并穿过被删节点桥接边，保持 DAG 可读 */
function filterCotGraphForDisplay(
  nodesIn: CoTNodePayload[],
  edgesIn: CoTEdgePayload[],
): { nodes: CoTNodePayload[]; edges: CoTEdgePayload[] } {
  const dropIds = new Set(nodesIn.filter(shouldDropThinNode).map((n) => n.id));
  if (dropIds.size === 0) {
    return { nodes: nodesIn, edges: edgesIn };
  }

  const nodes = nodesIn.filter((n) => !dropIds.has(n.id));
  const out = new Map<string, string[]>();
  const inc = new Map<string, string[]>();
  for (const e of edgesIn) {
    if (!out.has(e.source)) out.set(e.source, []);
    out.get(e.source)!.push(e.target);
    if (!inc.has(e.target)) inc.set(e.target, []);
    inc.get(e.target)!.push(e.source);
  }

  const edgeKey = new Set<string>();
  const nextEdges: CoTEdgePayload[] = [];
  const addEdge = (source: string, target: string) => {
    if (source === target) return;
    const k = `${source}|${target}`;
    if (edgeKey.has(k)) return;
    edgeKey.add(k);
    nextEdges.push({ id: `e_${source}_${target}`, source, target });
  };

  for (const e of edgesIn) {
    const s = e.source;
    const t = e.target;
    const sd = dropIds.has(s);
    const td = dropIds.has(t);
    if (!sd && !td) {
      addEdge(s, t);
      continue;
    }
    if (!sd && td) {
      for (const k of reachableKeptForward(t, dropIds, out)) addEdge(s, k);
      continue;
    }
    if (sd && !td) {
      for (const k of reachableKeptBackward(s, dropIds, inc)) addEdge(k, t);
    }
  }

  return { nodes, edges: nextEdges };
}

function sizeForPayload(n: CoTNodePayload): { w: number; h: number } {
  const p = n.phase ?? 0;
  if (p >= 4 || n.hide_thumbnail) {
    return { w: 200, h: 108 };
  }
  return { w: 188, h: 196 };
}

function toRfEdges(edgesIn: CoTEdgePayload[]): Edge[] {
  return edgesIn.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    type: 'smoothstep',
    animated: true,
    style: { stroke: '#64748b', strokeWidth: 1.5 },
  }));
}

/** Dagre 失败或非 DAG 时横向铺开，避免有数据却空白 */
function layoutStripFallback(nodesIn: CoTNodePayload[], edgesIn: CoTEdgePayload[]): { nodes: Node[]; edges: Edge[] } {
  const col = 248;
  const row = 120;
  const rfNodes: Node[] = nodesIn.map((n, i) => {
    const { w, h } = sizeForPayload(n);
    const x = (i % 6) * col;
    const y = Math.floor(i / 6) * row;
    return {
      id: n.id,
      type: 'cotNode',
      position: { x, y },
      data: { payload: n },
      style: { width: w, height: h },
      selectable: true,
    };
  });
  return { nodes: rfNodes, edges: toRfEdges(edgesIn) };
}

function layoutDagre(nodesIn: CoTNodePayload[], edgesIn: CoTEdgePayload[]): { nodes: Node[]; edges: Edge[] } {
  if (nodesIn.length === 0) {
    return { nodes: [], edges: [] };
  }

  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({
    rankdir: 'LR',
    ranker: 'longest-path',
    ranksep: 64,
    nodesep: 40,
    marginx: 24,
    marginy: 24,
  });

  for (const n of nodesIn) {
    const { w, h } = sizeForPayload(n);
    g.setNode(n.id, { width: w, height: h });
  }
  for (const e of edgesIn) {
    if (g.hasNode(e.source) && g.hasNode(e.target)) {
      g.setEdge(e.source, e.target);
    }
  }

  try {
    dagre.layout(g);
  } catch {
    return layoutStripFallback(nodesIn, edgesIn);
  }

  const rfNodes: Node[] = [];
  for (const n of nodesIn) {
    const { w, h } = sizeForPayload(n);
    const pos = g.node(n.id);
    const cx = pos?.x;
    const cy = pos?.y;
    if (cx == null || cy == null || Number.isNaN(cx) || Number.isNaN(cy)) {
      return layoutStripFallback(nodesIn, edgesIn);
    }
    rfNodes.push({
      id: n.id,
      type: 'cotNode',
      position: { x: cx - w / 2, y: cy - h / 2 },
      data: { payload: n },
      style: { width: w, height: h },
      selectable: true,
    });
  }

  return { nodes: rfNodes, edges: toRfEdges(edgesIn) };
}

function CoTFlowInner() {
  const revision = useCoTStore((s) => s.revision);
  const cotNodes = useCoTStore((s) => s.nodes);
  const cotEdges = useCoTStore((s) => s.edges);
  const isExecuting = useWorkflowStore((s) => s.isExecuting);
  const mainImageSrc = useWorkflowStore((s) => s.mainImageSrc);

  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [selected, setSelected] = useState<CoTNodePayload | null>(null);

  const { fitView } = useReactFlow();

  /** 与上方 ImageViewer 主图 workspace 路径一致时高亮节点 */
  const laidOut = useMemo(() => {
    const { nodes: n, edges: e } = filterCotGraphForDisplay(cotNodes, cotEdges);
    const layout = layoutDagre(n, e);
    const activeRel = workspaceRelFromHttpUrl(mainImageSrc)?.replace(/\\/g, '/');
    return {
      nodes: layout.nodes.map((node) => {
        const p = node.data.payload as CoTNodePayload;
        const rel = p.image_path?.replace(/^\//, '').replace(/\\/g, '/');
        const active = Boolean(activeRel && rel && activeRel === rel);
        return {
          ...node,
          data: { ...node.data, active },
        };
      }),
      edges: layout.edges,
    };
  }, [cotNodes, cotEdges, mainImageSrc]);

  useEffect(() => {
    setNodes(laidOut.nodes);
    setEdges(laidOut.edges);
  }, [laidOut, revision]);

  useEffect(() => {
    if (nodes.length === 0) return;
    const t = window.setTimeout(() => {
      fitView({ padding: 0.12, duration: 320, minZoom: 0.15, maxZoom: 1.4 });
    }, 60);
    return () => window.clearTimeout(t);
  }, [revision, nodes.length, fitView]);

  const onNodesChange = useCallback((changes: NodeChange[]) => {
    setNodes((nds) => applyNodeChanges(changes, nds));
  }, []);

  const onEdgesChange = useCallback((changes: EdgeChange[]) => {
    setEdges((eds) => applyEdgeChanges(changes, eds));
  }, []);

  const onNodeClick: NodeMouseHandler = useCallback((_, n) => {
    const p = (n.data as { payload?: CoTNodePayload })?.payload;
    if (p) setSelected(p);
  }, []);

  const empty = nodes.length === 0;

  return (
    <div className="relative w-full h-full min-h-[240px] overflow-hidden rounded-md bg-gradient-to-br from-[#050a14] via-[#0a1220] to-[#060b14]">
      {/* 空状态：不拦截指针，底部控件可点 */}
      {empty && (
        <div className="pointer-events-none absolute inset-0 z-[1] flex flex-col items-center justify-center px-6 text-center">
          <div className="mb-4 h-px w-40 bg-gradient-to-r from-transparent via-cyan-500/40 to-transparent" />
          <p className="font-mono text-xs tracking-wide text-slate-400">
            {isExecuting ? (
              <>
                <span className="text-cyan-400/90">推理进行中</span>
                <br />
                <span className="text-[11px] text-slate-500 mt-2 inline-block">
                  正在接收后端思维链数据…
                </span>
              </>
            ) : (
              <>
                <span className="text-slate-300">思维链展示区</span>
                <br />
                <span className="text-[11px] text-slate-500 mt-2 inline-block leading-relaxed">
                  在左侧执行分析任务后，各阶段推理、工具调用与中间图将在此
                  <br />
                  以动态图形式展开；请确认本机已启动{' '}
                  <code className="text-cyan-600/90">api_bridge.py</code>（端口 8000）。
                </span>
              </>
            )}
          </p>
          <div className="mt-5 flex items-center gap-2 text-[10px] font-mono text-slate-600">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-slate-600" />
            snapshot #{revision}
          </div>
          <div className="mt-6 h-px w-32 bg-gradient-to-r from-transparent via-slate-700 to-transparent" />
        </div>
      )}

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        onNodeClick={onNodeClick}
        onPaneClick={() => setSelected(null)}
        minZoom={0.08}
        maxZoom={2}
        nodesDraggable
        nodesConnectable={false}
        elementsSelectable
        proOptions={{ hideAttribution: true }}
        className="touchdevice-flow !bg-transparent"
      >
        <Background color="#06b6d4" gap={24} size={1} style={{ opacity: empty ? 0.04 : 0.07 }} />
        <Controls
          className="fill-slate-400 bg-slate-900/90 border border-slate-700 shadow-lg"
          showInteractive={false}
        />
      </ReactFlow>

      {selected && (
        <NodeModal
          title={selected.label}
          onClose={() => setSelected(null)}
          maxWidthClassName="max-w-4xl"
        >
          <CoTNodeDetailBody node={selected} />
        </NodeModal>
      )}
    </div>
  );
}

export function CoTFlowCanvas() {
  return (
    <ReactFlowProvider>
      <CoTFlowInner />
    </ReactFlowProvider>
  );
}
