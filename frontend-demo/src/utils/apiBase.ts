/**
 * 与 api_bridge 同源：用当前页面 hostname 访问 8000 端口，
 * 避免用 127.0.0.1 / 局域网 IP 打开前端时仍连 ws://localhost:8000 导致连错机器、思维树无数据。
 */
const DEFAULT_PORT = '8000';

export function getHttpApiBase(): string {
  const fromEnv = import.meta.env.VITE_API_BASE as string | undefined;
  if (fromEnv?.trim()) {
    return fromEnv.replace(/\/$/, '');
  }
  if (typeof window === 'undefined') {
    return `http://127.0.0.1:${DEFAULT_PORT}`;
  }
  const host = import.meta.env.VITE_API_HOST as string | undefined;
  const port = (import.meta.env.VITE_API_PORT as string | undefined) ?? DEFAULT_PORT;
  const h = host?.trim() || window.location.hostname;
  const proto = window.location.protocol === 'https:' ? 'https:' : 'http:';
  return `${proto}//${h}:${port}`;
}

export function getWsMissionUrl(): string {
  const fromEnv = import.meta.env.VITE_WS_MISSION as string | undefined;
  if (fromEnv?.trim()) return fromEnv.trim();
  if (typeof window === 'undefined') {
    return `ws://127.0.0.1:${DEFAULT_PORT}/ws/mission`;
  }
  const base = getHttpApiBase();
  try {
    const u = new URL(base);
    const wsProto = u.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${wsProto}//${u.host}/ws/mission`;
  } catch {
    return `ws://${window.location.hostname}:${DEFAULT_PORT}/ws/mission`;
  }
}

export function getDefaultImageUrl(): string {
  return `${getHttpApiBase()}/data/100000007.png`;
}
