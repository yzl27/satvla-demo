import { useState, useRef, useEffect, type InputHTMLAttributes } from 'react';

// ─── 1. 战术框架版下拉框 (Tactical Frame Select) ──────────────────────────────────
interface Option {
  value: string;
  label: string;
}

interface CyberSelectProps {
  options: Option[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  /** 为 true 时不展开、不响应选择，样式置灰 */
  disabled?: boolean;
}

export const CyberSelect: React.FC<CyberSelectProps> = ({
  options,
  value,
  onChange,
  placeholder = 'Select...',
  disabled = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const selectedLabel = options.find((opt) => opt.value === value)?.label || placeholder;

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (disabled) setIsOpen(false);
  }, [disabled]);

  return (
    <div
      className={`relative w-full text-[11px] font-mono mb-1 ${disabled ? 'pointer-events-none opacity-45 select-none' : ''}`}
      ref={containerRef}
    >
      {/* 触发器：2px 强化边框 + 护角装饰 */}
      <div
        onClick={() => !disabled && setIsOpen(!isOpen)}
        className={`relative w-full px-3 py-2.5 flex justify-between items-center transition-all duration-300 group ${
          disabled
            ? 'bg-slate-950/80 border-slate-800 cursor-not-allowed'
            : isOpen
              ? 'bg-cyan-950/40 border-cyan-400 shadow-[0_0_20px_rgba(6,182,212,0.3),inset_0_0_10px_rgba(6,182,212,0.2)] cursor-pointer'
              : 'bg-slate-900/80 border-slate-700 hover:border-cyan-600 hover:bg-slate-800 cursor-pointer'
        } border-2`}
      >
        {/* 战术护角 */}
        <div className={`absolute -top-1 -left-1 w-2 h-2 border-t-2 border-l-2 transition-colors ${isOpen ? 'border-cyan-400' : 'border-transparent group-hover:border-cyan-600'}`} />
        <div className={`absolute -bottom-1 -right-1 w-2 h-2 border-b-2 border-r-2 transition-colors ${isOpen ? 'border-cyan-400' : 'border-transparent group-hover:border-cyan-600'}`} />

        <span className={`tracking-widest transition-all ${
          value ? 'text-cyan-300 font-bold drop-shadow-[0_0_5px_rgba(34,211,238,0.5)]' : 'text-slate-500'
        }`}>
          {selectedLabel}
        </span>
        
        <div className="flex items-center gap-2">
          <div className={`w-1 h-1 rounded-full ${isOpen ? 'bg-cyan-400 animate-pulse' : 'bg-slate-600'}`} />
          <svg
            className={`w-3.5 h-3.5 transition-transform duration-300 ${isOpen ? 'rotate-180 text-cyan-400' : 'text-slate-500 group-hover:text-cyan-600'}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      {/* 展开列表 */}
      {isOpen && !disabled && (
        <div className="absolute z-50 w-[calc(100%+8px)] -left-[4px] mt-2 bg-[#060b14] border-2 border-cyan-500/50 shadow-[0_15px_50px_rgba(0,0,0,0.9)] overflow-hidden animate-in fade-in zoom-in-95 duration-200">
          <ul className="max-h-64 overflow-y-auto custom-scrollbar p-1">
            {options.map((option) => {
              const isSelected = option.value === value;
              return (
                <li
                  key={option.value}
                  onClick={() => { onChange(option.value); setIsOpen(false); }}
                  className={`px-3 py-2.5 my-1 cursor-pointer transition-all duration-150 flex items-center justify-between ${
                    isSelected ? 'bg-cyan-900/40 text-cyan-200 border-r-4 border-cyan-400' : 'text-slate-400 hover:bg-slate-800 hover:text-cyan-100'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <div className={`w-1 h-3 ${isSelected ? 'bg-cyan-400' : 'bg-slate-700'}`} />
                    {option.label}
                  </span>
                  {isSelected && <span className="text-[8px] text-cyan-500 font-bold">ACTIVE</span>}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
};

// ─── 2. 战术开关 (Tactical Toggle) ──────────────────────────────────────────
interface ToggleProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
}
export const TacticalToggle: React.FC<ToggleProps> = ({ label, checked, ...props }) => (
  <label className="flex items-center cursor-pointer group active:scale-[0.98] transition-all p-1 mb-1 hover:bg-slate-800/30 border border-transparent hover:border-slate-800">
    <div className="relative flex items-center">
      <input type="checkbox" className="sr-only" checked={checked} {...props} />
      <div className={`w-4 h-4 border-2 transition-all flex items-center justify-center ${
        checked ? 'border-cyan-500 bg-cyan-950 shadow-[0_0_10px_rgba(6,182,212,0.4)]' : 'border-slate-600 bg-slate-950'
      }`}>
        {checked && <div className="w-2 h-2 bg-cyan-400 shadow-[0_0_5px_#22d3ee]" />}
      </div>
    </div>
    <span className={`ml-3 text-[10px] font-mono tracking-widest uppercase transition-colors ${
      checked ? 'text-cyan-300' : 'text-slate-500 group-hover:text-slate-400'
    }`}>
      {label}
    </span>
  </label>
);

// ─── 3. 赛博滑块 (Cyber Slider) ──────────────────────────────────────────────
export const CyberSlider: React.FC<InputHTMLAttributes<HTMLInputElement>> = (props) => (
  <div className="py-2">
    <input
      type="range"
      {...props}
      className={`cyber-slider w-full appearance-none bg-transparent cursor-pointer ${props.className ?? ''}`}
    />
  </div>
);