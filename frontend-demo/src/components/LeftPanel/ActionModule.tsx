import { useState } from 'react';
import { TacticalPanel } from '../TacticalPanel';
import { CyberSelect } from '../CyberControls';
import { actionMlpOptions } from '../../mockData';

export type ActionType = 'satcomms' | 'satattitude';

interface ActionModuleProps {
  actionType: ActionType;
  onActionTypeChange: (t: ActionType) => void;
}

export const ActionModule = ({ actionType, onActionTypeChange }: ActionModuleProps) => {
  const [actionMlp, setActionMlp] = useState('track_mlp');

  return (
    <TacticalPanel title="动作执行模块">
      <div className="space-y-3">
        <div>
          <label className="text-slate-500 font-light tracking-wider text-[10px] font-mono block mb-1">
            动作 MLP 选择
          </label>
          <CyberSelect
            options={actionMlpOptions}
            value={actionMlp}
            onChange={setActionMlp}
          />
        </div>

        <div className="flex gap-2">
          {(['satcomms', 'satattitude'] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => onActionTypeChange(mode)}
              className={`flex-1 text-[12px] font-mono py-1.5 rounded transition-colors ${
                actionType === mode
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/50'
                  : 'text-slate-500 hover:text-slate-300 border border-slate-600'
              }`}
            >
              {mode === 'satcomms' ? '卫星通信' : '姿态控制'}
            </button>
          ))}
        </div>
      </div>
    </TacticalPanel>
  );
};
