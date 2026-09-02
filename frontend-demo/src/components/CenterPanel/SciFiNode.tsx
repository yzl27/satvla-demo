import { Handle, Position } from 'reactflow';

export type SciFiNodeStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'SKIPPED';

type NodeData = {
  label: string;
  status?: SciFiNodeStatus;
  /** RUNNING 时最后一行日志缩略 */
  subline?: string;
};

/** 与 WorkflowGraph Dagre 节点尺寸一致，推理过程中不随内容变化 */
export const WORKFLOW_NODE_W = 210;
export const WORKFLOW_NODE_H = 72;

export const SciFiNode = ({ data }: { data: NodeData }) => {
  const status: SciFiNodeStatus = data.status ?? 'PENDING';

  let containerClass =
    `relative box-border w-full h-full min-w-0 min-h-0 max-w-full max-h-full overflow-hidden px-3 py-2 bg-[#060b14]/90 border-2 font-mono text-[10px] tracking-widest transition-[border-color,box-shadow] duration-500 flex items-center `;
  let textClass = 'font-bold text-center w-full z-10 truncate ';
  let indicatorClass = 'absolute top-0 left-0 w-1.5 h-full transition-all duration-500 ';

  if (status === 'COMPLETED') {
    containerClass += 'border-cyan-500/60 shadow-[0_0_15px_rgba(6,182,212,0.25)]';
    textClass += 'text-cyan-300 drop-shadow-[0_0_5px_rgba(34,211,238,0.5)]';
    indicatorClass += 'bg-cyan-400 shadow-[0_0_8px_#22d3ee]';
  } else if (status === 'RUNNING') {
    containerClass +=
      'border-amber-500 shadow-[inset_0_0_15px_rgba(245,158,11,0.2),0_0_20px_rgba(245,158,11,0.5)]';
    textClass += 'text-amber-400 drop-shadow-[0_0_8px_rgba(245,158,11,0.8)] animate-pulse';
    indicatorClass += 'bg-amber-400 shadow-[0_0_10px_#f59e0b]';
  } else if (status === 'SKIPPED') {
    containerClass += 'border-slate-600 border-dashed opacity-75 shadow-none';
    textClass += 'text-slate-500';
    indicatorClass += 'bg-slate-600';
  } else {
    containerClass += 'border-slate-800 shadow-none';
    textClass += 'text-slate-600';
    indicatorClass += 'bg-slate-700';
  }

  return (
    <div className={`${containerClass} cursor-pointer select-none`}>
      <Handle
        type="target"
        position={Position.Left}
        className="w-1.5 h-6 bg-slate-500 border-none rounded-none -left-[4px]"
      />

      <div className={indicatorClass} />

      <div className="flex flex-col w-full min-h-0 justify-center gap-0.5">
        <span className={textClass} title={data.label}>
          {data.label}
        </span>
        {/* 固定高度占位行，始终渲染避免节点高度跳变 */}
        <span
          className={`h-4 shrink-0 text-[8px] text-center font-mono leading-tight px-1 truncate block min-h-[1rem] ${
            status === 'RUNNING'
              ? 'text-amber-500/90'
              : status === 'SKIPPED'
              ? 'text-slate-500 tracking-wider'
              : 'invisible'
          }`}
          title={status === 'RUNNING' ? (data.subline || '[ 处理中 ]') : undefined}
        >
          {status === 'RUNNING'
            ? (data.subline || '[ 处理中 ]')
            : status === 'SKIPPED'
            ? '[ 已跳过 ]'
            : '—'}
        </span>
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className="w-1.5 h-6 bg-slate-500 border-none rounded-none -right-[4px]"
      />
    </div>
  );
};
