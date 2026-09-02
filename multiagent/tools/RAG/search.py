"""
tools/RAG/search.py
────────────────────────────────────────────────────────────────
通过 Tavily Search API 执行即时网络检索，返回摘要文本。

Tavily API 文档：https://docs.tavily.com/docs/rest-api/api-reference

配置方式（优先级从高到低）：
  1. 环境变量  TAVILY_API_KEY
  2. 本文件底部 TAVILY_API_KEY 常量（填入后提交时注意安全）
────────────────────────────────────────────────────────────────
"""

import os
import logging
import requests

logger = logging.getLogger(__name__)

# ── API 配置 ──────────────────────────────────
# 通过环境变量 TAVILY_API_KEY 配置；未配置时返回占位结果（不占用配额）
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "YOUR_TAVILY_API_KEY_HERE")
TAVILY_API_URL = "https://api.tavily.com/search"

# 搜索参数默认值
DEFAULT_SEARCH_DEPTH = "advanced"   # "basic" 更快，"advanced" 质量更高
DEFAULT_MAX_RESULTS  = 5            # 返回条目数
DEFAULT_SNIPPET_LEN  = 400          # 每条摘录的最大字符数


def run(keyword: str) -> dict:
    """
    参数：
      keyword — 搜索关键词字符串，由阶段四情报提炼官生成

    返回：
      {
        "status" : "success" | "error",
        "keyword": str,
        "result" : str,   # 拼接好的摘要文本，直接传给阶段五
        "message": str,   # 仅 error 时存在
      }
    """
    if not keyword or not keyword.strip():
        return _err("search 工具收到空关键词")

    if TAVILY_API_KEY == "YOUR_TAVILY_API_KEY_HERE":
        logger.warning("[search] TAVILY_API_KEY 未配置，返回占位结果。")
        return {
            "status" : "success",
            "keyword": keyword,
            "result" : f"(Tavily API Key 未配置，无法检索：{keyword})",
        }

    payload = {
        "api_key"             : TAVILY_API_KEY,
        "query"               : keyword,
        "search_depth"        : DEFAULT_SEARCH_DEPTH,
        "include_answer"      : True,    # 让 Tavily 返回 AI 综合摘要
        "include_raw_content" : False,   # 不需要原始 HTML，减少 token 消耗
        "max_results"         : DEFAULT_MAX_RESULTS,
        "include_domains"     : [],      # 不限制来源域名
        "exclude_domains"     : [],
    }

    try:
        resp = requests.post(TAVILY_API_URL, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        return _err("Tavily 搜索超时（>30s），请检查网络或稍后重试")
    except requests.exceptions.HTTPError as e:
        return _err(f"Tavily HTTP 错误: {e} | 响应: {resp.text[:200]}")
    except requests.exceptions.RequestException as e:
        return _err(f"Tavily 请求异常: {e}")

    # ── 拼接结果文本 ──────────────────────────
    # Tavily 响应结构：
    # {
    #   "answer" : "...",          ← AI 综合摘要（最有价值）
    #   "results": [               ← 各条原始搜索结果
    #     {"title": ..., "url": ..., "content": ..., "score": ...},
    #     ...
    #   ]
    # }
    parts   = []
    answer  = data.get("answer", "").strip()
    results = data.get("results", [])

    if answer:
        parts.append(f"【综合摘要】\n{answer}")

    for r in results[:3]:          # 取 Top-3 条目，避免 context 过长
        title   = r.get("title",   "无标题")
        content = r.get("content", "").strip()
        url     = r.get("url",     "")
        snippet = content[:DEFAULT_SNIPPET_LEN]
        if len(content) > DEFAULT_SNIPPET_LEN:
            snippet += "……"
        parts.append(f"【{title}】\n{snippet}\n来源: {url}")

    result_text = "\n\n".join(parts) if parts else "搜索返回空结果"
    logger.info(f"[search] 关键词='{keyword}'，获得 {len(results)} 条，"
                f"摘要长度 {len(result_text)} 字符")

    return {
        "status" : "success",
        "keyword": keyword,
        "result" : result_text,
    }


def _err(msg: str) -> dict:
    logger.error(f"[search] {msg}")
    return {"status": "error", "keyword": "", "result": "", "message": msg}