import type { WorkflowStageId } from './workflowLogSegments';

/** 弹窗顶部一句话摘要（基于该阶段日志启发式） */
export function buildStageSummary(nodeId: WorkflowStageId, lines: string[]): string {
  if (lines.length === 0) {
    return 'No live logs for this stage yet. Structured artifact (if any) and demo text appear below.';
  }
  const text = lines.join('\n');

  if (nodeId === 'fast_check') {
    const m = text.match(/共发现\s*(\d+)\s*个目标/);
    if (m) return `Global QC complete: ${m[1]} target(s) detected on the current frame.`;
    if (text.includes('复原成功')) return 'Restoration / enhancement tools ran; pipeline advanced toward detection.';
    return 'Stage 1 activity recorded; see raw trace below.';
  }
  if (nodeId === 'perception') {
    if (text.includes('0 个目标')) return 'Zero targets: mid-pipeline bypass to Stage 5 per state_machine fallback.';
    const m = text.match(/确定优先级队列（共\s*(\d+)\s*个）/);
    if (m) return `Tactical queue built with ${m[1]} prioritized ROI(s).`;
    return 'Stage 2 command & queue logic executed.';
  }
  if (nodeId === 'specialist') {
    if (text.includes('队列为空，跳过阶段三')) return 'Empty queue — no local specialist passes.';
    if (text.includes('情报提取完成')) return 'Local crop analysis produced per-target intel.';
    return 'Stage 3 local tool loop activity recorded.';
  }
  if (nodeId === 'retrieval') {
    if (text.includes('无局部细节，跳过检索')) return 'No local details — RAG stage skipped with placeholder doc.';
    if (text.includes('检索完成')) return 'Keyword extraction + RAG search finished.';
    return 'Stage 4 intel extraction / search activity recorded.';
  }
  if (nodeId === 'reasoning') {
    if (text.includes('任务圆满结束')) return 'Final SOAP report written to workspace.';
    return 'Stage 5 report generation in progress or completed.';
  }
  return `${lines.length} log line(s) in this stage.`;
}
