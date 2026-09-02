import { useEffect, useState, type ReactNode } from 'react';
import { getHttpApiBase } from '../../utils/apiBase';
import { buildStageSummary } from '../../utils/workflowStageSummary';
import type { WorkflowStageId } from '../../utils/workflowLogSegments';

const DOC_FILE: Record<WorkflowStageId, string | null> = {
  fast_check: 'Doc1_Global.json',
  perception: 'Doc2_Queue.json',
  specialist: 'Doc3_Details.json',
  retrieval: 'Doc4_Search.json',
  reasoning: null,
};

interface Props {
  nodeId: WorkflowStageId;
  stageLines: string[];
  soapRawText: string;
  workflowTaskId: string | null;
  fallbackBody: ReactNode;
}

export function WorkflowNodeModalBody({
  nodeId,
  stageLines,
  soapRawText,
  workflowTaskId,
  fallbackBody,
}: Props) {
  const summary = buildStageSummary(nodeId, stageLines);
  const docName = DOC_FILE[nodeId];

  const [artifact, setArtifact] = useState<string | null>(null);
  const [artifactErr, setArtifactErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!workflowTaskId || !docName) {
      setArtifact(null);
      setArtifactErr(null);
      setLoading(false);
      return;
    }
    const url = `${getHttpApiBase()}/workspace/${workflowTaskId}/${docName}`;
    setLoading(true);
    setArtifact(null);
    setArtifactErr(null);
    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
        return r.text();
      })
      .then((t) => {
        try {
          const parsed = JSON.parse(t);
          setArtifact(JSON.stringify(parsed, null, 2));
        } catch {
          setArtifact(t);
        }
      })
      .catch((e: Error) => setArtifactErr(e.message))
      .finally(() => setLoading(false));
  }, [workflowTaskId, docName, nodeId]);

  const rawTracePlaceholder =
    stageLines.length === 0 ? (
      nodeId === 'reasoning' && soapRawText.trim() ? (
        <p className="text-[10px] font-mono text-slate-500">
          No split log lines for stage 5; use the SOAP block above or run another mission.
        </p>
      ) : (
        fallbackBody
      )
    ) : null;

  return (
    <div className="space-y-4">
      <section>
        <div className="text-[9px] font-mono text-slate-500 uppercase tracking-widest mb-1">
          Summary
        </div>
        <p className="text-[11px] font-mono text-cyan-100/90 leading-relaxed">{summary}</p>
      </section>

      {docName && (
        <section>
          <div className="text-[9px] font-mono text-slate-500 uppercase tracking-widest mb-1">
            Structured artifact · {docName}
          </div>
          {!workflowTaskId && (
            <p className="text-[10px] font-mono text-slate-500">
              Run a mission to capture task id; JSON loads from{' '}
              <code className="text-cyan-600/90">/workspace/&lt;task&gt;/…</code>.
            </p>
          )}
          {workflowTaskId && loading && (
            <p className="text-[10px] font-mono text-amber-400/90 animate-pulse">Loading…</p>
          )}
          {artifactErr && (
            <p className="text-[10px] font-mono text-rose-400/90">{artifactErr}</p>
          )}
          {artifact && (
            <pre className="text-[9px] font-mono text-slate-300 bg-slate-950/80 border border-slate-700 rounded p-2 max-h-52 overflow-auto whitespace-pre-wrap custom-scrollbar">
              {artifact}
            </pre>
          )}
        </section>
      )}

      {nodeId === 'reasoning' && soapRawText.trim() && (
        <section>
          <div className="text-[9px] font-mono text-slate-500 uppercase tracking-widest mb-1">
            SOAP report (full text)
          </div>
          <pre className="text-[9px] font-mono text-slate-300 bg-slate-950/80 border border-slate-700 rounded p-2 max-h-56 overflow-auto whitespace-pre-wrap custom-scrollbar">
            {soapRawText}
          </pre>
        </section>
      )}

      <section>
        <div className="text-[9px] font-mono text-slate-500 uppercase tracking-widest mb-1">
          Raw stage trace
        </div>
        {stageLines.length > 0 ? (
          <pre className="text-[10px] font-mono text-slate-300 whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto custom-scrollbar border border-slate-800 rounded p-2 bg-slate-950/40">
            {stageLines.join('\n')}
          </pre>
        ) : (
          <div className="text-[10px] font-mono text-slate-500 border border-slate-800 border-dashed rounded p-2">
            {rawTracePlaceholder}
          </div>
        )}
      </section>
    </div>
  );
}
