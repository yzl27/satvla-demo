import { Panel } from '../Panel';
import type { ParsedSOAP } from '../../store/useWorkflowStore';
import { useWorkflowStore } from '../../store/useWorkflowStore';
import { useStreamText } from '../../hooks/useStreamText';

const CARD_CONFIG = [
  {
    key: 'S' as const,
    title: '【S - 主观背景】',
    intro: '任务背景与情报假设：场景来源、关注点及需回答的核心问题。',
    border: 'border-l-blue-500',
    bg: 'from-blue-500/10',
    headerText: 'text-blue-400',
    cursor: 'bg-blue-400',
  },
  {
    key: 'O' as const,
    title: '【O - 客观观测】',
    intro: '可验证事实与观测结果：图像、检测、量测与工具产出的客观描述。',
    border: 'border-l-emerald-500',
    bg: 'from-emerald-500/10',
    headerText: 'text-emerald-400',
    cursor: 'bg-emerald-400',
  },
  {
    key: 'A' as const,
    title: '【A - 情报评估】',
    intro: '综合研判：对威胁、机会与不确定性的判断及置信度梗概。',
    border: 'border-l-amber-500',
    bg: 'from-amber-500/10',
    headerText: 'text-amber-400',
    cursor: 'bg-amber-400',
  },
  {
    key: 'P' as const,
    title: '【P - 行动建议】',
    intro: '后续动作与资源协调：可执行的步骤、优先级与风险提示。',
    border: 'border-l-rose-500',
    bg: 'from-rose-500/10',
    headerText: 'text-rose-400',
    cursor: 'bg-rose-400',
  },
] as const;

const KEY_TO_PARSED: Record<string, keyof ParsedSOAP> = {
  S: 'subjective',
  O: 'objective',
  A: 'assessment',
  P: 'plan',
};

type CardDef = (typeof CARD_CONFIG)[number];

function SOAPStreamBlock({
  card,
  sourceText,
  hasRealData,
  isExecuting,
  streamIndex,
}: {
  card: CardDef;
  sourceText: string;
  hasRealData: boolean;
  isExecuting: boolean;
  /** 0–3：错开起始时间，形成连续输出感 */
  streamIndex: number;
}) {
  const { title, intro, border, bg, headerText, cursor } = card;
  const runStream = hasRealData && sourceText.length > 0;
  const { display, streaming } = useStreamText(sourceText, runStream, {
    startDelayMs: streamIndex * 140,
    charsPerTick: 4,
    tickMs: 10,
  });

  const body = runStream ? display : isExecuting ? '…' : intro;
  const isReal = runStream;
  const showCursor = (isExecuting && !hasRealData) || (runStream && streaming);

  return (
    <div
      className={`relative w-full bg-slate-900/30 border border-slate-700/50 border-l-2 ${border} bg-gradient-to-r ${bg} to-transparent p-3 overflow-hidden`}
    >
      <div className="flex items-center gap-2 mb-2 border-b border-slate-700/50 pb-1.5 relative z-20">
        <span
          className={`font-mono text-sm font-bold tracking-wide antialiased ${headerText} drop-shadow-[0_0_10px_currentColor]`}
        >
          {title}
        </span>
      </div>

      <div
        className={`font-mono text-[12px] leading-relaxed whitespace-pre-wrap relative z-20 min-h-[1.25rem] ${
          isReal
            ? 'text-slate-300'
            : isExecuting
              ? 'text-slate-300'
              : 'text-slate-500 italic'
        }`}
      >
        {body}
        {showCursor && (
          <span
            className={`inline-block w-1.5 h-3 ml-0.5 align-middle animate-blink ${cursor}`}
          />
        )}
      </div>
    </div>
  );
}

export const SOAPOutput = () => {
  const { parsedSOAP, hasRealData, isExecuting } = useWorkflowStore();

  return (
    <Panel title="SOAP 分析报告" className="h-full min-h-0">
      {isExecuting && !hasRealData && (
        <div className="flex items-center gap-2 mb-3 px-2 py-1.5 bg-amber-950/30 border border-amber-900/50 rounded">
          <span className="w-1.5 h-1.5 bg-amber-500 rounded-full animate-ping" />
          <span className="text-[9px] text-amber-400 font-mono tracking-wider">
            等待任务报告...
          </span>
        </div>
      )}
      {hasRealData && (
        <div className="flex items-center gap-2 mb-3 px-2 py-1.5 bg-emerald-950/30 border border-emerald-900/50 rounded">
          <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />
          <span className="text-[9px] text-emerald-400 font-mono tracking-wider">
            实时情报报告（逐段输出）
          </span>
        </div>
      )}

      <div className="space-y-3">
        {CARD_CONFIG.map((card, idx) => {
          const sourceText =
            hasRealData && parsedSOAP
              ? parsedSOAP[KEY_TO_PARSED[card.key]] ?? ''
              : '';

          return (
            <SOAPStreamBlock
              key={card.key}
              card={card}
              sourceText={sourceText}
              hasRealData={hasRealData}
              isExecuting={isExecuting}
              streamIndex={idx}
            />
          );
        })}
      </div>
    </Panel>
  );
};
