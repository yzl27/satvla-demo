import { ImageViewer } from './ImageViewer';
import { CoTFlowCanvas } from './CoTFlowCanvas';
import { PromptInput } from './PromptInput';
import type { ActionType } from '../LeftPanel/ActionModule';

interface CenterPanelProps {
  actionType: ActionType;
}

export const CenterPanel = ({ actionType: _actionType }: CenterPanelProps) => (
  <main className="flex-1 flex flex-col gap-3 h-full min-w-0 border-x border-slate-800 px-3">
    
    {/* ⚡ 核心修改：将原本的 h-[38%] 提升到 h-[65%] (或者 h-[68%])，让图片占据绝对主导地位 */}
    <div className="h-[55%] shrink-0 relative">
      <ImageViewer />
    </div>

    {/* 流程图容器：与 TacticalPanel / Panel 一致的全息玻璃外框 */}
    <div className="flex-1 flex flex-col min-h-0 relative rounded-lg bg-[#080d19]/80 backdrop-blur-xl border border-slate-800 border-t-2 border-t-cyan-800/80 shadow-[0_10px_30px_-5px_rgba(0,0,0,0.8)] overflow-hidden group transition-all duration-500">
      <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />
      <div className="shrink-0 flex items-end px-4 pt-4 pb-3 border-b border-slate-800/60 bg-gradient-to-b from-slate-800/30 to-transparent relative z-10">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-2 h-2 rounded-full bg-cyan-500 shadow-[0_0_10px_#06b6d4] shrink-0" />
          <h3 className="font-mono text-base font-bold text-cyan-300 tracking-[0.12em] antialiased leading-snug drop-shadow-[0_0_10px_rgba(34,211,238,0.45)]">
            思维链展示区
          </h3>
        </div>
      </div>
      <div className="flex-1 min-h-0 relative z-10">
        <CoTFlowCanvas />
      </div>
    </div>

    {/* 底部指令输入框：保持不变 */}
    <div className="shrink-0 pb-1">
      <PromptInput />
    </div>
    
  </main>
);
