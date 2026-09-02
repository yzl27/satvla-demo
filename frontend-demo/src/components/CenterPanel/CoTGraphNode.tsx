import { Handle, Position } from 'reactflow';
import { getHttpApiBase } from '../../utils/apiBase';
import { STAGE_COLOR, filmLabelForNode } from '../../utils/imageLabels';
import type { CoTNodePayload } from '../../store/useCoTStore';

function thumbUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  const rel = path.replace(/^\//, '');
  return `${getHttpApiBase()}/workspace/${rel}`;
}

function statusTone(status: string | undefined): string {
  if (status === 'running') return 'text-amber-400/90';
  if (status === 'done') return 'text-cyan-500/80';
  return 'text-slate-500';
}

/** 与 ImageViewer 胶片条底部标签一致：SRC / DEHAZED / DETECTED / ROI-n / RAG / SOAP */
export function CoTGraphNode({
  data,
}: {
  data: { payload: CoTNodePayload; active?: boolean };
}) {
  const n = data.payload;
  const active = Boolean(data.active);
  const phase = n.phase ?? -1;
  const compact = phase >= 4 || n.hide_thumbnail;

  const showThumb = Boolean(n.image_path) && !n.hide_thumbnail;
  const img = showThumb ? thumbUrl(n.image_path) : null;

  const { label: filmLabel, stageTag } = filmLabelForNode(
    n.image_path,
    n.film_label,
    n.stage_tag,
  );
  const filmColor = STAGE_COLOR[stageTag] ?? 'text-slate-400';

  /** 只保留一种：汉字阶段名 或 数字序号，避免「阶段一 · 1」重复 */
  const phaseTitle =
    n.phase_label?.trim() ||
    (n.phase != null ? `阶段 ${n.phase}` : stageTag?.startsWith('S') ? `阶段 ${stageTag.slice(1)}` : '—');

  if (compact) {
    return (
      <div
        className={`relative box-border w-full h-full rounded-lg overflow-hidden bg-black/90 border font-mono text-[9px] min-w-0 max-w-full flex flex-col shadow-inner ${
          active
            ? 'border-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.45)] ring-1 ring-cyan-400/90'
            : n.status === 'running'
              ? 'ring-1 ring-amber-500/35 border-slate-700/60'
              : 'ring-1 ring-slate-700/50 border-slate-700/60'
        }`}
      >
        <Handle
          type="target"
          position={Position.Left}
          className="!w-1.5 !h-6 !bg-slate-600 !border-none !rounded-sm !-left-1"
        />
        <div className="shrink-0 px-2 py-1.5 bg-gradient-to-r from-violet-950/40 to-slate-950/40 border-b border-slate-800/80">
          <div className="text-[9px] font-bold text-violet-300/95 tracking-wide">{phaseTitle}</div>
          <div className={`text-[7px] text-right mt-0.5 ${statusTone(n.status)}`}>{n.status}</div>
        </div>
        <div className="flex-1 min-h-0 px-2.5 py-2 flex flex-col justify-center gap-1">
          <div className="text-[11px] font-semibold text-slate-100 leading-snug line-clamp-2">{n.label}</div>
          {n.subtitle ? (
            <div className="text-[8px] text-slate-500 line-clamp-2">{n.subtitle}</div>
          ) : null}
        </div>
        {/* 与 ImageViewer 胶片条同构底栏 */}
        <div
          className={`shrink-0 bg-black/75 text-[7px] font-mono text-center leading-tight py-1 truncate border-t border-slate-800/80 ${filmColor}`}
        >
          {filmLabel}
        </div>
        <Handle
          type="source"
          position={Position.Right}
          className="!w-1.5 !h-6 !bg-slate-600 !border-none !rounded-sm !-right-1"
        />
      </div>
    );
  }

  return (
    <div
      className={`relative box-border w-full h-full rounded-lg overflow-hidden bg-[#070d16] border font-mono min-w-0 max-w-full flex flex-col shadow-[0_0_18px_rgba(6,182,212,0.07)] ${
        active
          ? 'border-cyan-400 shadow-[0_0_12px_rgba(34,211,238,0.35)] ring-2 ring-cyan-400/70'
          : n.status === 'running'
            ? 'ring-1 ring-amber-500/40 border-cyan-900/45'
            : 'ring-1 ring-cyan-950/60 border-cyan-900/45'
      }`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!w-1.5 !h-6 !bg-cyan-700/80 !border-none !rounded-sm !-left-1"
      />

      <div className="shrink-0 px-2 py-1 bg-gradient-to-r from-cyan-950/80 to-slate-950/40 border-b border-cyan-900/30">
        <div className="text-[9px] font-bold text-cyan-200/95 tracking-wide text-center">{phaseTitle}</div>
        <div className={`text-[7px] text-right mt-0.5 ${statusTone(n.status)}`}>{n.status}</div>
      </div>

      {/* 中：缩略图（与 ImageViewer 胶片格同比例感：object-cover + 底栏标签） */}
      <div className="relative flex-1 min-h-[76px] max-h-[88px] bg-black/35 border-b border-slate-800/80">
        {img ? (
          <img src={img} alt="" className="w-full h-full object-cover min-h-[76px]" loading="lazy" />
        ) : (
          <div className="w-full h-full min-h-[76px] flex items-center justify-center text-[8px] text-slate-700 px-2 text-center">
            —
          </div>
        )}
      </div>

      <div
        className={`shrink-0 bg-black/75 text-[8px] font-mono text-center leading-tight py-1 px-1 truncate border-t border-slate-800/80 ${filmColor}`}
        title={filmLabel}
      >
        {filmLabel}
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className="!w-1.5 !h-6 !bg-cyan-700/80 !border-none !rounded-sm !-right-1"
      />
    </div>
  );
}
