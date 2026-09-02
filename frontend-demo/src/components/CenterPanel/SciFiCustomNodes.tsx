import { Handle, Position } from 'reactflow';

type NodeData = { label: string; status: string };

export const SciFiRouter = ({ data }: { data: NodeData }) => {
  const isSuccess = data.status === 'SUCCESS';

  return (
    <div
      className={`relative w-16 h-16 flex items-center justify-center border-2 backdrop-blur-md transition-all duration-300 transform rotate-45 ${
        isSuccess ? 'border-emerald-500 bg-emerald-950/40' : 'border-slate-600 bg-slate-800/50'
      }`}
    >
      <div className="transform -rotate-45 text-center flex flex-col items-center justify-center w-full h-full">
        <span
          className={`font-mono text-[8px] font-bold uppercase leading-tight px-1 ${
            isSuccess ? 'text-emerald-400' : 'text-slate-500'
          }`}
        >
          {data.label}
        </span>
      </div>

      <Handle type="target" position={Position.Top} id="top" className="!w-2 !h-2 !bg-transparent !border-none !-mt-1" />
      <Handle type="source" position={Position.Right} id="right" className="!w-2 !h-2 !bg-transparent !border-none !-mr-1" />
      <Handle type="source" position={Position.Bottom} id="bottom" className="!w-2 !h-2 !bg-transparent !border-none !-mb-1" />
      <Handle type="target" position={Position.Left} id="left" className="!w-2 !h-2 !bg-transparent !border-none !-ml-1" />
    </div>
  );
};

export const SciFiWarning = ({ data }: { data: NodeData }) => (
  <div className="relative px-3 py-2 min-w-[140px] rounded-sm border-2 border-slate-700 opacity-60">
    <div className="absolute inset-0 bg-[repeating-linear-gradient(45deg,#000,#000_8px,#ef4444_8px,#ef4444_16px)] opacity-15" />
    <div className="relative z-10 flex items-center justify-center gap-2 bg-black/80 px-2 py-1">
      <div className="w-1.5 h-1.5 rounded-full bg-slate-600" />
      <span className="font-mono text-[9px] font-bold tracking-widest text-slate-500">
        {data.label}
      </span>
    </div>

    <Handle type="target" position={Position.Left} className="!w-2 !h-4 !bg-transparent !border-none !-ml-1" />
    <Handle type="source" position={Position.Right} className="!w-2 !h-4 !bg-transparent !border-none !-mr-1" />
  </div>
);
