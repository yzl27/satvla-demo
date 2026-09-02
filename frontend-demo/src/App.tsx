import { useState } from 'react';
import { LeftPanel } from './components/LeftPanel';
import { CenterPanel } from './components/CenterPanel';
import { RightPanel } from './components/RightPanel';
import type { ActionType } from './components/LeftPanel/ActionModule';

export default function App() {
  const [actionType, setActionType] = useState<ActionType>('satcomms');

  return (
    <div className="relative flex h-screen w-screen bg-[#0f172a] p-4 gap-4 font-sans text-slate-300 overflow-hidden z-0 selection:bg-cyan-900 selection:text-cyan-50">
      {/* Ambient glow */}
      <div className="absolute top-[-10%] left-[-10%] w-[40vw] h-[40vw] bg-cyan-600/12 rounded-full blur-[120px] pointer-events-none -z-10" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40vw] h-[40vw] bg-blue-800/12 rounded-full blur-[120px] pointer-events-none -z-10" />

      <LeftPanel actionType={actionType} onActionTypeChange={setActionType} />
      <CenterPanel actionType={actionType} />
      <RightPanel actionType={actionType} />
    </div>
  );
}
