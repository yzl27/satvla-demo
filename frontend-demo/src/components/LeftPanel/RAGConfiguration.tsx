import { useState } from 'react';
import { TacticalPanel } from '../TacticalPanel';
import { CyberSelect } from '../CyberControls';
import {
  knowledgeBaseOptions,
  retrievalAlgorithmOptions,
  RETRIEVAL_ALGORITHM_WEB_SEARCH,
} from '../../mockData';

/** 与 CyberSelect 触发器同形：不可下拉，固定文案「网络知识库」（样式与选中项一致） */
function KnowledgeBaseInertShell() {
  return (
    <div className="relative w-full text-[11px] font-mono mb-1 pointer-events-none select-none">
      <div
        className="relative w-full px-3 py-2.5 flex justify-between items-center transition-all duration-300 bg-slate-900/80 border-2 border-slate-700 cursor-not-allowed"
        aria-hidden
      >
        <div className="absolute -top-1 -left-1 w-2 h-2 border-t-2 border-l-2 border-transparent" />
        <div className="absolute -bottom-1 -right-1 w-2 h-2 border-b-2 border-r-2 border-transparent" />
        <span className="flex-1 min-h-[1.25em] tracking-widest text-cyan-300 font-bold truncate drop-shadow-[0_0_5px_rgba(34,211,238,0.5)]">
          网络知识库
        </span>
        <div className="flex items-center gap-2 shrink-0">
          <div className="w-1 h-1 rounded-full bg-slate-600" />
          <svg
            className="w-3.5 h-3.5 text-slate-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>
    </div>
  );
}

export const RAGConfiguration = () => {
  const [knowledgeBase, setKnowledgeBase] = useState('test');
  const [retrievalAlgorithm, setRetrievalAlgorithm] = useState(RETRIEVAL_ALGORITHM_WEB_SEARCH);

  const webSearchOnly = retrievalAlgorithm === RETRIEVAL_ALGORITHM_WEB_SEARCH;

  return (
    <TacticalPanel title="RAG 检索配置">
      <div className="space-y-4">
        <div>
          <label className="text-slate-500 font-light tracking-wider text-[10px] font-mono block mb-1">
            检索算法
          </label>
          <CyberSelect
            options={retrievalAlgorithmOptions}
            value={retrievalAlgorithm}
            onChange={setRetrievalAlgorithm}
          />
        </div>
        <div>
          <label className="text-slate-500 font-light tracking-wider text-[10px] font-mono block mb-1">
            知识库
          </label>
          {webSearchOnly ? (
            <KnowledgeBaseInertShell />
          ) : (
            <CyberSelect
              options={knowledgeBaseOptions}
              value={knowledgeBase}
              onChange={setKnowledgeBase}
            />
          )}
        </div>
      </div>
    </TacticalPanel>
  );
};
