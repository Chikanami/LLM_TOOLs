#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Water Sort Puzzle — 完整状态空间图生成器
输入：谜题初始条件 (JSON)
输出：自包含 HTML 可视化文件（SCC 压缩 + 距离驱动边染色 + 层级/力导向双布局）

用法：
  python water_sort_graph.py input.json            → 生成 input_graph.html
  python water_sort_graph.py input.json -o out.html → 指定输出路径
  python water_sort_graph.py                       → 从 stdin 读取，输出 water_sort_graph.html
"""

import json
import sys
import os
import base64
from collections import deque
from typing import Tuple, List, Dict, Set, Optional

sys.setrecursionlimit(50000)


# ═══════════════════════════════════════════════════════════════
# 状态表示
# ═══════════════════════════════════════════════════════════════

def canonicalize(state: Tuple[Tuple[int, ...], ...]) -> Tuple[Tuple[int, ...], ...]:
    """试管排序消除置换对称"""
    return tuple(sorted(state))


def get_top_layer(tube: Tuple[int, ...]) -> Optional[Tuple[int, int]]:
    """返回 (颜色, 连续层体积)；空管返回 None"""
    if not tube:
        return None
    color = tube[-1]
    count = 0
    for i in range(len(tube) - 1, -1, -1):
        if tube[i] == color:
            count += 1
        else:
            break
    return (color, count)


def is_solution(Vol: int, state: Tuple[Tuple[int, ...], ...]) -> bool:
    """目标状态：每管全空 或 单色满"""
    for tube in state:
        if not tube:
            continue
        if len(tube) != Vol or len(set(tube)) != 1:
            return False
    return True


# ═══════════════════════════════════════════════════════════════
# 状态空间探索
# ═══════════════════════════════════════════════════════════════

def get_next_states(Vol: int, state: Tuple[Tuple[int, ...], ...]) -> List[Tuple[Tuple[int, ...], ...]]:
    """生成所有合法倾倒的后继状态（已规范化）"""
    next_states = []
    h = len(state)
    for i in range(h):
        if not state[i]:
            continue
        top_color, top_count = get_top_layer(state[i])
        for j in range(h):
            if i == j:
                continue
            dest = state[j]
            space = Vol - len(dest)
            if space == 0:
                continue
            if dest and dest[-1] != top_color:
                continue
            pour = min(top_count, space)
            if pour == 0:
                continue

            new = list(state)
            src_list = list(state[i])
            for _ in range(pour):
                src_list.pop()
            new[i] = tuple(src_list)
            dst_list = list(dest)
            for _ in range(pour):
                dst_list.append(top_color)
            new[j] = tuple(dst_list)
            next_states.append(canonicalize(tuple(new)))
    return next_states


def explore(Vol: int, init: tuple, max_states: int = 50000):
    """BFS 枚举所有可达状态，返回 (sid_map, edges, states)"""
    sid = {init: 0}
    states = [init]
    edges = []
    q = deque([0])
    while q:
        cur = q.popleft()
        for ns in get_next_states(Vol, states[cur]):
            if ns not in sid:
                if len(states) >= max_states:
                    print("WARNING: 达到上限 %d，状态空间可能不完整" % max_states, file=sys.stderr)
                    return sid, edges, states
                sid[ns] = len(states)
                states.append(ns)
                q.append(len(states) - 1)
            edges.append((cur, sid[ns]))
    return sid, edges, states


# ═══════════════════════════════════════════════════════════════
# SCC 压缩 (Tarjan)
# ═══════════════════════════════════════════════════════════════

def tarjan(n: int, adj: List[List[int]]) -> List[List[int]]:
    """返回强连通分量列表"""
    idx = 0
    indices = [-1] * n
    lowlink = [0] * n
    onstack = [False] * n
    stack = []
    sccs = []

    def strongconnect(v):
        nonlocal idx
        indices[v] = idx
        lowlink[v] = idx
        idx += 1
        stack.append(v)
        onstack[v] = True
        for w in adj[v]:
            if indices[w] == -1:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif onstack[w]:
                lowlink[v] = min(lowlink[v], indices[w])
        if lowlink[v] == indices[v]:
            scc = []
            while True:
                w = stack.pop()
                onstack[w] = False
                scc.append(w)
                if w == v:
                    break
            sccs.append(scc)

    for v in range(n):
        if indices[v] == -1:
            strongconnect(v)
    return sccs


def condense(states, edges, sccs):
    """构建 SCC 凝聚图（DAG），返回 (dag_adj, state_to_scc)"""
    state_to_scc = {}
    for sid, scc in enumerate(sccs):
        for v in scc:
            state_to_scc[v] = sid
    dag_adj = [set() for _ in sccs]
    for u, v in edges:
        su, sv = state_to_scc[u], state_to_scc[v]
        if su != sv:
            dag_adj[su].add(sv)
    return [sorted(s) for s in dag_adj], state_to_scc


# ═══════════════════════════════════════════════════════════════
# 分类 & 距离
# ═══════════════════════════════════════════════════════════════

def classify_nodes(sccs, state_to_scc, init_id, Vol, states, dag_adj):
    """
    返回 (cls, init_scc, sol_sccs)
    cls: {scc_id: 'init'|'solution'|'dead_cycle'|'cycle'|'dead_end'|'intermediate'}
    """
    init_scc = state_to_scc[init_id]

    sol_sccs = set()
    for sid, scc in enumerate(sccs):
        if any(is_solution(Vol, states[v]) for v in scc):
            sol_sccs.add(sid)

    cycle_sccs = {sid for sid, scc in enumerate(sccs) if len(scc) > 1}

    dead_sccs = set()
    for sid in range(len(sccs)):
        if not dag_adj[sid] and sid not in sol_sccs:
            dead_sccs.add(sid)

    cls = {}
    for sid in range(len(sccs)):
        if sid in sol_sccs:
            cls[sid] = 'solution'
        elif sid == init_scc:
            cls[sid] = 'init'
        elif sid in dead_sccs and sid in cycle_sccs:
            cls[sid] = 'dead_cycle'          # 死循环：内部环路，无出路
        elif sid in cycle_sccs:
            cls[sid] = 'cycle'               # 活循环：有出路
        elif sid in dead_sccs:
            cls[sid] = 'dead_end'
        else:
            cls[sid] = 'intermediate'
    return cls, init_scc, sol_sccs


def compute_distances(dag_adj, init_scc, sol_sccs):
    """
    返回 (d_from_init, d_to_sol)
    """
    d_init = {init_scc: 0}
    q = deque([init_scc])
    while q:
        u = q.popleft()
        for v in dag_adj[u]:
            if v not in d_init:
                d_init[v] = d_init[u] + 1
                q.append(v)

    rev_adj = [[] for _ in dag_adj]
    for u in range(len(dag_adj)):
        for v in dag_adj[u]:
            rev_adj[v].append(u)

    d_sol = {}
    q = deque()
    for s in sol_sccs:
        d_sol[s] = 0
        q.append(s)
    while q:
        u = q.popleft()
        for v in rev_adj[u]:
            if v not in d_sol:
                d_sol[v] = d_sol[u] + 1
                q.append(v)

    return d_init, d_sol


# ═══════════════════════════════════════════════════════════════
# 边颜色（核心——修复红色分量）
# ═══════════════════════════════════════════════════════════════

def edge_color(src_scc, dst_scc, d_init, d_sol, sol_exists, init_scc, sol_sccs):
    """
    颜色语义：
      #00FF00 (绿)  ── 近初始（或直接出自初始）
      #00FFFF (青)  ── 近解（或直接连解）
      #FF0000 (红)  ── 远离两者
      #CC3333 (暗红) ── 有解时不可达解的支线
      #666666 (灰)  ── 不可达

    修复要点：使用幂函数放大红色权重，使中间区域的红色肉眼可见。
    """
    # ── 特判 ──
    if sol_exists and dst_scc in sol_sccs:
        return "#00FFFF"
    if src_scc == init_scc:
        return "#00FF00"

    di = d_init.get(dst_scc)
    ds = d_sol.get(dst_scc) if sol_exists else None

    if di is None:
        return "#666666"

    if sol_exists:
        if ds is None:
            # 可达初始但不可达任何解 → 死支 → 暗红
            return "#CC3333"

        max_di = max(d_init.values()) if d_init else 1
        max_ds = max(d_sol.values()) if d_sol else 1

        if max_di == 0 and max_ds == 0:
            return "#00FF00"

        ni = di / max_di if max_di > 0 else 0
        ns = ds / max_ds if max_ds > 0 else 0

        # ── 幂函数增强红色 ──
        # w_g 在 ni 低时大（近初始），ni 高时迅速坍缩
        # w_c 对 ns 同理
        # w_r 对 (ni*ns) 用 0.7 次方放大：使中等距离就有明显红色
        w_g = (1.0 - ni) ** 1.5
        w_c = (1.0 - ns) ** 1.5
        w_r = (ni * ns) ** 0.7

        total = w_g + w_c + w_r
        if total < 0.001:
            total = 1.0

        r = max(0, min(255, int(255 * w_r / total)))
        g = max(0, min(255, int(255 * (w_g + w_c) / total)))
        b = max(0, min(255, int(255 * w_c / total)))
        return "#%02X%02X%02X" % (r, g, b)

    else:
        # 无解：绿→红 线性
        max_di = max(d_init.values()) if d_init else 1
        ni = di / max_di if max_di > 0 else 0
        r = int(255 * ni)
        g = int(255 * (1.0 - ni))
        return "#%02X%02X00" % (r, g)


# ═══════════════════════════════════════════════════════════════
# 死循环节点 SVG（橙色带红色中心）
# ═══════════════════════════════════════════════════════════════

def dead_cycle_svg_uri():
    """返回 data: URI —— 橙色圆 + 红色圆心"""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="44" height="44" viewBox="0 0 44 44">'
        '<circle cx="22" cy="22" r="20" fill="#FFB74D" stroke="#F57C00" stroke-width="2.5"/>'
        '<circle cx="22" cy="22" r="7" fill="#EF5350" stroke="#C62828" stroke-width="1"/>'
        '</svg>'
    )
    b64 = base64.b64encode(svg.encode('utf-8')).decode('ascii')
    return 'data:image/svg+xml;base64,' + b64


# ═══════════════════════════════════════════════════════════════
# HTML 生成
# ═══════════════════════════════════════════════════════════════

NODE_STYLE = {
    'init':         {'bg': '#448AFF', 'border': '#1565C0', 'font': '#ffffff'},
    'intermediate': {'bg': '#F5F5F5', 'border': '#BDBDBD', 'font': '#333333'},
    'cycle':        {'bg': '#FFB74D', 'border': '#F57C00', 'font': '#333333'},
    'dead_cycle':   {'bg': '#FFB74D', 'border': '#EF5350', 'font': '#333333',
                     'image': True},   # 使用 SVG 图片
    'dead_end':     {'bg': '#EF5350', 'border': '#C62828', 'font': '#ffffff'},
    'solution':     {'bg': '#66BB6A', 'border': '#2E7D32', 'font': '#ffffff'},
}

CLASS_LABEL = {
    'init': '初始', 'solution': '解', 'cycle': '环',
    'dead_cycle': '死循环', 'dead_end': '死胡同', 'intermediate': '中间',
}


def build_html(sccs, dag_adj, cls, d_init, d_sol, init_scc, sol_sccs,
               Vol, states, s2scc, initial_raw):
    sol_exists = bool(sol_sccs)
    num_sccs = len(sccs)

    # ── 节点数据 ──
    nodes_json = []
    dead_cycle_img = dead_cycle_svg_uri()

    for sid in range(num_sccs):
        c = cls[sid]
        sc = len(sccs[sid])
        sty = NODE_STYLE[c]
        is_key = (c in ('init', 'solution'))

        # 层级（用于层级布局）
        level = d_init.get(sid, 999) if d_init.get(sid) is not None else 999

        # 标签
        if c == 'intermediate':
            label = "S%d" % sid
        elif c == 'dead_cycle':
            label = "死循环\nS%d" % sid
        else:
            label = "%s\nS%d" % (CLASS_LABEL[c], sid)

        # tooltip
        di_val = d_init.get(sid)
        ds_val = d_sol.get(sid) if sol_exists else None
        di_str = str(di_val) if di_val is not None else '∞'
        ds_str = str(ds_val) if ds_val is not None else ('N/A' if not sol_exists else '∞')

        title = "SCC%d | %s | 含%d状态 | d_init=%s | d_sol=%s" % (
            sid, CLASS_LABEL[c], sc, di_str, ds_str
        )

        node_obj = {
            'id': sid,
            'label': label,
            'title': title,
            'level': level,
            'color': {
                'background': sty['bg'],
                'border': sty['border'],
                'highlight': {'background': sty['bg'], 'border': '#000000'},
                'hover': {'background': sty['bg'], 'border': '#000000'},
            },
            'font': {
                'size': 11 if is_key else 9,
                'color': sty['font'],
                'face': 'Microsoft YaHei, PingFang SC, sans-serif',
                'bold': is_key,
            },
            'shape': 'box' if is_key else 'dot',
            'size': 28 if is_key else 16,
            'borderWidth': 3 if is_key else 1,
        }

        # 死循环：使用 SVG 图片渲染
        if c == 'dead_cycle':
            node_obj['shape'] = 'image'
            node_obj['image'] = dead_cycle_img
            node_obj['size'] = 24
            node_obj['borderWidth'] = 0
            # 保留 color 用于选中高亮
            node_obj['color']['highlight'] = {'background': '#FFB74D', 'border': '#EF5350'}
            node_obj['color']['hover'] = {'background': '#FFB74D', 'border': '#EF5350'}

        nodes_json.append(node_obj)

    # ── 边数据 ──
    edges_json = []
    seen_edges = set()
    for u in range(num_sccs):
        for v in dag_adj[u]:
            if (u, v) in seen_edges:
                continue
            seen_edges.add((u, v))
            ec = edge_color(u, v, d_init, d_sol, sol_exists, init_scc, sol_sccs)
            edges_json.append({
                'from': u,
                'to': v,
                'color': {'color': ec, 'highlight': ec, 'hover': ec, 'inherit': False},
                'arrows': {'to': {'enabled': True, 'scaleFactor': 0.8}},
                'width': 2.5,
                'smooth': {'type': 'curvedCCW', 'roundness': 0.18},
            })

    # ── 侧边栏统计 ──
    counts = {}
    for c in ['init', 'intermediate', 'cycle', 'dead_cycle', 'dead_end', 'solution']:
        counts[c] = sum(1 for x in cls.values() if x == c)

    stat_html = (
        '<div class="stat-row"><span>总状态数</span><span>%d</span></div>\n'
        '<div class="stat-row"><span>SCC 节点</span><span>%d</span></div>\n'
        '<div class="stat-row"><span>DAG 边数</span><span>%d</span></div>\n'
        '<div class="stat-row"><span>试管容积 N</span><span>%d</span></div>\n'
        '<div class="stat-row"><span>试管数 h</span><span>%d</span></div>\n'
        '<div class="stat-row"><span>存在解</span><span style="color:%s">%s</span></div>'
    ) % (
        len(states), num_sccs, len(edges_json),
        Vol, len(initial_raw),
        '#66BB6A' if sol_exists else '#EF5350',
        '是' if sol_exists else '否'
    )

    legend_items = []
    for c in ['init', 'intermediate', 'cycle', 'dead_cycle', 'dead_end', 'solution']:
        sty = NODE_STYLE[c]
        label = CLASS_LABEL[c]
        cnt = counts[c]
        if c == 'dead_cycle':
            legend_items.append(
                '<div class="legend-item">'
                '<img src="%s" width="22" height="22" style="flex-shrink:0" alt="">'
                '<span>%s (%d)</span>'
                '</div>' % (dead_cycle_img, label, cnt)
            )
        else:
            legend_items.append(
                '<div class="legend-item">'
                '<div class="dot" style="background:%s;border-color:%s"></div>'
                '<span>%s (%d)</span>'
                '</div>' % (sty['bg'], sty['border'], label, cnt)
            )
    legend_html = '\n'.join(legend_items)

    # ── 初始条件展示 ──
    display = {}
    for i, t in enumerate(initial_raw):
        display["tt%d" % (i+1)] = list(t) if t else []
    init_json_str = json.dumps(display, ensure_ascii=False, indent=2)

    # ── 注入 JS 变量 ──
    init_scc_js = init_scc
    sol_scc_js = min(sol_sccs) if sol_sccs else -1  # 第一个解节点

    # ── 模板 ──
    html = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Water Sort – 状态空间图</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.js">
</script>
<link href="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.css" rel="stylesheet">
<style>
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
body{
  font-family:'Microsoft YaHei','PingFang SC','Noto Sans SC',sans-serif;
  background:#0c0c1d;color:#c8c8d4;display:flex;height:100vh;overflow:hidden;
}
#graph{flex:1;background:#12122a;min-width:0}
#side{
  width:320px;padding:20px;background:#16162e;
  overflow-y:auto;font-size:13px;border-left:2px solid #0f3460;
  display:flex;flex-direction:column;gap:14px;
}
h2{color:#e94560;font-size:20px;border-bottom:2px solid #e94560;padding-bottom:10px;margin-bottom:2px}
h3{color:#f0a500;font-size:14px;margin:0 0 6px}
.stat-row{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #2a2a4a}
.stat-row span:last-child{font-weight:bold;color:#e0e0e0}
.legend-item{display:flex;align-items:center;gap:10px;margin:5px 0}
.dot{width:20px;height:20px;border-radius:50%;border:2px solid transparent;flex-shrink:0}
.line{width:42px;height:4px;border-radius:2px;flex-shrink:0}
.init-box{
  background:#0d1b36;border-radius:6px;padding:10px;
  font:11px 'Cascadia Code','Courier New',monospace;
  max-height:200px;overflow-y:auto;white-space:pre-wrap;
  word-break:break-all;color:#8ab4f8;border:1px solid #1a3a5c;
}
.btn-row{display:flex;flex-wrap:wrap;gap:6px}
.btn{
  flex:1;min-width:70px;padding:8px 10px;
  border:none;border-radius:6px;cursor:pointer;
  font-size:12px;font-weight:bold;font-family:inherit;
  transition:transform .1s,box-shadow .1s;
}
.btn:active{transform:scale(0.96)}
.btn-init{background:#448AFF;color:#fff}
.btn-sol{background:#66BB6A;color:#fff}
.btn-layout{background:#f0a500;color:#0c0c1d}
.btn-physics{background:#7c4dff;color:#fff}
.btn:hover{box-shadow:0 0 12px rgba(255,255,255,.25)}
.note{font-size:11px;color:#888;line-height:1.5}
</style>
</head>
<body>
<div id="graph"></div>
<div id="side">
<h2>状态空间图</h2>
<div class="note">SCC 凝聚图 · 拖拽节点 · 滚轮缩放 · 按钮定位</div>

<div class="btn-row">
  <button class="btn btn-init" onclick="focusInit()" title="定位到初始状态节点">📍 初始节点</button>
  <button class="btn btn-sol" id="btnSol" onclick="focusSol()" title="定位到解节点">🎯 解节点</button>
</div>
<div class="btn-row">
  <button class="btn btn-layout" id="btnLayout" onclick="toggleLayout()">🏗️ 层级布局</button>
  <button class="btn btn-physics" id="btnPhysics" onclick="togglePhysics()">⏸️ 暂停物理</button>
</div>

<h3>统计</h3>
__STAT_ROWS__

<h3>节点图例</h3>
__LEGEND_NODES__

<h3>边颜色</h3>
<div class="legend-item"><div class="line" style="background:#00FF00"></div><span>近初始 / 出自初始</span></div>
<div class="legend-item"><div class="line" style="background:#00FFFF"></div><span>近解 / 直连解</span></div>
<div class="legend-item"><div class="line" style="background:#FF0000"></div><span>远离两者</span></div>
<div class="legend-item"><div class="line" style="background:#CC3333"></div><span>不可达解（死支）</span></div>
<div class="legend-item"><div class="line" style="background:#666666"></div><span>不可达</span></div>

<h3>初始条件</h3>
<div class="init-box">__INIT_JSON__</div>
</div>
<script>
/* ── 参数 ── */
var INIT_SCC = __INIT_SCC__;
var SOL_SCC  = __SOL_SCC__;
var SOL_EXISTS = __SOL_EXISTS__;

/* ── 数据 ── */
var nodes = new vis.DataSet(__NODES_JSON__);
var edges = new vis.DataSet(__EDGES_JSON__);

/* ── 布局选项 ── */
var forceOptions = {
  physics: {
    enabled: true,
    solver: 'forceAtlas2Based',
    forceAtlas2Based: {
      gravitationalConstant: -55,
      centralGravity: 0.012,
      springLength: 160,
      springConstant: 0.06,
      damping: 0.45
    },
    stabilization: { iterations: 250, updateInterval: 10 }
  },
  layout: { hierarchical: false },
  edges: {
    arrows: { to: { enabled: true, scaleFactor: 0.7 } },
    smooth: { type: 'curvedCCW', roundness: 0.18 }
  },
  interaction: {
    hover: true,
    tooltipDelay: 120,
    zoomView: true,
    dragView: true,
    navigationButtons: true
  },
  nodes: { borderWidthSelected: 4 }
};

var hierOptions = {
  physics: { enabled: false },
  layout: {
    hierarchical: {
      enabled: true,
      direction: 'LR',
      sortMethod: 'directed',
      nodeSpacing: 140,
      levelSeparation: 220,
      treeSpacing: 40,
      blockShifting: true,
      edgeMinimization: true,
      parentCentralization: false
    }
  },
  edges: {
    arrows: { to: { enabled: true, scaleFactor: 0.7 } },
    smooth: { type: 'curvedCCW', roundness: 0.18 }
  },
  interaction: {
    hover: true,
    tooltipDelay: 120,
    zoomView: true,
    dragView: true,
    navigationButtons: true
  },
  nodes: { borderWidthSelected: 4 }
};

var container = document.getElementById('graph');
var network = new vis.Network(container, { nodes: nodes, edges: edges }, forceOptions);
var usingHierarchical = false;
var physicsEnabled = true;

/* ── 功能按钮 ── */
function focusInit() {
  network.focus(INIT_SCC, { scale: 0.9, animation: { duration: 700, easingFunction: 'easeInOutQuad' } });
  setTimeout(function(){ network.selectNodes([INIT_SCC]); }, 750);
}

function focusSol() {
  if (!SOL_EXISTS) { alert('该谜题无解'); return; }
  network.focus(SOL_SCC, { scale: 0.9, animation: { duration: 700, easingFunction: 'easeInOutQuad' } });
  setTimeout(function(){ network.selectNodes([SOL_SCC]); }, 750);
}

function toggleLayout() {
  var btn = document.getElementById('btnLayout');
  if (usingHierarchical) {
    network.setOptions(forceOptions);
    usingHierarchical = false;
    btn.textContent = '🏗️ 层级布局';
    if (!physicsEnabled) {
      network.setOptions({ physics: { enabled: false } });
    }
  } else {
    network.setOptions(hierOptions);
    usingHierarchical = true;
    btn.textContent = '🕸️ 力导向布局';
    physicsEnabled = false;
    document.getElementById('btnPhysics').textContent = '▶️ 启动物理';
  }
}

function togglePhysics() {
  var btn = document.getElementById('btnPhysics');
  if (physicsEnabled) {
    network.setOptions({ physics: { enabled: false } });
    physicsEnabled = false;
    btn.textContent = '▶️ 启动物理';
  } else {
    if (usingHierarchical) {
      toggleLayout();  // 回力导向再开物理
    }
    network.setOptions({ physics: { enabled: true } });
    physicsEnabled = true;
    btn.textContent = '⏸️ 暂停物理';
  }
}

/* ── 无解时隐藏解节点按钮 ── */
if (!SOL_EXISTS) {
  document.getElementById('btnSol').style.display = 'none';
}

/* ── 键盘快捷键 ── */
document.addEventListener('keydown', function(e) {
  if (e.key === 'i' || e.key === 'I') { focusInit(); }
  if ((e.key === 's' || e.key === 'S') && SOL_EXISTS) { focusSol(); }
  if (e.key === 'l' || e.key === 'L') { toggleLayout(); }
  if (e.key === 'p' || e.key === 'P') { togglePhysics(); }
});
</script>
</body>
</html>'''

    html = html.replace('__STAT_ROWS__', stat_html)
    html = html.replace('__LEGEND_NODES__', legend_html)
    html = html.replace('__INIT_JSON__', init_json_str)
    html = html.replace('__NODES_JSON__', json.dumps(nodes_json, ensure_ascii=False))
    html = html.replace('__EDGES_JSON__', json.dumps(edges_json, ensure_ascii=False))
    html = html.replace('__INIT_SCC__', str(init_scc_js))
    html = html.replace('__SOL_SCC__', str(sol_scc_js))
    html = html.replace('__SOL_EXISTS__', 'true' if sol_exists else 'false')

    return html


# ═══════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════

def main():
    output_path = None
    args = sys.argv[1:]
    input_path = None

    i = 0
    while i < len(args):
        if args[i] == '-o' and i + 1 < len(args):
            output_path = args[i + 1]
            i += 2
        elif not args[i].startswith('-') and input_path is None:
            input_path = args[i]
            i += 1
        else:
            i += 1

    if input_path:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if output_path is None:
            base = os.path.splitext(input_path)[0]
            output_path = base + '_graph.html'
    else:
        data = json.load(sys.stdin)
        if output_path is None:
            output_path = 'water_sort_graph.html'

    Vol = data['Vol']
    raw = data['TtList']
    keys = sorted(raw.keys(), key=lambda k: (len(k), k))
    initial_display = tuple(raw[k] for k in keys)
    initial = tuple(tuple(raw[k]) for k in keys)
    init_canon = canonicalize(initial)

    print("=" * 50, file=sys.stderr)
    print("Water Sort Puzzle — 状态空间图生成器", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    print("试管容积 N = %d" % Vol, file=sys.stderr)
    print("试管数量 h = %d" % len(initial), file=sys.stderr)

    # 1. 枚举
    sid_map, transitions, states = explore(Vol, init_canon)
    n = len(states)
    print("可达状态数: %d" % n, file=sys.stderr)
    print("转移边数:   %d" % len(transitions), file=sys.stderr)

    # 2. SCC
    raw_adj = [[] for _ in range(n)]
    for u, v in transitions:
        raw_adj[u].append(v)
    sccs = tarjan(n, raw_adj)
    print("SCC 数量:   %d" % len(sccs), file=sys.stderr)

    # 3. DAG
    dag_adj, s2scc = condense(states, transitions, sccs)
    init_id = sid_map[init_canon]

    # 4. 分类
    cls, init_scc, sol_sccs = classify_nodes(sccs, s2scc, init_id, Vol, states, dag_adj)
    for c in ['init', 'solution', 'cycle', 'dead_cycle', 'dead_end', 'intermediate']:
        cnt = sum(1 for x in cls.values() if x == c)
        if cnt > 0:
            print("  %s: %d" % (CLASS_LABEL.get(c, c), cnt), file=sys.stderr)

    # 5. 距离
    d_init, d_sol = compute_distances(dag_adj, init_scc, sol_sccs)
    if sol_sccs:
        print("解节点 SCC: %s" % sorted(sol_sccs), file=sys.stderr)

    # 6. 生成 HTML
    html = build_html(sccs, dag_adj, cls, d_init, d_sol, init_scc, sol_sccs,
                      Vol, states, s2scc, initial_display)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print("=" * 50, file=sys.stderr)
    print("输出文件: %s" % output_path, file=sys.stderr)
    print("文件大小: %d 字节" % len(html.encode('utf-8')), file=sys.stderr)
    print("完成。用浏览器打开该 HTML 文件即可查看。", file=sys.stderr)


if __name__ == '__main__':
    main()
