/**
 * 与 ImageViewer 胶片条、multiagent 工具输出文件名规则一致。
 * 从 workspace 相对路径或完整路径推导标签。
 */

export interface FilmLabelInfo {
  label: string;
  stageTag: string;
}

/** 胶片条阶段标签颜色（与 ImageViewer STAGE_COLOR 对齐，并扩展 S4/S5） */
export const STAGE_COLOR: Record<string, string> = {
  S0: 'text-slate-400',
  S1: 'text-cyan-400',
  S2: 'text-amber-400',
  S3: 'text-violet-400',
  S4: 'text-sky-400',
  S5: 'text-fuchsia-400',
};

/**
 * 从图片路径推导胶片标签（与 useWorkflowStore 原逻辑一致）。
 */
export function deriveImageInfo(path: string): FilmLabelInfo {
  const name = (path.split('/').pop() ?? '').toLowerCase();
  const stem = name.replace(/\.(png|jpg|jpeg)$/i, '');

  if (/_crop\d+/.test(stem)) {
    if (/_bina\d+$|_binaotsu$/i.test(stem)) {
      return { label: 'BINARIZED', stageTag: 'S3' };
    }
    if (/_grey$/i.test(stem)) {
      return { label: 'GREYSCALE', stageTag: 'S3' };
    }
    if (/_crop\d+_sr$/i.test(stem) || /_sr$/i.test(stem)) {
      return { label: 'SUPER-RES', stageTag: 'S3' };
    }
    const m = name.match(/_crop(\d+)\./);
    if (m) {
      return { label: `ROI-${m[1]}`, stageTag: 'S2' };
    }
  }

  if (name.includes('_detected')) return { label: 'DETECTED', stageTag: 'S1' };
  if (name.includes('_dehazed')) return { label: 'DEHAZED', stageTag: 'S1' };
  if (name.includes('_deblur')) return { label: 'DEBLURRED', stageTag: 'S1' };
  if (name.includes('_denoise')) return { label: 'DENOISED', stageTag: 'S1' };
  if (name.includes('_derain')) return { label: 'DERAINED', stageTag: 'S1' };
  return { label: 'SRC', stageTag: 'S0' };
}

/** 从节点 payload 取展示用标签（优先后端 film_label） */
export function filmLabelForNode(
  imagePath: string | null | undefined,
  filmLabel: string | null | undefined,
  stageTag: string | null | undefined,
): FilmLabelInfo {
  if (filmLabel?.trim() && stageTag?.trim()) {
    return { label: filmLabel.trim(), stageTag: stageTag.trim() };
  }
  if (imagePath?.trim()) {
    return deriveImageInfo(imagePath);
  }
  return { label: '—', stageTag: 'S0' };
}

/** 与主画面 mainImageSrc 比较用：抽出 /workspace/ 后相对路径 */
export function workspaceRelFromHttpUrl(url: string): string | null {
  const m = url.match(/\/workspace\/([^?#]+)/);
  return m ? decodeURIComponent(m[1].replace(/^\//, '')) : null;
}
