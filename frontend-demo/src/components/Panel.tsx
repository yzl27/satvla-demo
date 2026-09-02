import type { ReactNode } from 'react';

interface PanelProps {
  title: string;
  children: ReactNode;
  className?: string;
}

export const Panel = ({ title, children, className = '' }: PanelProps) => (
  <div
    className={`flex flex-col rounded-lg overflow-hidden relative bg-[#080d19]/80 backdrop-blur-xl border border-slate-800 border-t-2 border-t-cyan-800/80 shadow-[0_10px_30px_-5px_rgba(0,0,0,0.8)] ${className}`}
  >
    <div className="shrink-0 flex items-center px-4 py-1 border-b border-slate-800/60 bg-gradient-to-b from-slate-800/30 to-transparent">
      <div className="w-2 h-2 rounded-full bg-cyan-500 shadow-[0_0_10px_#06b6d4] mr-2.5 shrink-0" />
      <h3 className="text-base font-bold text-cyan-300 tracking-[0.14em] uppercase font-mono antialiased leading-snug drop-shadow-[0_0_10px_rgba(34,211,238,0.45)]">
        {title}
      </h3>
    </div>
    <div className="p-4 flex-1 overflow-y-auto custom-scrollbar">{children}</div>
  </div>
);
