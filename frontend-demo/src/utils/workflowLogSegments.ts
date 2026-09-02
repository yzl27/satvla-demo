/**
 * 将 api_bridge 推送的 run.py 日志按 multiagent 五阶段切分，
 * 供 Node Workflow Chain 点击节点时展示对应阶段输出。
 */

export type WorkflowStageId =
  | 'fast_check'
  | 'perception'
  | 'specialist'
  | 'retrieval'
  | 'reasoning';

export function splitLogsByStage(logs: string[]): Record<WorkflowStageId, string[]> {
  const empty = (): Record<WorkflowStageId, string[]> => ({
    fast_check: [],
    perception: [],
    specialist: [],
    retrieval: [],
    reasoning: [],
  });
  const result = empty();

  let current: WorkflowStageId | null = null;

  for (const line of logs) {
    if (line.includes('🟢 阶段一')) current = 'fast_check';
    else if (line.includes('🟡 阶段二')) current = 'perception';
    else if (line.includes('🟠 阶段三')) current = 'specialist';
    else if (line.includes('🔵 阶段四')) current = 'retrieval';
    else if (line.includes('🟣 阶段五')) current = 'reasoning';

    if (line.includes('🎉 任务圆满结束')) {
      result.reasoning.push(line);
      continue;
    }

    if (current) {
      result[current].push(line);
    } else {
      // 阶段一之前的启动日志归入 Stage 1 展示
      result.fast_check.push(line);
    }
  }

  return result;
}
