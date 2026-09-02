import { IntermediateOutput } from './IntermediateOutput';
import { SOAPOutput } from './SOAPOutput';
import { FinalActionResult } from './FinalActionResult';
import type { ActionType } from '../LeftPanel/ActionModule';

interface RightPanelProps {
  actionType: ActionType;
}

export const RightPanel = ({ actionType }: RightPanelProps) => (
  <aside className="w-[50%] max-w-[500px] h-full flex flex-col gap-4 min-w-0 border-l border-slate-800 pl-3">
    <div className="flex-[1.2] min-h-0 flex flex-col">
      <IntermediateOutput />
    </div>
    <div className="flex-[5.5] min-h-0 flex flex-col">
      <SOAPOutput />
    </div>
    <div className="flex-[2] min-h-0 flex flex-col">
      <FinalActionResult actionType={actionType} />
    </div>
  </aside>
);
