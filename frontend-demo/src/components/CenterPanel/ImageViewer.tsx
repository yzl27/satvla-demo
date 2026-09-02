import { useState, useEffect, useRef } from 'react';
import { useWorkflowStore } from '../../store/useWorkflowStore';
import { STAGE_COLOR } from '../../utils/imageLabels';

export const ImageViewer = () => {
  const { mainImageSrc, imageHistory, isExecuting } = useWorkflowStore();

  // ── 手动预览（胶片条点击锁定）vs 自动跟随 ─────────────
  const [pinned, setPinned] = useState<string | null>(null);
  const displayImg = pinned ?? mainImageSrc;

  // 新图到达时若没有锁定则自动解锁（保持跟随最新）
  useEffect(() => {
    if (!pinned) return;
    // 若用户在 AUTO 模式，什么都不做；pinned 由用户主动点击控制
  }, [mainImageSrc, pinned]);

  // ── 交叉淡入淡出 ──────────────────────────────────────
  // 用 ref 追踪"当前已渲染的图"，避免把 currentImg 放入依赖导致
  // React cleanup 在 setCurrentImg 触发重渲染后立即取消定时器（isFading 卡死）
  const shownImgRef = useRef(displayImg);
  const [currentImg, setCurrentImg] = useState(displayImg);
  const [prevImg, setPrevImg] = useState('');
  const [isFading, setIsFading] = useState(false);

  useEffect(() => {
    if (displayImg === shownImgRef.current) return;
    setPrevImg(shownImgRef.current);
    shownImgRef.current = displayImg;
    setCurrentImg(displayImg);
    setIsFading(true);
    const timer = setTimeout(() => setIsFading(false), 700);
    // cleanup 只在 displayImg 再次变化时才运行（快速切换时取消旧动画）
    return () => clearTimeout(timer);
  }, [displayImg]); // 只依赖 displayImg，不依赖 currentImg

  // ── 胶片条：自动滚动到最新帧 ──────────────────────────
  const filmstripRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (pinned) return; // 锁定时不自动滚动
    const el = filmstripRef.current;
    if (el) el.scrollLeft = el.scrollWidth;
  }, [imageHistory.length, pinned]);

  return (
    <div className="relative w-full h-full bg-black overflow-hidden tech-panel-clip tech-border border border-slate-600">

      {/* ── 图像渲染层 ─────────────────────────────────── */}
      <div className="absolute inset-0 w-full h-full">
        {/* 旧图淡出 */}
        {isFading && prevImg && (
          <img
            src={prevImg}
            alt="prev_state"
            className="absolute inset-0 w-full h-full object-cover z-10 transition-opacity duration-700 opacity-0"
          />
        )}
        {/* 当前图淡入 */}
        <img
          src={currentImg}
          alt="current_state"
          className={`absolute inset-0 w-full h-full object-cover z-20 transition-opacity duration-700 ease-in-out ${
            isFading ? 'opacity-0' : 'opacity-90 scale-105'
          }`}
        />
      </div>


      {/* ── 网格叠加 ──────────────────────────────────── */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:40px_40px] pointer-events-none z-10" />
      {isExecuting && (
        <div className="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] bg-[length:100%_4px,3px_100%] pointer-events-none z-10 opacity-20" />
      )}

      {/* ── REC 指示器 ────────────────────────────────── */}
      <div className="absolute top-2 left-3 flex items-center gap-2 font-mono text-[10px] text-red-500 z-40 bg-black/60 px-2 py-1 border border-red-900/50 rounded-sm">
        <div className={`w-2 h-2 rounded-full shadow-[0_0_8px_#ef4444] ${isExecuting ? 'bg-red-500 animate-pulse' : 'bg-red-800'}`} />
        {isExecuting ? '录制 // 实时画面' : '待机'}
      </div>

      {/* ── 执行中进度提示 ──────────────────────────────── */}
      {isExecuting && (
        <div className="absolute top-2 left-1/2 -translate-x-1/2 z-40 bg-amber-950/80 border border-amber-500/60 text-amber-400 font-mono text-[9px] px-3 py-1 tracking-widest animate-pulse">
          处理中...
        </div>
      )}

      {/* ── 锁定/自动模式标签 ─────────────────────────── */}
      {pinned && (
        <div
          className="absolute top-2 right-3 z-50 flex items-center gap-1 bg-violet-950/80 border border-violet-500/60 text-violet-300 font-mono text-[9px] px-2 py-1 cursor-pointer hover:bg-violet-900/80"
          onClick={() => setPinned(null)}
          title="点击恢复自动跟随"
        >
          <span className="text-[8px]">📌</span> 已锁定 — 点击恢复跟随
        </div>
      )}

      {/* ── 遥测数据 ──────────────────────────────────── */}
      <div className="absolute top-2 right-3 text-right font-mono text-[10px] z-40 bg-black/40 p-2 border-r-2 border-cyan-500 backdrop-blur-sm" style={{ display: pinned ? 'none' : undefined }}>
        <div><span className="text-slate-500">纬度:</span> <span className="text-cyan-400">34.0522° N</span></div>
        <div><span className="text-slate-500">经度:</span> <span className="text-cyan-400">118.2437° W</span></div>
        <div className="text-slate-500 mt-1">高度: 450.2 KM</div>
        <div className={`mt-1 animate-pulse ${isExecuting ? 'text-amber-400' : 'text-cyan-400'}`}>
          {isExecuting ? '数传: 活跃' : '数传: 安全'}
        </div>
      </div>

      {/* ── 准星 ──────────────────────────────────────── */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-20">
        <div className="relative w-40 h-40 opacity-40">
          <div className="absolute top-0 bottom-0 left-1/2 w-[1px] bg-cyan-400 transform -translate-x-1/2" />
          <div className="absolute left-0 right-0 top-1/2 h-[1px] bg-cyan-400 transform -translate-y-1/2" />
          <div className="absolute inset-0 border border-cyan-400/40 rounded-full border-dashed animate-[spin_30s_linear_infinite]" />
          <div className="absolute inset-10 border border-cyan-400/20 rounded-full" />
        </div>
      </div>

      {/* ── 处理链胶片条（悬浮在底部，不改变外层高度）─── */}
      <div
        ref={filmstripRef}
        className="absolute bottom-0 left-0 right-0 h-[58px] z-50 bg-black/80 backdrop-blur-sm border-t border-slate-700/70 flex items-center gap-1.5 px-2 overflow-x-auto scrollbar-thin scrollbar-thumb-slate-600 scrollbar-track-transparent"
      >
        {imageHistory.length === 0 ? (
          <span className="text-slate-600 font-mono text-[9px] ml-2 whitespace-nowrap">
            暂无图像历史
          </span>
        ) : (
          imageHistory.map((rec, idx) => {
            const isActive = (pinned ?? mainImageSrc) === rec.src;
            return (
              <button
                key={`${idx}-${rec.src}`}
                onClick={() => setPinned((prev) => (prev === rec.src ? null : rec.src))}
                title={rec.label}
                className={`relative shrink-0 w-[48px] h-[40px] border overflow-hidden rounded-sm transition-all ${
                  isActive
                    ? 'border-cyan-400 shadow-[0_0_6px_#22d3ee] scale-105'
                    : 'border-slate-600/60 hover:border-slate-400 opacity-70 hover:opacity-100'
                }`}
              >
                <img
                  src={rec.src}
                  alt={rec.label}
                  className="w-full h-full object-cover"
                  onError={(e) => { (e.currentTarget as HTMLImageElement).style.opacity = '0.3'; }}
                />
                {/* 序号徽章 */}
                <span className="absolute top-0 left-0 bg-black/70 text-[7px] font-mono text-slate-400 leading-none px-0.5 py-0.5">
                  {idx + 1}
                </span>
                {/* 阶段标签 */}
                <div className={`absolute bottom-0 left-0 right-0 bg-black/75 text-[7px] font-mono text-center leading-tight py-0.5 truncate ${STAGE_COLOR[rec.stageTag] ?? 'text-slate-400'}`}>
                  {rec.label}
                </div>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
};
