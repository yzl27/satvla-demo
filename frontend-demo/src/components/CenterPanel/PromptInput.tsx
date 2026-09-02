import { useState } from 'react';
import { useWorkflowStore } from '../../store/useWorkflowStore';

export const PromptInput = () => {
  const [cmd, setCmd] = useState('');
  const { startMission, isExecuting } = useWorkflowStore();

  const handleExecute = () => {
    const imagePath = cmd.trim();
    startMission(imagePath || undefined);
    setCmd('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isExecuting) {
      handleExecute();
    }
  };

  return (
    <div
      className={`relative w-full flex items-stretch mt-2 rounded-md bg-[#080d19]/90 backdrop-blur-md border border-slate-700/80 border-t-2 overflow-hidden group transition-all duration-300 ${
        isExecuting
          ? 'border-t-amber-600/70 shadow-[0_10px_30px_rgba(0,0,0,0.8),inset_0_0_20px_rgba(245,158,11,0.08)]'
          : 'border-t-emerald-700/50 shadow-[0_10px_30px_rgba(0,0,0,0.8),inset_0_0_15px_rgba(16,185,129,0.05)] focus-within:border-t-emerald-500 focus-within:shadow-[0_10px_30px_rgba(0,0,0,0.8),inset_0_0_20px_rgba(16,185,129,0.1)]'
      }`}
    >
      {/* 终端提示符区域 */}
      <div className="bg-slate-900/80 px-4 py-3 flex items-center border-r border-slate-700/80 shrink-0 relative">
        <span className="text-emerald-500 font-mono text-xs whitespace-nowrap drop-shadow-[0_0_5px_rgba(16,185,129,0.4)]">
          root@sat-vla<span className="text-slate-500">:~#</span>
        </span>
        <span className="ml-1.5 w-1.5 h-3.5 bg-emerald-500/80 animate-blink shadow-[0_0_5px_#10b981]" />
      </div>

      {/* 输入区：接受图片路径作为任务参数 */}
      <input
        type="text"
        value={cmd}
        onChange={(e) => setCmd(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={isExecuting}
        placeholder={
          isExecuting
            ? '任务进行中...'
            : '输入图像路径（如 /path/to/image.png）或留空使用默认图像'
        }
        className="flex-1 bg-transparent text-emerald-400 font-mono text-xs px-4 outline-none placeholder:text-slate-700 focus:bg-emerald-950/10 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      />

      {/* 执行按钮 */}
      <button
        type="button"
        onClick={handleExecute}
        disabled={isExecuting}
        className={`relative px-6 border-l border-slate-700/80 text-[11px] font-bold tracking-[0.2em] uppercase transition-all duration-300 flex items-center gap-2 group/btn overflow-hidden disabled:cursor-not-allowed ${
          isExecuting
            ? 'bg-amber-950/40 text-amber-500 border-amber-800/50'
            : 'bg-slate-900/50 hover:bg-emerald-950/60 hover:border-emerald-600/50 text-slate-400 hover:text-emerald-400'
        }`}
      >
        {/* 按钮悬停扫描线 */}
        {!isExecuting && (
          <div className="absolute inset-0 bg-[linear-gradient(transparent_0%,rgba(16,185,129,0.2)_50%,transparent_100%)] bg-[length:100%_4px] animate-[scanline_2s_linear_infinite] opacity-0 group-hover/btn:opacity-100 transition-opacity pointer-events-none" />
        )}
        <div className="absolute left-0 top-0 bottom-0 w-1 bg-transparent group-hover/btn:bg-emerald-500 transition-colors" />

        {isExecuting ? (
          <>
            <span className="relative z-10 w-2 h-2 rounded-full bg-amber-500 animate-ping" />
            <span className="relative z-10">运行中</span>
          </>
        ) : (
          <>
            <span className="relative z-10 drop-shadow-[0_0_5px_rgba(16,185,129,0)] group-hover/btn:drop-shadow-[0_0_5px_rgba(16,185,129,0.6)]">
              执 行
            </span>
            <svg
              className="relative z-10 w-3.5 h-3.5 group-hover/btn:translate-x-1 transition-transform"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
            </svg>
          </>
        )}
      </button>
    </div>
  );
};
