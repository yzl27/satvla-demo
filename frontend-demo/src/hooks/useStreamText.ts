import { useEffect, useState } from 'react';

type Options = {
  /** 开始流式输出前的等待（用于多段错开） */
  startDelayMs?: number;
  /** 每次追加的字符数 */
  charsPerTick?: number;
  /** 每次 tick 间隔 ms */
  tickMs?: number;
};

/**
 * 将 fullText 以流式方式递增展示；run 为 false 或 fullText 为空时清空。
 */
export function useStreamText(
  fullText: string,
  run: boolean,
  { startDelayMs = 0, charsPerTick = 3, tickMs = 16 }: Options = {},
): { display: string; streaming: boolean } {
  const [display, setDisplay] = useState('');
  const [streaming, setStreaming] = useState(false);

  useEffect(() => {
    if (!run || !fullText) {
      setDisplay('');
      setStreaming(false);
      return;
    }

    setDisplay('');
    setStreaming(true);

    let intervalId: ReturnType<typeof setInterval> | null = null;
    const startTimeout = setTimeout(() => {
      let n = 0;
      intervalId = setInterval(() => {
        n += charsPerTick;
        if (n >= fullText.length) {
          setDisplay(fullText);
          setStreaming(false);
          if (intervalId) clearInterval(intervalId);
        } else {
          setDisplay(fullText.slice(0, n));
        }
      }, tickMs);
    }, startDelayMs);

    return () => {
      clearTimeout(startTimeout);
      if (intervalId) clearInterval(intervalId);
    };
  }, [fullText, run, startDelayMs, charsPerTick, tickMs]);

  return { display, streaming };
}
