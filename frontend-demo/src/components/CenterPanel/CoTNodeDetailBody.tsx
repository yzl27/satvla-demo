import { getHttpApiBase } from '../../utils/apiBase';
import type { CoTNodePayload } from '../../store/useCoTStore';

function workspaceUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  return `${getHttpApiBase()}/workspace/${path.replace(/^\//, '')}`;
}

function ActionsList({ details }: { details: Record<string, unknown> }) {
  const actions = details.actions;
  if (!Array.isArray(actions) || actions.length === 0) return null;
  return (
    <ul className="space-y-2 text-[10px] font-mono text-slate-300">
      {(actions as { summary?: string; log?: string }[]).map((a, i) => (
        <li key={i} className="border-l-2 border-fuchsia-900/60 pl-2">
          <span className="text-fuchsia-400/90">{a.summary ?? '—'}</span>
          {a.log ? (
            <pre className="mt-1 text-[9px] text-slate-500 whitespace-pre-wrap break-all max-h-24 overflow-auto">
              {a.log}
            </pre>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

export function CoTNodeDetailBody({ node }: { node: CoTNodePayload }) {
  const big = workspaceUrl(node.image_path);
  const d = node.details ?? {};
  const cap = typeof d.image_caption === 'string' ? d.image_caption : '';
  const decision = typeof d.decision === 'string' ? d.decision : '';
  const missionComplete = typeof d.mission_complete === 'string' ? d.mission_complete : '';
  const forcedNoImg = typeof d.forced_summary_no_image === 'string' ? d.forced_summary_no_image : '';

  const thoughtRaw = node.thought?.trim() ?? '';
  const looksLikeToolLog = /\[工具\]|^\s*INFO\s*\|/i.test(thoughtRaw);
  const thought = looksLikeToolLog ? '' : thoughtRaw;
  const phaseText = node.phase_label ?? (node.phase != null ? `阶段${node.phase}` : '未知阶段');
  const actionText = node.action_label ?? (node.label || '未命名步骤');

  const rawPayload = {
    phase: node.phase,
    phase_label: node.phase_label,
    action_label: node.action_label,
    label: node.label,
    subtitle: node.subtitle,
    film_label: node.film_label,
    stage_tag: node.stage_tag,
    thumb_source: node.thumb_source,
    image_path: node.image_path,
    thought: node.thought,
    details: d,
    status: node.status,
  };

  return (
    <div className="space-y-4">
      {big ? (
        <section>
          <div className="text-[9px] font-mono text-slate-500 uppercase tracking-widest mb-1">
            大图预览（点击遮罩外关闭）
          </div>
          <div className="rounded border border-slate-700 overflow-hidden bg-black/50 flex justify-center items-center max-h-[70vh]">
            <img
              src={big}
              alt=""
              className="w-full h-auto max-h-[70vh] object-contain"
            />
          </div>
          <p className="text-[8px] font-mono text-slate-500 mt-1 break-all">{node.image_path}</p>
        </section>
      ) : null}

      <section>
        <div className="text-[9px] font-mono text-slate-500 uppercase tracking-widest mb-1">
          阶段与操作
        </div>
        <p className="text-[11px] font-mono text-slate-200">
          {node.phase_label?.trim()
            ? `${phaseText} · ${actionText}`
            : `${phaseText}${node.phase != null ? `（${node.phase}）` : ''} · ${actionText}`}
        </p>
        <p className="text-[10px] font-mono text-slate-400 mt-1">{node.label}</p>
      </section>

      <section>
        <div className="text-[9px] font-mono text-cyan-600/90 uppercase tracking-widest mb-1">
          VLM 思考
        </div>
        <p className="text-[11px] font-mono text-cyan-100/90 leading-relaxed whitespace-pre-wrap">
          {thought || '（本节点无 VLM 思考文本）'}
        </p>
      </section>

      {cap ? (
        <section>
          <div className="text-[9px] font-mono text-slate-500 uppercase tracking-widest mb-1">
            VLM 图像描述
          </div>
          <p className="text-[11px] font-mono text-slate-200 leading-relaxed whitespace-pre-wrap">{cap}</p>
        </section>
      ) : null}

      {decision ? (
        <section>
          <div className="text-[9px] font-mono text-slate-500 uppercase tracking-widest mb-1">
            VLM 工具决策
          </div>
          <p className="text-[10px] font-mono text-amber-200/85 whitespace-pre-wrap">{decision}</p>
        </section>
      ) : null}

      <section>
        <div className="text-[9px] font-mono text-slate-500 uppercase tracking-widest mb-1">
          工具执行链
        </div>
        <ActionsList details={d as Record<string, unknown>} />
        {(!Array.isArray(d.actions) || (d.actions as unknown[]).length === 0) && (
          <p className="text-[10px] font-mono text-slate-600">暂无工具链记录</p>
        )}
      </section>

      {node.thumb_source ? (
        <section>
          <div className="text-[9px] font-mono text-slate-500 uppercase tracking-widest mb-1">
            缩略图来源说明
          </div>
          <p className="text-[10px] font-mono text-amber-300/90">{node.thumb_source}</p>
        </section>
      ) : null}

      {forcedNoImg ? (
        <section>
          <div className="text-[9px] font-mono text-slate-500 uppercase tracking-widest mb-1">
            强制总结（无新图时并入前序节点）
          </div>
          <p className="text-[10px] font-mono text-slate-300 whitespace-pre-wrap">{forcedNoImg}</p>
        </section>
      ) : null}

      {missionComplete ? (
        <section>
          <div className="text-[9px] font-mono text-slate-500 uppercase tracking-widest mb-1">任务结束</div>
          <p className="text-[10px] font-mono text-emerald-400/90 whitespace-pre-wrap">{missionComplete}</p>
        </section>
      ) : null}

      <section>
        <div className="text-[9px] font-mono text-slate-500 uppercase tracking-widest mb-1">
          原始载荷（调试）
        </div>
        <pre className="text-[9px] font-mono text-slate-400 whitespace-pre-wrap break-words max-h-80 overflow-auto bg-black/50 p-3 rounded border border-slate-800/80">
          {JSON.stringify(rawPayload, null, 2)}
        </pre>
      </section>
    </div>
  );
}
