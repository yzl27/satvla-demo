import { useState } from 'react';
import { TacticalPanel } from '../TacticalPanel';
import { CyberSelect } from '../CyberControls';
import { visionHeadOptions, mlpProjectorOptions, llmOptions } from '../../mockData';
import { useWorkflowStore } from '../../store/useWorkflowStore';

const STAGES = [
  { id: 'fast_check', short: 'S1', label: '全局感知' },
  { id: 'perception', short: 'S2', label: '战术指挥' },
  { id: 'specialist', short: 'S3', label: '局部精析' },
  { id: 'retrieval',  short: 'S4', label: '情报提取' },
  { id: 'reasoning',  short: 'S5', label: '报告生成' },
] as const;

type StageId = (typeof STAGES)[number]['id'];

function getStageStatus(
  id: StageId,
  activeNode: string | null,
  isExecuting: boolean,
  bypassMidPipeline: boolean,
): 'idle' | 'running' | 'done' | 'skipped' {
  const seq = STAGES.map((s) => s.id);
  const idx = seq.indexOf(id);
  const curIdx = activeNode === 'action'
    ? seq.length
    : seq.indexOf(activeNode as StageId);

  const done = activeNode === 'action';
  if (done && bypassMidPipeline && (idx === 1 || idx === 2 || idx === 3)) return 'skipped';
  if (idx < curIdx || (done && idx <= curIdx)) return 'done';
  if (idx === curIdx && isExecuting) return 'running';
  return 'idle';
}

const architectureOptions = [
  { value: 'multi_agent', label: '[M-AGT] Multi-Agent VLM' },
  { value: 'llava_e2e', label: '[L-VLM] End-to-End LLaVA' },
];

export const LLaVAControlPanel = () => {
  const [architecture, setArchitecture] = useState('multi_agent');
  const [visionHead, setVisionHead] = useState('clip');
  const [mlpProjector, setMlpProjector] = useState('2layer');
  const [llm, setLlm] = useState('vicuna_7b');

  const activeNode       = useWorkflowStore((s) => s.activeNode);
  const isExecuting      = useWorkflowStore((s) => s.isExecuting);
  const bypassMidPipeline = useWorkflowStore((s) => s.bypassMidPipeline);

  return (
    <TacticalPanel title="推理引擎架构">
      <div className="space-y-2">
        <div className="pb-2 border-b border-slate-800/80">
          <label className="text-slate-500 font-bold tracking-widest text-[10px] font-mono block mb-1">
            核心框架
          </label>
          <CyberSelect
            options={architectureOptions}
            value={architecture}
            onChange={setArchitecture}
          />
        </div>

        <div className="relative overflow-hidden transition-all duration-500">
          {architecture === 'multi_agent' && (
            <div className="space-y-2 animate-in fade-in slide-in-from-right-2 duration-300">
              {/* VLM 后端标签 */}
              <div className="flex items-center justify-between text-[9px] font-mono text-slate-500 px-0.5">
                <span>VLM</span>
                <span className="text-cyan-500">Qwen-VL · Ollama</span>
              </div>

              {/* 五阶段进度条 */}
              <div className="flex gap-1">
                {STAGES.map((s) => {
                  const status = getStageStatus(s.id, activeNode, isExecuting, bypassMidPipeline);
                  return (
                    <div key={s.id} className="flex-1 flex flex-col items-center gap-0.5" title={s.label}>
                      <div
                        className={`w-full h-1.5 rounded-full transition-all duration-500 ${
                          status === 'done'    ? 'bg-cyan-400 shadow-[0_0_4px_#22d3ee]' :
                          status === 'running' ? 'bg-amber-400 animate-pulse shadow-[0_0_6px_#f59e0b]' :
                          status === 'skipped' ? 'bg-slate-600 opacity-40' :
                                                 'bg-slate-700'
                        }`}
                      />
                      <span className={`text-[7px] font-mono leading-none ${
                        status === 'done'    ? 'text-cyan-500' :
                        status === 'running' ? 'text-amber-400' :
                        status === 'skipped' ? 'text-slate-600' :
                                               'text-slate-700'
                      }`}>
                        {s.short}
                      </span>
                    </div>
                  );
                })}
              </div>

              {/* 当前状态文字 */}
              <div className="text-[9px] font-mono text-right">
                {isExecuting ? (
                  <span className="text-amber-400 animate-pulse">
                    {STAGES.find((s) => s.id === activeNode)?.label ?? '初始化'} 运行中…
                  </span>
                ) : activeNode === 'action' ? (
                  <span className="text-emerald-400">任务完成</span>
                ) : (
                  <span className="text-slate-600">待命</span>
                )}
              </div>
            </div>
          )}

          {architecture === 'llava_e2e' && (
            <div className="space-y-2.5 animate-in fade-in slide-in-from-left-2 duration-300">
              <div>
                <label className="text-slate-500 font-light tracking-wider text-[10px] font-mono block mb-1">
                  视觉编码器
                </label>
                <CyberSelect
                  options={visionHeadOptions}
                  value={visionHead}
                  onChange={setVisionHead}
                />
              </div>
              <div>
                <label className="text-slate-500 font-light tracking-wider text-[10px] font-mono block mb-1">
                  MLP 投影层
                </label>
                <CyberSelect
                  options={mlpProjectorOptions}
                  value={mlpProjector}
                  onChange={setMlpProjector}
                />
              </div>
              <div>
                <label className="text-slate-500 font-light tracking-wider text-[10px] font-mono block mb-1">
                  大语言模型
                </label>
                <CyberSelect
                  options={llmOptions}
                  value={llm}
                  onChange={setLlm}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </TacticalPanel>
  );
};