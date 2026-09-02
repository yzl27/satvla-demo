import React from 'react';

interface TacticalPanelProps {
  title: string;
  subTitle?: string;
  children: React.ReactNode;
}

export const TacticalPanel: React.FC<TacticalPanelProps> = ({
  title,
  subTitle,
  children,
}) => {
  return (
    <div className="flex flex-col relative w-full h-full rounded-lg bg-[#080d19]/80 backdrop-blur-xl border border-slate-800 border-t-2 border-t-cyan-800/80 shadow-[0_10px_30px_-5px_rgba(0,0,0,0.8)] transition-all duration-500 group">
      {/* 顶部高光扫光边缘 (仅在鼠标悬停时显现) */}
      <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700" />

      {/* 标题栏：shrink-0 防止被压缩 */}
      <div className="shrink-0 flex justify-between items-end px-4 pt-4 pb-3 border-b border-slate-800/60 bg-gradient-to-b from-slate-800/30 to-transparent">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-2 h-2 rounded-full bg-cyan-500 shadow-[0_0_10px_#06b6d4] shrink-0" />
          <h3 className="font-mono text-base font-bold text-cyan-300 tracking-[0.14em] uppercase antialiased leading-snug drop-shadow-[0_0_10px_rgba(34,211,238,0.45)]">
            {title}
          </h3>
        </div>
        {subTitle && (
          <span className="font-mono text-[10px] text-slate-500 tracking-widest uppercase shrink-0">
            {subTitle}
          </span>
        )}
      </div>

      {/* 内容区：蓝图网格 + 雷达扫描线 */}
      <div
        className="flex-1 min-h-0 p-4 relative z-10 overflow-y-auto custom-scrollbar
          bg-[linear-gradient(rgba(6,182,212,0.08)_1px,transparent_1px),linear-gradient(90deg,rgba(6,182,212,0.08)_1px,transparent_1px)] bg-[size:20px_20px]
          before:content-[''] before:absolute before:inset-0 before:bg-[linear-gradient(transparent_0%,rgba(6,182,212,0.05)_50%,transparent_100%)] before:bg-[length:100%_4px] before:animate-[scanline_8s_linear_infinite] before:pointer-events-none"
      >
        {children}
      </div>
    </div>
  );
};
