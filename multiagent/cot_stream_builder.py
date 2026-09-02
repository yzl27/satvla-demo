"""
CoT 思维树：扁平 nodes + edges。
阶段 1/2/3 仅在「已有图像路径」时创建节点（VLM/工具先写入 buffer，首帧图再落盘），
避免出现「等待工具产出图像」的无图节点；阶段 4/5 仍各保留无图节点。
"""

from __future__ import annotations

import ast
import json
import re
from typing import Any, Optional


COT_PREFIX = "__COT_UPDATE__::"


def _rel_workspace_path(abs_or_rel: str) -> str:
    s = abs_or_rel.strip()
    if "/workspace/" in s:
        return s.split("/workspace/", 1)[1]
    if s.startswith("workspace/"):
        return s[len("workspace/") :]
    return s


PHASE_NAMES = ("输入", "阶段一", "阶段二", "阶段三", "阶段四", "阶段五")


def _thumb_for_new_image(line: str, rel: str) -> str:
    r = rel.lower()
    if "_detected" in r:
        return "目标检测 · 可视化"
    if "crop" in r and "_crop" in r:
        return "裁剪 ROI · 输出"
    if "超分" in line or "Real-ESRGAN" in line or "super_resolution" in r or "_sr" in r:
        return "超分辨率 · 输出"
    if "二值化" in line or "bina" in r:
        return "二值化 · 输出"
    if "灰度" in line or "_grey" in r:
        return "灰度化 · 输出"
    if "复原" in line or "新图" in line:
        m = re.search(r"复原:\s*(\w+)", line)
        if m:
            return f"复原({m.group(1)}) · 输出"
        return "复原/增强 · 输出"
    return "工具输出"


def derive_film_label(rel: str) -> tuple[str, str]:
    """与 frontend `deriveImageInfo` 一致：胶片标签 + S0–S5。"""
    name = rel.split("/")[-1].lower()
    stem = re.sub(r"\.(png|jpg|jpeg)$", "", name, flags=re.I)
    if re.search(r"_crop\d+", stem):
        if re.search(r"_bina\d+$|_binaotsu$", stem, re.I):
            return ("BINARIZED", "S3")
        if re.search(r"_grey$", stem, re.I):
            return ("GREYSCALE", "S3")
        if re.search(r"_crop\d+_sr$", stem, re.I) or re.search(r"_sr$", stem, re.I):
            return ("SUPER-RES", "S3")
        m = re.search(r"_crop(\d+)\.", name)
        if m:
            return (f"ROI-{m.group(1)}", "S2")
    if "_detected" in name:
        return ("DETECTED", "S1")
    if "_dehazed" in name:
        return ("DEHAZED", "S1")
    if "_deblur" in name:
        return ("DEBLURRED", "S1")
    if "_denoise" in name:
        return ("DENOISED", "S1")
    if "_derain" in name:
        return ("DERAINED", "S1")
    return ("SRC", "S0")


class CoTStreamBuilder:
    def __init__(self) -> None:
        self.revision = 0
        self._nodes: dict[str, dict[str, Any]] = {}
        self._edges: list[dict[str, str]] = []
        self._edge_ids: set[str] = set()
        self._seq = 0

        self._tail: Optional[str] = None
        self._task_id: Optional[str] = None

        # 阶段 1/2/3：VLM 先进入 buffer，首帧图出现后再 _flush_buffer_to_node
        self._vlm_buffer: Optional[dict[str, Any]] = None
        self._pending_vlm_id: Optional[str] = None

        self._current_target: Optional[str] = None
        self._target_tails: dict[str, str] = {}
        self._after_queue_id: Optional[str] = None
        # 检测可视化节点 id：阶段二队列确定后从此节点扇出 ROI1/2/3 分支
        self._detected_node_id: Optional[str] = None
        # 每个 target_id → 该分支首节点（队列行预创建，裁剪/🎯 时更新）
        self._roi_branch_heads: dict[str, str] = {}
        self._pending_crop_target: Optional[str] = None

        # 最近一次成功产出的图（用于检测结束等无新图日志时仍能 flush buffer）
        self._last_image_rel: Optional[str] = None
        self._last_local_by_target: dict[str, str] = {}

    def reset(self) -> None:
        self.__init__()

    def _nid(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}_{self._seq}"

    def _add_step(
        self,
        nid: str,
        *,
        phase: int,
        phase_label: str,
        action_label: str,
        label: str,
        subtitle: Optional[str] = None,
        thought: Optional[str] = None,
        image_path: Optional[str] = None,
        hide_thumbnail: bool = False,
        details: Optional[dict[str, Any]] = None,
        thumb_source: Optional[str] = None,
        status: str = "running",
    ) -> None:
        self._nodes[nid] = {
            "id": nid,
            "kind": "step",
            "phase": phase,
            "phase_label": phase_label,
            "action_label": action_label,
            "label": label,
            "subtitle": subtitle,
            "thought": thought,
            "image_path": image_path,
            "hide_thumbnail": hide_thumbnail,
            "thumb_source": thumb_source,
            "details": details if details is not None else {},
            "status": status,
        }
        self._apply_film_meta(nid)

    def _apply_film_meta(self, nid: str) -> None:
        """film_label / stage_tag：与 ImageViewer 胶片条一致；阶段 4/5 收束节点为 RAG / SOAP。"""
        n = self._nodes.get(nid)
        if not n:
            return
        ph = int(n.get("phase") or 0)
        if n.get("hide_thumbnail") and ph >= 4:
            n["film_label"] = "RAG" if ph == 4 else "SOAP" if ph == 5 else None
            n["stage_tag"] = f"S{ph}"
            return
        rel = n.get("image_path")
        if rel:
            fl, st = derive_film_label(rel)
            n["film_label"] = fl
            n["stage_tag"] = st

    def _ensure_edge(self, src: str, tgt: str) -> None:
        if not src or not tgt or src == tgt:
            return
        eid = f"e_{src}_{tgt}"
        if eid in self._edge_ids:
            return
        self._edge_ids.add(eid)
        self._edges.append({"id": eid, "source": src, "target": tgt})

    def _link(self, src: Optional[str], tgt: str) -> None:
        if src:
            self._ensure_edge(src, tgt)
        self._tail = tgt

    def _discard_buffer(self) -> None:
        self._vlm_buffer = None

    def _start_vlm_buffer(
        self,
        phase: int,
        action_label: str,
        label: str,
        subtitle: Optional[str] = None,
        link_from: Optional[str] = None,
    ) -> None:
        self._discard_buffer()
        self._pending_vlm_id = None
        self._vlm_buffer = {
            "phase": phase,
            "action_label": action_label,
            "label": label,
            "subtitle": subtitle or "",
            "thought": "",
            "details": {},
            "link_from": link_from if link_from is not None else self._tail,
        }

    def _buffer_append_action(self, line: str, summary: str) -> None:
        if not self._vlm_buffer:
            return
        self._vlm_buffer.setdefault("details", {}).setdefault("actions", []).append(
            {"summary": summary, "log": line[:500]}
        )

    def _flush_buffer_to_node(
        self,
        image_path: str,
        thumb_source: str,
        merge_line: str,
        merge_summary: str,
    ) -> Optional[str]:
        """用 buffer + 首帧图创建节点；返回新节点 id。"""
        b = self._vlm_buffer
        if not b:
            return None
        phase = int(b["phase"])
        pl = PHASE_NAMES[phase] if 0 <= phase < len(PHASE_NAMES) else f"阶段{phase}"
        nid = self._nid("step")
        details = dict(b.get("details") or {})
        details.setdefault("actions", []).append({"summary": merge_summary, "log": merge_line[:500]})
        self._add_step(
            nid,
            phase=phase,
            phase_label=pl,
            action_label=b["action_label"],
            label=b["label"],
            subtitle=b.get("subtitle") or None,
            thought=b.get("thought") or "",
            image_path=image_path,
            hide_thumbnail=False,
            thumb_source=thumb_source,
            details=details,
        )
        src = b.get("link_from")
        self._link(src, nid)
        self._last_image_rel = image_path
        self._vlm_buffer = None
        self._pending_vlm_id = nid
        if phase == 3 and self._current_target:
            self._last_local_by_target[self._current_target] = image_path
        return nid

    def _merge_into_pending(
        self,
        line: str,
        summary: str,
        image_path: Optional[str] = None,
        thumb_source: Optional[str] = None,
    ) -> None:
        # 先处理「首帧图」：buffer → 节点
        if image_path and self._vlm_buffer:
            self._flush_buffer_to_node(
                image_path,
                thumb_source or summary,
                line,
                summary,
            )
            return

        if image_path:
            self._last_image_rel = image_path
            if self._current_target:
                self._last_local_by_target[self._current_target] = image_path

        pid = self._pending_vlm_id
        if pid and pid in self._nodes:
            n = self._nodes[pid]
            d = n.setdefault("details", {})
            d.setdefault("actions", []).append({"summary": summary, "log": line[:500]})
            if image_path:
                n["image_path"] = image_path
                n["thumb_source"] = thumb_source or summary
                self._apply_film_meta(pid)
            if summary and not n.get("subtitle"):
                n["subtitle"] = summary[:80]
            return

        if self._vlm_buffer and not image_path:
            self._buffer_append_action(line, summary)

    def feed_line(self, line: str) -> dict[str, Any]:
        if line.startswith(COT_PREFIX):
            self._merge_json_payload(line[len(COT_PREFIX) :].strip())
        else:
            self._parse_log_line(line)
        self.revision += 1
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        return {
            "revision": self.revision,
            "task_id": self._task_id,
            "nodes": list(self._nodes.values()),
            "edges": list(self._edges),
        }

    def _merge_json_payload(self, raw: str) -> None:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return
        for n in data.get("nodes") or []:
            nid = n.get("id")
            if not nid:
                continue
            if nid in self._nodes:
                self._nodes[nid].update({k: v for k, v in n.items() if v is not None})
            else:
                self._nodes[nid] = n
        for e in data.get("edges") or []:
            s, t = e.get("source"), e.get("target")
            if s and t:
                self._ensure_edge(s, t)

    def _new_step(
        self,
        phase: int,
        action_label: str,
        label: str,
        subtitle: Optional[str] = None,
        thought: Optional[str] = None,
        image_path: Optional[str] = None,
        hide_thumbnail: bool = False,
        thumb_source: Optional[str] = None,
        link_from: Optional[str] = None,
        *,
        link: bool = True,
    ) -> str:
        pl = PHASE_NAMES[phase] if 0 <= phase < len(PHASE_NAMES) else f"阶段{phase}"
        nid = self._nid("step")
        self._add_step(
            nid,
            phase=phase,
            phase_label=pl,
            action_label=action_label,
            label=label,
            subtitle=subtitle,
            thought=thought or "",
            image_path=image_path,
            hide_thumbnail=hide_thumbnail,
            thumb_source=thumb_source,
            details={},
        )
        if link:
            src = link_from if link_from is not None else self._tail
            self._link(src, nid)
        if image_path:
            self._last_image_rel = image_path
        return nid

    def _parse_log_line(self, line: str) -> None:
        m_ts = re.search(r"时间戳图:\s*(\S+\.(?:png|jpg|jpeg|bmp))", line, re.I)
        if m_ts:
            rel = _rel_workspace_path(m_ts.group(1))
            self._discard_buffer()
            self._pending_vlm_id = None
            nid = self._new_step(
                0,
                "输入",
                "输入图像",
                subtitle="任务工作区中的待分析图",
                image_path=rel,
                thumb_source="输入图像（任务拷贝）",
                link_from=self._tail,
            )
            self._tail = nid
            self._last_image_rel = rel
            if self._task_id:
                self._nodes[nid]["subtitle"] = f"{self._task_id} · 输入"
            return

        m = re.search(r"🚀\s*启动任务:\s*(task_\d{8}_\d{6})", line)
        if m:
            self._task_id = m.group(1)
            # 不再创建“任务启动”无图节点，避免污染阶段 0 展示；
            # 输入 SRC 由“时间戳图”行或前端预置节点承载。
            if self._tail is not None and self._nodes.get(self._tail, {}).get("phase") == 0:
                self._nodes[self._tail]["subtitle"] = f"{self._task_id} · 输入"
            return

        if "🟢" in line and "阶段一" in line:
            self._discard_buffer()
            self._pending_vlm_id = None
            return

        if "🤖" in line and "[VLM·阶段一]" in line and "正在观察" in line:
            self._start_vlm_buffer(
                1,
                "全局观察与决策",
                "阶段一 · 整图推理",
                "VLM 观察与工具选择",
            )
            return

        if self._vlm_buffer and self._vlm_buffer.get("phase") == 1:
            if "🖼️" in line and "[VLM·描述]" in line:
                cap = re.sub(r"^.*\[VLM·描述\]\s*", "", line).strip()
                self._vlm_buffer.setdefault("details", {})["image_caption"] = cap
                self._vlm_buffer["subtitle"] = (cap[:48] + "…") if len(cap) > 48 else cap
                return
            if "💭" in line and "[VLM·思考]" in line:
                self._vlm_buffer["thought"] = re.sub(r"^.*\[VLM·思考\]\s*", "", line).strip()
                return
            if "🛠️" in line and "[VLM·决策]" in line:
                self._vlm_buffer.setdefault("details", {})["decision"] = line.strip()
                return

        if self._pending_vlm_id and self._pending_vlm_id in self._nodes:
            n = self._nodes[self._pending_vlm_id]
            if n.get("phase") == 1:
                if "🖼️" in line and "[VLM·描述]" in line:
                    cap = re.sub(r"^.*\[VLM·描述\]\s*", "", line).strip()
                    n.setdefault("details", {})["image_caption"] = cap
                    n["subtitle"] = (cap[:48] + "…") if len(cap) > 48 else cap
                    return
                if "💭" in line and "[VLM·思考]" in line:
                    n["thought"] = re.sub(r"^.*\[VLM·思考\]\s*", "", line).strip()
                    return
                if "🛠️" in line and "[VLM·决策]" in line:
                    n.setdefault("details", {})["decision"] = line.strip()
                    return

        if "⚙️" in line and "[工具]" in line and (
            "超分辨率" in line or "二值化" in line or "灰度化" in line
        ):
            tname = "local"
            if "超分辨率" in line:
                tname = "super_resolution"
            elif "二值化" in line:
                tname = "binarize"
            elif "灰度化" in line:
                tname = "grey"
            self._merge_into_pending(line, f"工具: {tname}")
            return

        if "⚙️" in line and "[工具]" in line and "阶段" not in line:
            if "执行图像复原" in line or "GroundingDINO" in line or "检测" in line:
                if "GroundingDINO" in line or ("检测" in line and "执行" in line):
                    self._merge_into_pending(line, "调用检测")
                elif "复原" in line:
                    m2 = re.search(r"复原:\s*(\w+)", line)
                    self._merge_into_pending(line, f"复原: {m2.group(1) if m2 else 'restore'}")
                return

        if "✅" in line and "[工具]" in line and ("检测完成" in line or "强制检测完成" in line):
            mct = re.search(r"共发现\s*(\d+)\s*个目标", line)
            extra = f"检测完成 · {mct.group(1)} 个目标" if mct else "检测完成"

            # 优先使用日志里的新图路径；若未出现，按当前全局图推导 *_detected 兜底，
            # 确保思维链出现 DETECTED 节点，与 ImageViewer 一致。
            detected_rel: Optional[str] = None
            m_det = re.search(r"新图:\s*(\S+\.(?:png|jpg|jpeg))", line, re.I)
            if m_det:
                detected_rel = _rel_workspace_path(m_det.group(1))
            elif self._last_image_rel:
                if "_detected" in self._last_image_rel.lower():
                    detected_rel = self._last_image_rel
                else:
                    detected_rel = re.sub(r"(\.\w+)$", r"_detected\1", self._last_image_rel, flags=re.I)

            flushed_id: Optional[str] = None
            if self._vlm_buffer and self._vlm_buffer.get("phase") == 1 and detected_rel:
                flushed_id = self._flush_buffer_to_node(
                    detected_rel,
                    "目标检测 · 可视化",
                    line,
                    extra,
                )
            else:
                self._merge_into_pending(line, extra)
            self._pending_vlm_id = None
            self._discard_buffer()
            if flushed_id:
                self._detected_node_id = flushed_id
            return

        m_img = re.search(r"✅\s*\[工具\].*新图:\s*(\S+\.(?:png|jpg|jpeg))", line, re.I)
        if m_img:
            rel = _rel_workspace_path(m_img.group(1))
            self._merge_into_pending(
                line,
                "生成中间图",
                image_path=rel,
                thumb_source=_thumb_for_new_image(line, rel),
            )
            return

        if "🟡" in line and "阶段二" in line:
            self._discard_buffer()
            self._pending_vlm_id = None
            return

        if "🤖" in line and "[VLM·阶段二]" in line:
            self._start_vlm_buffer(
                2,
                "目标排序",
                "阶段二 · 候选目标排序",
                "VLM 优先级与裁剪",
            )
            return

        if self._vlm_buffer and self._vlm_buffer.get("phase") == 2:
            if "🖼️" in line and "[VLM·描述]" in line:
                cap = re.sub(r"^.*\[VLM·描述\]\s*", "", line).strip()
                self._vlm_buffer.setdefault("details", {})["image_caption"] = cap
                return
            if "💭" in line and "[VLM·思考]" in line:
                self._vlm_buffer["thought"] = re.sub(r"^.*\[VLM·思考\]\s*", "", line).strip()
                return

        if self._pending_vlm_id and self._pending_vlm_id in self._nodes:
            n = self._nodes[self._pending_vlm_id]
            if n.get("phase") == 2:
                if "💭" in line and "[VLM·思考]" in line:
                    n["thought"] = re.sub(r"^.*\[VLM·思考\]\s*", "", line).strip()
                    return

        if "✅" in line and "阶段二" in line and "优先级队列" in line:
            self._merge_into_pending(line, "确定优先级队列")
            self._after_queue_id = self._pending_vlm_id
            self._pending_vlm_id = None
            self._discard_buffer()
            top_queue: list[Any] = []
            mq = re.search(r":\s*(\[[^\]]*\])", line)
            if mq:
                try:
                    top_queue = ast.literal_eval(mq.group(1))
                except (SyntaxError, ValueError):
                    top_queue = []
            # 从检测节点扇出 ROI1/2/3… 分支首节点（先共用检测图，裁剪成功后更新为 crop）
            if self._detected_node_id and top_queue:
                det = self._nodes.get(self._detected_node_id)
                det_img = det.get("image_path") if det else None
                if det_img:
                    self._roi_branch_heads.clear()
                    for i, tid in enumerate(top_queue):
                        if not isinstance(tid, str):
                            tid = str(tid)
                        nid = self._nid("step")
                        self._add_step(
                            nid,
                            phase=2,
                            phase_label=PHASE_NAMES[2],
                            action_label="ROI 分支",
                            label=f"ROI-{i + 1}",
                            subtitle=f"目标 {tid}",
                            thought="",
                            image_path=det_img,
                            hide_thumbnail=False,
                            thumb_source="与检测图同源（裁剪后更新）",
                            details={"target_id": tid, "queue_index": i, "branch": "roi_head"},
                        )
                        self._nodes[nid]["film_label"] = f"ROI-{i + 1}"
                        self._nodes[nid]["stage_tag"] = "S2"
                        self._ensure_edge(self._detected_node_id, nid)
                        self._roi_branch_heads[tid] = nid
                        self._target_tails[tid] = nid
            return

        if "✂️" in line and "裁剪" in line:
            mctid = re.search(r"裁剪\s+crop\d+:\s*(\S+)\s+BBox", line)
            if mctid:
                self._pending_crop_target = mctid.group(1).strip()
            self._merge_into_pending(line, "裁剪 ROI")
            return

        if "✅" in line and "裁剪成功" in line:
            m2 = re.search(r"裁剪成功\s*→\s*(\S+)", line)
            rel = _rel_workspace_path(m2.group(1)) if m2 else None
            tid = self._pending_crop_target
            if rel and tid and tid in self._roi_branch_heads:
                hid = self._roi_branch_heads[tid]
                if hid in self._nodes:
                    hn = self._nodes[hid]
                    hn["image_path"] = rel
                    hn["subtitle"] = "裁剪 ROI 入口"
                    hn["thumb_source"] = "裁剪 ROI · 输出"
                    self._apply_film_meta(hid)
                    hn.setdefault("details", {})["actions"] = hn.get("details", {}).get("actions", [])
                    if not any(
                        isinstance(a, dict) and a.get("summary") == "裁剪结果" for a in hn["details"]["actions"]
                    ):
                        hn["details"]["actions"].append({"summary": "裁剪结果", "log": line[:500]})
                    self._target_tails[tid] = hid
                    self._last_local_by_target[tid] = rel
                    self._last_image_rel = rel
                    self._pending_vlm_id = hid
            else:
                self._merge_into_pending(
                    line,
                    "裁剪结果",
                    image_path=rel,
                    thumb_source="裁剪 ROI · 输出",
                )
                if self._pending_vlm_id:
                    self._after_queue_id = self._pending_vlm_id
            self._pending_crop_target = None
            return

        if "🟠" in line and "阶段三" in line:
            self._discard_buffer()
            self._pending_vlm_id = None
            return

        m_t = re.search(r"🎯\s*开始处理目标:\s*(\S+)\s*\|\s*图:\s*(\S+)", line)
        if m_t:
            tid = m_t.group(1)
            self._current_target = tid
            rel = _rel_workspace_path(m_t.group(2))
            self._discard_buffer()
            self._pending_vlm_id = None
            head = self._roi_branch_heads.get(tid)
            if head and head in self._nodes:
                hn = self._nodes[head]
                hn["image_path"] = rel
                hn["subtitle"] = "裁剪 ROI 入口"
                hn["thumb_source"] = "裁剪 ROI · 入口图"
                self._apply_film_meta(head)
                self._target_tails[tid] = head
                self._last_local_by_target[tid] = rel
                self._last_image_rel = rel
                return
            anchor = self._detected_node_id or self._after_queue_id or self._tail
            nid = self._new_step(
                3,
                f"目标 {tid}",
                f"局部分析 · {tid}",
                subtitle="裁剪 ROI 入口",
                image_path=rel,
                thumb_source="裁剪 ROI · 入口图",
                link_from=anchor,
            )
            self._roi_branch_heads[tid] = nid
            self._target_tails[tid] = nid
            self._last_local_by_target[tid] = rel
            self._last_image_rel = rel
            return

        m_v3 = re.search(
            r"🤖\s*\[VLM·阶段三\]\s*分析\s*(\S+)\s*，\s*第\s*(\d+)\s*次",
            line,
        )
        if m_v3:
            tid = m_v3.group(1)
            self._current_target = tid
            parent = self._target_tails.get(tid) or self._tail
            self._start_vlm_buffer(
                3,
                f"第{m_v3.group(2)}轮 · 局部推理",
                f"{tid} · 第{m_v3.group(2)}轮",
                "VLM 与局部工具",
                link_from=parent,
            )
            return

        if "🤖" in line and "[VLM·阶段三·强制总结]" in line:
            m2 = re.search(r"强制总结\]\s*(\S+)", line)
            tid = m2.group(1) if m2 else (self._current_target or "unknown")
            parent = self._target_tails.get(tid) or self._tail
            rel = self._last_local_by_target.get(tid) or self._last_image_rel
            th = line.strip()
            self._discard_buffer()
            self._pending_vlm_id = None
            if rel:
                nid = self._new_step(
                    3,
                    "强制总结",
                    f"VLM · {tid} · 强制总结",
                    subtitle="工具次数达上限",
                    thought=th,
                    image_path=rel,
                    thumb_source="当前局部图 · 总结",
                    link_from=parent,
                )
                self._target_tails[tid] = nid
            else:
                pt = self._target_tails.get(tid)
                if pt and pt in self._nodes:
                    self._nodes[pt].setdefault("details", {})["forced_summary_no_image"] = th
            return

        if self._vlm_buffer and self._vlm_buffer.get("phase") == 3:
            if "🖼️" in line and "[VLM·描述]" in line:
                cap = re.sub(r"^.*\[VLM·描述\]\s*", "", line).strip()
                self._vlm_buffer.setdefault("details", {})["image_caption"] = cap
                return
            if "💭" in line and "[VLM·思考]" in line:
                self._vlm_buffer["thought"] = re.sub(r"^.*\[VLM·思考\]\s*", "", line).strip()
                return
            if "🛠️" in line and "[VLM·决策]" in line:
                self._vlm_buffer.setdefault("details", {})["decision"] = line.strip()
                return

        if self._pending_vlm_id and self._pending_vlm_id in self._nodes:
            n = self._nodes[self._pending_vlm_id]
            if n.get("phase") == 3:
                if "🖼️" in line and "[VLM·描述]" in line:
                    cap = re.sub(r"^.*\[VLM·描述\]\s*", "", line).strip()
                    n.setdefault("details", {})["image_caption"] = cap
                    return
                if "💭" in line and "[VLM·思考]" in line:
                    n["thought"] = re.sub(r"^.*\[VLM·思考\]\s*", "", line).strip()
                    return
                if "🛠️" in line and "[VLM·决策]" in line:
                    n.setdefault("details", {})["decision"] = line.strip()
                    return

        if "✅" in line and ("超分成功" in line or "二值化成功" in line or "灰度化成功" in line):
            m2 = re.search(r"→\s*(\S+\.(?:png|jpg|jpeg))", line, re.I)
            rel = _rel_workspace_path(m2.group(1)) if m2 else None
            self._merge_into_pending(
                line,
                "局部处理结果",
                image_path=rel,
                thumb_source=_thumb_for_new_image(line, rel) if rel else None,
            )
            tid = self._current_target
            if tid and self._pending_vlm_id:
                self._target_tails[tid] = self._pending_vlm_id
            return

        if "情报提取完成" in line:
            self._pending_vlm_id = None
            self._discard_buffer()
            return

        if "🔵" in line and "阶段四" in line:
            self._discard_buffer()
            self._pending_vlm_id = None
            return

        if "🤖" in line and "[VLM·阶段四]" in line:
            prev_tail = self._tail
            nid = self._new_step(
                4,
                "阶段四最终输出",
                "RAG · 知识检索",
                subtitle="关键词与检索",
                link=False,
            )
            if self._target_tails:
                for tail in self._target_tails.values():
                    self._ensure_edge(tail, nid)
            elif prev_tail is not None:
                self._ensure_edge(prev_tail, nid)
            self._tail = nid
            self._pending_vlm_id = nid
            return

        if "🔍" in line and "RAG" in line:
            self._merge_into_pending(line, "执行 RAG 检索")
            return

        if "✅" in line and "检索完成" in line:
            self._merge_into_pending(line, "检索完成")
            return

        if "🟣" in line and "阶段五" in line:
            self._discard_buffer()
            self._pending_vlm_id = None
            return

        if "🤖" in line and "[VLM·阶段五]" in line:
            self._pending_vlm_id = self._new_step(
                5,
                "阶段五最终输出",
                "SOAP · 结构化报告",
                subtitle="结构化情报总结",
                hide_thumbnail=True,
            )
            return

        if "🎉" in line and "任务圆满结束" in line:
            for n in self._nodes.values():
                if n.get("status") == "running":
                    n["status"] = "done"
            t = self._tail
            if t and t in self._nodes and self._nodes[t].get("phase") == 5:
                self._nodes[t].setdefault("details", {})["mission_complete"] = line.strip()
            return

        if "[档案]" in line and ".json" in line:
            return
