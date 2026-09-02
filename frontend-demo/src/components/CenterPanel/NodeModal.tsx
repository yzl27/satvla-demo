import type { ReactNode } from 'react';
import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';

interface NodeModalProps {
  title: string;
  children: ReactNode;
  onClose: () => void;
  /** 加宽以容纳 JSON（仅 Node Workflow Chain 使用） */
  maxWidthClassName?: string;
}

export const NodeModal = ({
  title,
  children,
  onClose,
  maxWidthClassName = 'max-w-lg',
}: NodeModalProps) => {
  // 用于控制组件挂载后的动画状态
  const [isRendered, setIsRendered] = useState(false);

  useEffect(() => {
    // 组件挂载后，稍微延迟触发动画，确保 CSS 过渡生效
    const timer = setTimeout(() => setIsRendered(true), 10);
    return () => clearTimeout(timer); // 清理定时器
  }, []);

  // 处理关闭动画
  const handleClose = () => {
    setIsRendered(false); // 触发退场动画
    // 等待动画结束后再调用 onClose 销毁组件 (假设退场动画 300ms)
    setTimeout(onClose, 300);
  };

  // 挂到 document.body，避免被 Node Workflow Chain 的 overflow-hidden / backdrop-blur 裁切
  return createPortal(
    <div
      // ⚡ 遮罩层动效：淡入 + 毛玻璃渐变
      className={`fixed inset-0 z-[100] flex items-center justify-center transition-all duration-300 ease-out 
        ${isRendered ? 'bg-black/70 backdrop-blur-sm' : 'bg-black/0 backdrop-blur-0'}`}
      onClick={handleClose} // 点击遮罩层调用带动画的关闭
      role="presentation"
    >
      <div
        // ⚡ 弹窗主体核心动效：全息投影生成 (Holographic Spawn)
        // 组合动效：从 90% 放大到 100% + Y轴微调 + 垂直方向极度压缩进入 + 透明度
        // 配合 transition-all 打造丝滑效果
        className={`relative w-full ${maxWidthClassName} max-h-[80vh] flex flex-col rounded-lg bg-[#080d19]/90 backdrop-blur-xl border border-slate-800 border-t-2 border-t-cyan-800/80 shadow-[0_20px_50px_-5px_rgba(0,0,0,0.9),inset_0_0_20px_rgba(6,182,212,0.05)] overflow-hidden group 
          transition-all duration-300 ease-[cubic-bezier(0.34,1.56,0.64,1)]
          ${isRendered 
            ? 'opacity-100 translate-y-0 scale-100' 
            : 'opacity-0 translate-y-4 scale-90'}`}
        onClick={(e) => e.stopPropagation()} // 阻止冒泡
        role="dialog"
        aria-modal="true"
      >
        {/* 🌟 顶部的高光边缘 (保持原有静态样式) */}
        <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent"></div>

        {/* 📺 高级动效：全息扫描强光 (加载时闪烁一次) */}
        <div className={`absolute inset-0 pointer-events-none z-50 bg-cyan-400/10 
          transition-opacity duration-500 delay-150 ease-out
          ${isRendered ? 'opacity-0' : 'opacity-100'}`}>
        </div>

        {/* 标题栏区域：自带向下的微弱渐变 */}
        <div className="shrink-0 flex items-center justify-between border-b border-slate-800/60 px-4 py-3.5 bg-gradient-to-b from-slate-800/30 to-transparent relative z-20">
          <div className="flex items-center gap-2.5 min-w-0">
            {/* 战术发光指示灯 (保持原有 animate-pulse) */}
            <div className="w-2 h-2 rounded-full bg-cyan-500 shadow-[0_0_10px_#06b6d4] animate-pulse shrink-0"></div>
            <h3 className="text-base font-mono font-bold text-cyan-300 tracking-[0.14em] uppercase antialiased leading-snug drop-shadow-[0_0_10px_rgba(34,211,238,0.45)]">
              {title}
            </h3>
          </div>
          <button
            type="button"
            onClick={handleClose} // 调用带动画的关闭
            className="text-slate-500 hover:text-cyan-400 hover:bg-slate-800/50 rounded transition-all p-1"
            aria-label="Close"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* 内容区：加入与左侧栏一致的科技蓝图网格背景，并保持原有的滚动逻辑 */}
        <div className="flex-1 min-h-0 p-4 overflow-y-auto custom-scrollbar bg-[linear-gradient(rgba(6,182,212,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(6,182,212,0.03)_1px,transparent_1px)] bg-[size:16px_16px] relative z-10">
          {children}
        </div>
      </div>
    </div>,
    document.body
  );
};