import { Panel } from '../Panel';
import { actionResultOutput } from '../../mockData';
import { useWorkflowStore } from '../../store/useWorkflowStore';
import type { ActionType } from '../LeftPanel/ActionModule';

interface FinalActionResultProps {
  actionType: ActionType;
}

export const FinalActionResult = ({ actionType }: FinalActionResultProps) => {
  const isExecuting = useWorkflowStore((s) => s.isExecuting);
  const hasRealData = useWorkflowStore((s) => s.hasRealData);

  const showDone = hasRealData && !isExecuting;

  return (
    <Panel title="任务执行结果" className="h-full min-h-0">
      <div className="flex flex-col h-full">
        {/* VLA Closed Loop - 固定头部 */}
        <div
          className={`shrink-0 relative border rounded-lg p-3 overflow-hidden min-h-[60px] ${
            showDone
              ? 'border-emerald-500/30 bg-emerald-950/20'
              : isExecuting
                ? 'border-amber-500/30 bg-amber-950/15'
                : 'border-slate-600/40 bg-slate-900/30'
          }`}
        >
          <div
            className={`text-[9px] font-mono uppercase tracking-widest mb-2 ${
              showDone ? 'text-emerald-500' : isExecuting ? 'text-amber-500' : 'text-slate-500'
            }`}
          >
            VLA 闭环控制
          </div>
          <div
            className={`font-mono text-sm font-bold ${
              showDone
                ? 'text-emerald-400 text-glow-cyan'
                : isExecuting
                  ? 'text-amber-400'
                  : 'text-slate-500'
            }`}
          >
            {showDone
              ? `${actionResultOutput.action} 已执行`
              : isExecuting
                ? '任务执行中…'
                : '未执行'}
          </div>
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-slate-900">
            <div
              className={`h-full transition-all duration-1000 ${
                showDone ? 'w-full bg-emerald-500' : isExecuting ? 'w-2/3 bg-amber-500 animate-pulse' : 'w-0'}
              `}
            />
          </div>
        </div>

        {/* 动态内容区：固定高度 + key 触发切换动效；仅任务完成后展示 mock 详情 */}
        <div className="flex-1 min-h-[120px] flex flex-col mt-3 relative overflow-hidden">
          {!showDone ? (
            <div className="text-[10px] font-mono text-slate-500 px-1 py-2">
              {isExecuting ? '等待闭环输出…' : '执行完成后将显示卫星通信 / 姿态等摘要。'}
            </div>
          ) : (
            <div
              key={actionType}
              className="absolute inset-0 flex flex-col animate-fade-slide-in"
            >
              {actionType === 'satcomms' ? (
                <div className="flex flex-col h-full justify-start">
                  <div className="border-t border-slate-600 pt-2 space-y-1">
                    <div className="text-[9px] text-slate-500 font-mono uppercase mb-2">卫星通信输出</div>
                    <div className="flex justify-between text-[10px] font-mono">
                      <span className="text-slate-400">压缩率</span>
                      <span className="text-cyan-400">{(actionResultOutput.satComms.compressionRate * 100).toFixed(1)}%</span>
                    </div>
                    <div className="flex justify-between text-[10px] font-mono">
                      <span className="text-slate-400">下行优先级</span>
                      <span className="text-cyan-400">{actionResultOutput.satComms.downlinkPriority}</span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col h-full justify-start gap-2">
                  <div className="border-t border-slate-600 pt-2 space-y-1">
                    <div className="text-[9px] text-slate-500 font-mono uppercase mb-2">卫星姿态输出</div>
                    <div className="flex justify-between text-[10px] font-mono">
                      <span className="text-slate-400">滚转角 (°)</span>
                      <span className="text-cyan-400">{actionResultOutput.satAttitude.rollAngle}</span>
                    </div>
                    <div className="flex justify-between text-[10px] font-mono">
                      <span className="text-slate-400">俯仰角 (°)</span>
                      <span className="text-cyan-400">{actionResultOutput.satAttitude.pitchAngle}</span>
                    </div>
                    <div className="flex justify-between text-[10px] font-mono">
                      <span className="text-slate-400">偏航角 (°)</span>
                      <span className="text-cyan-400">{actionResultOutput.satAttitude.yawAngle}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </Panel>
  );
};
