import { LLaVAControlPanel } from './LLaVAControlPanel';
import { RAGConfiguration } from './RAGConfiguration';
import { SkillLibrary } from './SkillLibrary';
import { ActionModule, type ActionType } from './ActionModule';

interface LeftPanelProps {
  actionType: ActionType;
  onActionTypeChange: (t: ActionType) => void;
}

export const LeftPanel = ({ actionType, onActionTypeChange }: LeftPanelProps) => (
  <aside className="w-[30%] max-w-[320px] h-full flex flex-col gap-3 pb-2 pr-2">
    {/* LLaVA 模块：分配 3 份高度 */}
    <div className="flex-[3.4] min-h-0">
      <LLaVAControlPanel />
    </div>

    {/* RAG 模块：分配 2 份高度 */}
    <div className="flex-[3.5] min-h-0">
      <RAGConfiguration />
    </div>

    {/* SKILL 模块：分配 2 份高度 */}
    <div className="flex-[2.5] min-h-0">
      <SkillLibrary />
    </div>

    {/* ACTION 模块：分配 3 份高度 */}
    <div className="flex-[3] min-h-0">
      <ActionModule actionType={actionType} onActionTypeChange={onActionTypeChange} />
    </div>
  </aside>
);
