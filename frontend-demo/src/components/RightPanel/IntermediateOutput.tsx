import { useEffect, useState } from 'react';
import { Panel } from '../Panel';
import { NodeModal } from '../CenterPanel/NodeModal';
import { useWorkflowStore } from '../../store/useWorkflowStore';

const ASSET_BASE = 'http://localhost:8000';

interface Doc4Data {
  keyword: string;
  result: string;
}

interface SummaryBlock {
  body: string;
  source?: string;
}

/** 仅从 Doc4 result 中解析「综合摘要」块，供按钮与弹窗使用 */
function parseSummaryOnly(raw: string): SummaryBlock | null {
  const blocks = raw.split(/(?=【)/).filter(Boolean);
  const block = blocks.find((b) => /^【综合摘要】/.test(b));
  if (!block) return null;
  const rest = block.replace(/^【[^\]】]+[】\]]/, '').trim();
  const sourceMatch = rest.match(/来源:\s*(https?:\/\/\S+)/);
  const source = sourceMatch ? sourceMatch[1] : undefined;
  const body = rest.replace(/来源:\s*https?:\/\/\S+/, '').trim();
  if (!body) return null;
  return { body, source };
}

export const IntermediateOutput = () => {
  const workflowTaskId = useWorkflowStore((s) => s.workflowTaskId);
  const runId = useWorkflowStore((s) => s.runId);
  const activeNode = useWorkflowStore((s) => s.activeNode);
  const isExecuting = useWorkflowStore((s) => s.isExecuting);

  const [doc4, setDoc4] = useState<Doc4Data | null>(null);
  const [loading, setLoading] = useState(false);
  const [summaryModalOpen, setSummaryModalOpen] = useState(false);
  const [retrievalModalOpen, setRetrievalModalOpen] = useState(false);

  useEffect(() => {
    setDoc4(null);
    setSummaryModalOpen(false);
    setRetrievalModalOpen(false);
  }, [runId]);

  useEffect(() => {
    if (!workflowTaskId) {
      setDoc4(null);
      return;
    }

    let cancelled = false;

    const fetchDoc4 = async () => {
      setLoading(true);
      try {
        const res = await fetch(
          `${ASSET_BASE}/workspace/${workflowTaskId}/Doc4_Search.json`,
        );
        if (!cancelled && res.ok) {
          const data: Doc4Data = await res.json();
          setDoc4(data);
          setLoading(false);
          return true;
        }
      } catch {
        /* 文件还未生成，等下次轮询 */
      }
      setLoading(false);
      return false;
    };

    let timer: ReturnType<typeof setInterval>;
    fetchDoc4().then((ok) => {
      if (!ok && !cancelled) {
        timer = setInterval(async () => {
          const success = await fetchDoc4();
          if (success && timer) clearInterval(timer);
        }, 3000);
      }
    });

    return () => {
      cancelled = true;
      if (timer) clearInterval(timer);
    };
  }, [workflowTaskId]);

  const summarySection = doc4 ? parseSummaryOnly(doc4.result) : null;

  const stageStatus =
    activeNode === 'retrieval' && isExecuting
      ? 'running'
      : doc4
        ? 'done'
        : 'idle';

  const retrievalStatusLabel =
    loading && !doc4
      ? '正在加载检索结果…'
      : stageStatus === 'running' && !doc4
        ? '检索中…'
        : doc4
          ? '检索完成'
          : '等待任务';

  return (
    <Panel title="RAG Intel Retrieval" className="h-full min-h-0">
      <div className="flex flex-col h-full gap-2 overflow-hidden min-h-0">
        <div className="shrink-0 flex flex-row gap-2 min-h-0 min-w-0 items-stretch">
          <div className="min-w-0 flex-1 flex flex-col justify-stretch">
            <button
              type="button"
              onClick={() => setRetrievalModalOpen(true)}
              aria-label="打开阶段四 RAG 检索详情"
              className="w-full h-full min-h-[2rem] rounded-lg overflow-hidden bg-black/90 border border-amber-950/50 font-mono text-[9px] min-w-0 flex flex-row items-center justify-between gap-2 shadow-inner ring-1 ring-slate-700/50 hover:border-amber-700/60 hover:ring-amber-500/25 transition-all px-3 py-1.5"
            >
              <span className="text-[16px] font-bold text-amber-200/95 tracking-wide truncate min-w-0">
                RAG 检索
              </span>
              <span className="text-[12px] font-mono text-amber-500/70 shrink-0">点击查看详情</span>
            </button>
          </div>

          {summarySection && (
            <div className="min-w-0 flex-1 flex flex-col justify-stretch">
              <button
                type="button"
                onClick={() => setSummaryModalOpen(true)}
                aria-label="打开综合摘要全文"
                className="w-full h-full min-h-[2rem] rounded-lg overflow-hidden bg-black/90 border font-mono text-[9px] min-w-0 flex flex-row items-center justify-between gap-2 shadow-inner ring-1 ring-slate-700/50 border-slate-700/60 hover:border-cyan-700/70 hover:ring-cyan-500/35 transition-all px-3 py-1.5"
              >
                <span className="text-[16px] font-bold text-violet-300/95 tracking-wide truncate min-w-0">
                  综合摘要
                </span>
                <span className="text-[12px] font-mono text-cyan-500/80 shrink-0">点击查看全文</span>
              </button>
            </div>
          )}
        </div>

        {loading && !doc4 && (
          <p className="shrink-0 text-[10px] font-mono text-slate-500 px-1 animate-pulse">
            正在加载检索结果…
          </p>
        )}

        {!loading && !doc4 && (
          <p className="shrink-0 text-[10px] font-mono text-slate-600 px-1">
            阶段四完成后，关键词与综合摘要将显示于此。
          </p>
        )}

        <div className="flex-1 min-h-0" />
      </div>

      {retrievalModalOpen && (
        <NodeModal
          title="阶段四 · RAG 情报检索"
          onClose={() => setRetrievalModalOpen(false)}
          maxWidthClassName="max-w-2xl"
        >
          <div className="space-y-4 text-[10px] font-mono">
            <section>
              <div className="text-[9px] text-slate-500 uppercase tracking-widest mb-1.5">
                状态
              </div>
              <p
                className={`${
                  doc4 ? 'text-cyan-400/95' : stageStatus === 'running' ? 'text-amber-400' : 'text-slate-400'
                }`}
              >
                {retrievalStatusLabel}
              </p>
            </section>
            <section>
              <div className="text-[9px] text-slate-500 uppercase tracking-widest mb-1.5">
                检索关键词
              </div>
              <p className="text-slate-200 whitespace-pre-wrap break-words leading-relaxed">
                {doc4?.keyword?.trim() ? `🔍 ${doc4.keyword}` : '—'}
              </p>
            </section>
            {workflowTaskId ? (
              <section>
                <div className="text-[9px] text-slate-500 uppercase tracking-widest mb-1.5">
                  任务 ID
                </div>
                <p className="text-slate-400 break-all text-[9px] leading-relaxed">{workflowTaskId}</p>
              </section>
            ) : null}
          </div>
        </NodeModal>
      )}

      {summaryModalOpen && summarySection && (
        <NodeModal
          title="综合摘要"
          onClose={() => setSummaryModalOpen(false)}
          maxWidthClassName="max-w-2xl"
        >
          <p className="text-[10px] font-mono text-slate-300 whitespace-pre-wrap leading-relaxed">
            {summarySection.body}
          </p>
          {summarySection.source && (
            <a
              href={summarySection.source}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 inline-block text-[9px] font-mono text-cyan-600 hover:text-cyan-400 break-all transition-colors"
            >
              ↗ {summarySection.source}
            </a>
          )}
        </NodeModal>
      )}
    </Panel>
  );
};
