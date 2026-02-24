#!/usr/bin/env python3
"""
アニメスタジオ ポジショニングマップ生成スクリプト
Plotlyを使用して9ビュー切替のインタラクティブHTMLマップを生成する

ビュー一覧:
  1. 設立時マップ
  2. 現在マップ
  3. 成長軌跡マップ
  4. ビジネスモデル分析マップ
  5. AI活用度マップ
  6. 収益・規模マップ
  7. 所有構造・企業グループマップ
  8. 配信PF関係マップ
  9. 設立年・黒字化分析マップ

成長軌跡の矢印: annotation ではなく line trace + triangle marker で描画
"""

import json
import math
import yaml
import plotly.graph_objects as go
from pathlib import Path

# --- データ読み込み ---
DATA_PATH = Path(__file__).parent / "data" / "studios_merged.yaml"
OUTPUT_PATH = Path(__file__).parent / "positioning_map.html"

with open(DATA_PATH, "r", encoding="utf-8") as f:
    data = yaml.safe_load(f)

studios = data["studios"]

# --- スタジオのグローバルインデックスマップ（id → index）---
studio_global_idx = {id(s): i for i, s in enumerate(studios)}

# --- データ分類 ---
domestic = [s for s in studios if s["region"] == "domestic"]
international = [s for s in studios if s["region"] == "international"]

# 成長軌跡マップ用: 設立時と現在のデータが両方あるスタジオ
growth_studios = [
    s for s in studios
    if s.get("size_founded_num") and s.get("size_current_num")
    and s["size_founded_num"] != s["size_current_num"]
]

# --- 色定義 ---
COLOR_DOMESTIC = "#3498DB"
COLOR_INTERNATIONAL = "#E74C3C"
COLOR_GRID = "rgba(200,200,200,0.3)"

# --- カラーパレット ---
COLOR_PALETTES = {
    "ai_adoption_level": {
        "none": "#BDBDBD",
        "experimental": "#FFC107",
        "production": "#4CAF50",
        "core": "#FFD700",
    },
    "ownership_type": {
        "independent": "#27AE60",
        "subsidiary": "#2980B9",
        "group_company": "#8E44AD",
    },
    "business_model": {
        "commission": "#E74C3C",
        "mixed": "#F39C12",
        "original": "#27AE60",
        "ip_holding": "#2980B9",
    },
    "primary_platform_color": {
        "Netflix": "#E50914",
        "Crunchyroll": "#F47521",
        "Amazon": "#00A8E1",
        "Disney+": "#113CCF",
        "Bilibili": "#00A1D6",
        "Other": "#95A5A6",
    },
}

# --- ラベル名マッピング ---
LABEL_NAMES = {
    "ai_adoption_level": {
        "none": "なし",
        "experimental": "実験的",
        "production": "本番導入",
        "core": "コア技術",
    },
    "ownership_type": {
        "independent": "独立系",
        "subsidiary": "子会社",
        "group_company": "グループ会社",
    },
    "business_model": {
        "commission": "受託制作",
        "mixed": "混合",
        "original": "オリジナル",
        "ip_holding": "IP保有",
    },
}

# --- 共通レイアウト ---
AXIS_RANGE_X = [-0.05, 1.05]
AXIS_RANGE_Y_LINEAR = [-50, 3000]
AXIS_RANGE_Y_LOG = [0.5, 4.0]


# --- チャートサイズ ---
CHART_WIDTH = 1200
CHART_HEIGHT = 750

# --- マーカー固定サイズ ---
MARKER_SIZE = 10  # 全ビュー共通の固定マーカーサイズ
MARKER_SIZE_SMALL = 7  # 成長軌跡の始点（設立時）用


# --- ラベル衝突回避 ---
def resolve_label_positions(studio_list, size_key="size_current_num", x_key="original_score"):
    """ラベルが近いスタジオ同士のtextpositionをずらして衝突回避（多段）"""
    positions = []
    for i, s in enumerate(studio_list):
        x = s.get(x_key, s["original_score"])
        if x is None:
            x = 0
        y_val = s.get(size_key, 10) or 10
        y = y_val
        positions.append((x, y, i))

    text_positions = ["middle right"] * len(studio_list)
    alternatives = [
        "top right", "bottom right", "top center",
        "top left", "middle left", "bottom center", "bottom left",
    ]

    # 全ペアを距離順にソートして近い順から処理
    pairs = []
    for i in range(len(positions)):
        for j in range(i + 1, len(positions)):
            dx = abs(positions[i][0] - positions[j][0])
            dy = abs(positions[i][1] - positions[j][1])
            pairs.append((dx + dy * 0.5, i, j, dx, dy))
    pairs.sort()

    used = set()
    for _, i, j, dx, dy in pairs:
        if dx < 0.10 and dy < 150:
            # j番目のラベルを、i番目およびすでに使われた位置と被らないようずらす
            for alt in alternatives:
                if alt != text_positions[i] and (j, alt) not in used:
                    text_positions[j] = alt
                    used.add((j, alt))
                    break
    return text_positions


def merge_overlapping(studio_list, x_key="original_score", size_key="size_current_num"):
    """同一座標のスタジオをマージし、ホバー・ラベルを統合"""
    groups = {}
    for s in studio_list:
        x = s.get(x_key, s["original_score"])
        y = s.get(size_key, 10) or 10
        key = (x, y)
        groups.setdefault(key, []).append(s)

    merged = []
    for (x, y), studios in groups.items():
        if len(studios) == 1:
            merged.append(studios[0])
        else:
            combined = dict(studios[0])
            combined["name"] = "<br>".join(s["name"] for s in studios)
            combined["_hover_parts"] = studios
            merged.append(combined)
    return merged


def build_point_map(studio_list, x_key="original_score", size_key="size_current_num"):
    """各マージポイントが元のどのスタジオに対応するかのマッピングを構築"""
    merged = merge_overlapping(studio_list, x_key, size_key)
    point_map = []
    for s in merged:
        if "_hover_parts" in s:
            indices = [studio_global_idx[id(p)] for p in s["_hover_parts"]]
        else:
            indices = [studio_global_idx[id(s)]]
        point_map.append(indices)
    return point_map


def make_layout(title_text):
    return dict(
        xaxis=dict(
            title=dict(text="← 受託          オリジナル →", font=dict(size=14)),
            range=AXIS_RANGE_X,
            dtick=0.1,
            gridcolor=COLOR_GRID,
            zeroline=False,
            tickformat=".1f",
        ),
        yaxis=dict(
            title=dict(text="人数規模（人）", font=dict(size=14)),
            type="log",
            range=AXIS_RANGE_Y_LOG,
            dtick=None,
            gridcolor=COLOR_GRID,
            zeroline=False,
            tickformat=",d",
        ),
        title=dict(text=title_text, x=0.5, y=0.965, font=dict(size=16)),
        plot_bgcolor="white",
        paper_bgcolor="white",
        dragmode="pan",
        hovermode="closest",
        hoverdistance=30,
        legend=dict(
            x=0.01, y=0.99,
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#ccc", borderwidth=1,
            font=dict(size=11),
        ),
        margin=dict(l=80, r=40, t=140, b=60),
        width=CHART_WIDTH,
        height=CHART_HEIGHT,
    )


def hover_text(s, size_key="size_current_num"):
    """拡張ホバーテキスト（新フィールドをnull安全に表示）"""
    works = ", ".join(s.get("notable_works", [])[:3])
    region_label = "国内" if s.get("region") == "domestic" else "海外"

    lines = [
        f"<b>{s['name']}</b>",
        f"分類: {region_label}",
        f"設立: {s.get('founded', '?')}年",
        f"人数: {s.get(size_key, '?')}人",
        f"オリジナルスコア: {s.get('original_score', '?')}",
    ]

    # 親会社
    parent = s.get("parent_company")
    if parent:
        lines.append(f"親会社: {parent}")

    # 所有形態
    ot = s.get("ownership_type")
    if ot:
        ot_label = LABEL_NAMES.get("ownership_type", {}).get(ot, ot)
        lines.append(f"所有形態: {ot_label}")

    # AI活用
    ai = s.get("ai_adoption_level")
    if ai and ai != "none":
        ai_label = LABEL_NAMES.get("ai_adoption_level", {}).get(ai, ai)
        detail = s.get("ai_adoption_detail", "")
        ai_text = f"AI活用: {ai_label}"
        if detail:
            ai_text += f" ({detail})"
        lines.append(ai_text)

    # 売上
    rev = s.get("revenue_billion_yen")
    if rev is not None:
        rev_year = s.get("revenue_year", "?")
        lines.append(f"売上: {rev}億円 ({rev_year}年)")

    # 営業利益率
    margin = s.get("operating_margin")
    if margin is not None:
        lines.append(f"営業利益率: {margin*100:.1f}%")

    # 版権収入比率
    lic = s.get("licensing_ratio")
    if lic is not None:
        lines.append(f"版権収入比率: {lic*100:.0f}%")

    # 主要PF
    pf = s.get("primary_platform", [])
    if pf:
        lines.append(f"主要PF: {', '.join(pf)}")

    # 黒字化年数
    ytp = s.get("years_to_profitability")
    if ytp is not None:
        lines.append(f"黒字化年数: {ytp}年")

    lines.append(f"代表作: {works}")

    return "<br>".join(lines)


def make_scatter(studio_list, color, name, size_key="size_current_num",
                 opacity=1.0, symbol="circle", marker_size=None, show_labels=True,
                 x_key="original_score", size_field=None):
    if marker_size is None:
        marker_size = MARKER_SIZE

    # 座標重複スタジオをマージ
    studio_list = merge_overlapping(studio_list, x_key, size_key)

    text_positions = resolve_label_positions(studio_list, size_key, x_key) if show_labels else ["middle right"] * len(studio_list)

    # ホバーテキスト生成（マージされたスタジオは統合表示）
    hover_texts = []
    for s in studio_list:
        if "_hover_parts" in s:
            hover_texts.append("<br>───────────<br>".join(hover_text(part, size_key) for part in s["_hover_parts"]))
        else:
            hover_texts.append(hover_text(s, size_key))

    # 動的マーカーサイズ
    if size_field:
        sizes = []
        for s in studio_list:
            val = s.get(size_field)
            if val and val > 0:
                sizes.append(max(6, min(30, 6 + 8 * math.log10(val))))
            else:
                sizes.append(8)
        marker_size = sizes

    return go.Scatter(
        x=[s.get(x_key, s["original_score"]) for s in studio_list],
        y=[s.get(size_key, 10) or 10 for s in studio_list],
        mode="markers+text" if show_labels else "markers",
        marker=dict(
            size=marker_size,
            color=color,
            opacity=opacity,
            line=dict(width=1, color="white"),
            symbol=symbol,
        ),
        text=[s["name"] for s in studio_list] if show_labels else None,
        textposition=text_positions,
        textfont=dict(size=9, color=color),
        hovertext=hover_texts,
        hoverinfo="text",
        name=name,
    )


def make_categorical_scatter(studio_list, color_field, palette, label_map,
                             x_key="original_score", y_key="size_current_num",
                             size_field=None, legend_prefix=""):
    """カテゴリカル色分けのスキャッタートレースをグループ別に生成"""
    groups = {}
    for s in studio_list:
        val = s.get(color_field, "unknown")
        if val is None:
            val = "unknown"
        groups.setdefault(val, []).append(s)

    scatter_traces = []
    for cat_val, cat_studios in groups.items():
        color = palette.get(cat_val, "#95A5A6")
        label = label_map.get(cat_val, cat_val)
        legend_name = f"{legend_prefix}{label}" if legend_prefix else label

        merged = merge_overlapping(cat_studios, x_key, y_key)
        text_positions = resolve_label_positions(merged, y_key, x_key)

        hover_texts = []
        for s in merged:
            if "_hover_parts" in s:
                hover_texts.append("<br>───────────<br>".join(hover_text(part, y_key) for part in s["_hover_parts"]))
            else:
                hover_texts.append(hover_text(s, y_key))

        # 動的マーカーサイズ
        ms = MARKER_SIZE
        if size_field:
            sizes = []
            for s in merged:
                val = s.get(size_field)
                if val and val > 0:
                    sizes.append(max(6, min(30, 6 + 8 * math.log10(val))))
                else:
                    sizes.append(8)
            ms = sizes

        tr = go.Scatter(
            x=[s.get(x_key, s.get("original_score", 0)) for s in merged],
            y=[s.get(y_key, 10) or 10 for s in merged],
            mode="markers+text",
            marker=dict(
                size=ms,
                color=color,
                opacity=1.0,
                line=dict(width=1, color="white"),
                symbol="circle",
            ),
            text=[s["name"] for s in merged],
            textposition=text_positions,
            textfont=dict(size=9, color=color),
            hovertext=hover_texts,
            hoverinfo="text",
            name=legend_name,
        )
        scatter_traces.append(tr)
    return scatter_traces


GRADIENT_STEPS = 8  # グラデーション分割数


def make_growth_line_traces(studio_list, color, region_label):
    """成長軌跡の線をグラデーション付きで生成"""
    line_traces = []
    for step in range(GRADIENT_STEPS):
        t0 = step / GRADIENT_STEPS
        t1 = (step + 1) / GRADIENT_STEPS
        opacity = 0.08 + 0.77 * ((step + 1) / GRADIENT_STEPS) ** 2
        width = 2.5 + 1.5 * (step / (GRADIENT_STEPS - 1))

        x_seg = []
        y_seg = []
        for s in studio_list:
            x_start = s.get("original_score_founded", s["original_score"])
            x_end = s["original_score"]
            y_start = s["size_founded_num"] or 10
            y_end = s["size_current_num"]
            x0 = x_start + (x_end - x_start) * t0
            x1 = x_start + (x_end - x_start) * t1
            y0 = y_start + (y_end - y_start) * t0
            y1 = y_start + (y_end - y_start) * t1
            x_seg.extend([x0, x1, None])
            y_seg.extend([y0, y1, None])

        tr = go.Scatter(
            x=x_seg, y=y_seg,
            mode="lines",
            line=dict(color=color, width=width),
            opacity=opacity,
            hoverinfo="skip",
            showlegend=False,
            name=f"軌跡線（{region_label}）",
        )
        line_traces.append(tr)
    return line_traces


def get_primary_platform(s):
    """スタジオの主要プラットフォーム（最上位）を返す"""
    pf = s.get("primary_platform", [])
    if not pf:
        return "Other"
    return pf[0]


# ==================================================================
# 全9ビューのトレースを作成し、visibility で切替
# ==================================================================
traces = []
visibility_map = {"founded": [], "current": [], "growth": []}
trace_point_maps = {}  # trace_index -> [[studio_idx, ...], ...]

# --- ビュー1: 設立時マップ ---
tr_dom_founded = make_scatter(domestic, COLOR_DOMESTIC, "国内スタジオ", "size_founded_num")
traces.append(tr_dom_founded)
trace_point_maps[len(traces) - 1] = build_point_map(domestic, "original_score", "size_founded_num")
visibility_map["founded"].append(len(traces) - 1)

tr_intl_founded = make_scatter(international, COLOR_INTERNATIONAL, "海外スタジオ", "size_founded_num")
traces.append(tr_intl_founded)
trace_point_maps[len(traces) - 1] = build_point_map(international, "original_score", "size_founded_num")
visibility_map["founded"].append(len(traces) - 1)

# --- ビュー2: 現在マップ ---
tr_dom_current = make_scatter(domestic, COLOR_DOMESTIC, "国内スタジオ", "size_current_num")
traces.append(tr_dom_current)
trace_point_maps[len(traces) - 1] = build_point_map(domestic, "original_score", "size_current_num")
visibility_map["current"].append(len(traces) - 1)

tr_intl_current = make_scatter(international, COLOR_INTERNATIONAL, "海外スタジオ", "size_current_num")
traces.append(tr_intl_current)
trace_point_maps[len(traces) - 1] = build_point_map(international, "original_score", "size_current_num")
visibility_map["current"].append(len(traces) - 1)

# --- ビュー3: 成長軌跡マップ ---
growth_dom = [s for s in growth_studios if s["region"] == "domestic"]
growth_intl = [s for s in growth_studios if s["region"] == "international"]

# 始点マーカー（設立時）
tr_growth_start_dom = make_scatter(growth_dom, COLOR_DOMESTIC, "国内（設立時）",
                                   "size_founded_num", opacity=0.4, marker_size=MARKER_SIZE_SMALL, show_labels=True,
                                   x_key="original_score_founded")
tr_growth_start_dom.textfont = dict(size=9, color="rgba(52,152,219,0.6)")
growth_dom_merged = merge_overlapping(growth_dom, "original_score_founded", "size_founded_num")
tr_growth_start_dom.text = [
    "<br>".join(f"({p['founded']})" for p in s["_hover_parts"]) if "_hover_parts" in s
    else f"({s['founded']})"
    for s in growth_dom_merged
]
traces.append(tr_growth_start_dom)
trace_point_maps[len(traces) - 1] = build_point_map(growth_dom, "original_score_founded", "size_founded_num")
visibility_map["growth"].append(len(traces) - 1)

tr_growth_start_intl = make_scatter(growth_intl, COLOR_INTERNATIONAL, "海外（設立時）",
                                    "size_founded_num", opacity=0.4, marker_size=MARKER_SIZE_SMALL, show_labels=True,
                                    x_key="original_score_founded")
tr_growth_start_intl.textfont = dict(size=9, color="rgba(231,76,60,0.6)")
growth_intl_merged = merge_overlapping(growth_intl, "original_score_founded", "size_founded_num")
tr_growth_start_intl.text = [
    "<br>".join(f"({p['founded']})" for p in s["_hover_parts"]) if "_hover_parts" in s
    else f"({s['founded']})"
    for s in growth_intl_merged
]
traces.append(tr_growth_start_intl)
trace_point_maps[len(traces) - 1] = build_point_map(growth_intl, "original_score_founded", "size_founded_num")
visibility_map["growth"].append(len(traces) - 1)

# 終点マーカー（現在）
tr_growth_end_dom = make_scatter(growth_dom, COLOR_DOMESTIC, "国内（現在）", "size_current_num")
traces.append(tr_growth_end_dom)
trace_point_maps[len(traces) - 1] = build_point_map(growth_dom, "original_score", "size_current_num")
visibility_map["growth"].append(len(traces) - 1)

tr_growth_end_intl = make_scatter(growth_intl, COLOR_INTERNATIONAL, "海外（現在）", "size_current_num")
traces.append(tr_growth_end_intl)
trace_point_maps[len(traces) - 1] = build_point_map(growth_intl, "original_score", "size_current_num")
visibility_map["growth"].append(len(traces) - 1)

# 軌跡線トレース（グラデーション付き）
visibility_map["growth_lines"] = []
growth_line_studio_indices = {}

growth_dom_global = [studio_global_idx[id(s)] for s in growth_dom]
for tr in make_growth_line_traces(growth_dom, COLOR_DOMESTIC, "国内"):
    traces.append(tr)
    visibility_map["growth"].append(len(traces) - 1)
    visibility_map["growth_lines"].append(len(traces) - 1)
    growth_line_studio_indices[len(traces) - 1] = growth_dom_global

growth_intl_global = [studio_global_idx[id(s)] for s in growth_intl]
for tr in make_growth_line_traces(growth_intl, COLOR_INTERNATIONAL, "海外"):
    traces.append(tr)
    visibility_map["growth"].append(len(traces) - 1)
    visibility_map["growth_lines"].append(len(traces) - 1)
    growth_line_studio_indices[len(traces) - 1] = growth_intl_global


# --- ビュー4: ビジネスモデル分析マップ ---
# X: original_score, Y: ip_ownership_score, Size: size_current_num, Color: business_model
visibility_map["business_model"] = []
bm_studios = [s for s in studios if s.get("ip_ownership_score") is not None]
for tr in make_categorical_scatter(
    bm_studios, "business_model",
    COLOR_PALETTES["business_model"],
    LABEL_NAMES["business_model"],
    x_key="original_score",
    y_key="ip_ownership_score",
    size_field="size_current_num",
):
    traces.append(tr)
    trace_point_maps[len(traces) - 1] = build_point_map(
        [s for s in bm_studios if s.get("business_model") == tr.name.replace("", "")],
        "original_score", "ip_ownership_score"
    )
    visibility_map["business_model"].append(len(traces) - 1)

# build_point_map for view 4 needs to be recalculated per group
# Rebuild properly
_bm_trace_start = len(traces) - len(visibility_map["business_model"])
for i, view_idx in enumerate(visibility_map["business_model"]):
    # Extract category from trace name
    tr = traces[view_idx]
    cat_label = tr.name
    # Find matching studios
    cat_key = None
    for k, v in LABEL_NAMES["business_model"].items():
        if v == cat_label:
            cat_key = k
            break
    if cat_key:
        cat_studios = [s for s in bm_studios if s.get("business_model") == cat_key]
        trace_point_maps[view_idx] = build_point_map(cat_studios, "original_score", "ip_ownership_score")


# --- ビュー5: AI活用度マップ ---
# X: original_score, Y: size_current_num, Color: ai_adoption_level
visibility_map["ai_adoption"] = []
# シンボル: region別
ai_symbol_map = {"domestic": "circle", "international": "diamond"}
for region_key, region_studios, region_label in [
    ("domestic", domestic, "国内"),
    ("international", international, "海外")
]:
    symbol = ai_symbol_map[region_key]
    for ai_level in ["none", "experimental", "production", "core"]:
        level_studios = [s for s in region_studios if s.get("ai_adoption_level") == ai_level]
        if not level_studios:
            continue
        color = COLOR_PALETTES["ai_adoption_level"][ai_level]
        ai_label = LABEL_NAMES["ai_adoption_level"][ai_level]
        legend_name = f"{region_label} - {ai_label}"

        merged = merge_overlapping(level_studios, "original_score", "size_current_num")
        text_positions = resolve_label_positions(merged, "size_current_num", "original_score")

        hover_texts = []
        for s in merged:
            if "_hover_parts" in s:
                hover_texts.append("<br>───────────<br>".join(hover_text(part, "size_current_num") for part in s["_hover_parts"]))
            else:
                hover_texts.append(hover_text(s, "size_current_num"))

        tr = go.Scatter(
            x=[s.get("original_score", 0) for s in merged],
            y=[s.get("size_current_num", 10) or 10 for s in merged],
            mode="markers+text",
            marker=dict(
                size=MARKER_SIZE,
                color=color,
                opacity=1.0,
                line=dict(width=1, color="white"),
                symbol=symbol,
            ),
            text=[s["name"] for s in merged],
            textposition=text_positions,
            textfont=dict(size=9, color=color),
            hovertext=hover_texts,
            hoverinfo="text",
            name=legend_name,
        )
        traces.append(tr)
        trace_point_maps[len(traces) - 1] = build_point_map(level_studios, "original_score", "size_current_num")
        visibility_map["ai_adoption"].append(len(traces) - 1)


# --- ビュー6: 収益・規模マップ ---
# X: operating_margin, Y: revenue_billion_yen, Size: size_current_num
# Color: licensing_ratio (continuous)
visibility_map["revenue"] = []
revenue_studios = [s for s in studios if s.get("revenue_billion_yen") is not None]

if revenue_studios:
    merged_rev = merge_overlapping(revenue_studios, "operating_margin", "revenue_billion_yen")
    text_positions_rev = resolve_label_positions(merged_rev, "revenue_billion_yen", "operating_margin")

    hover_texts_rev = []
    for s in merged_rev:
        if "_hover_parts" in s:
            hover_texts_rev.append("<br>───────────<br>".join(hover_text(part, "revenue_billion_yen") for part in s["_hover_parts"]))
        else:
            hover_texts_rev.append(hover_text(s, "revenue_billion_yen"))

    # 色: licensing_ratio → 連続スケール
    colors_rev = []
    for s in merged_rev:
        lic = s.get("licensing_ratio")
        if lic is not None:
            colors_rev.append(lic)
        else:
            colors_rev.append(0)

    sizes_rev = []
    for s in merged_rev:
        val = s.get("size_current_num", 100)
        if val and val > 0:
            sizes_rev.append(max(8, min(35, 8 + 10 * math.log10(val))))
        else:
            sizes_rev.append(10)

    tr_rev = go.Scatter(
        x=[s.get("operating_margin", 0) or 0 for s in merged_rev],
        y=[s.get("revenue_billion_yen", 1) or 1 for s in merged_rev],
        mode="markers+text",
        marker=dict(
            size=sizes_rev,
            color=colors_rev,
            colorscale=[[0, "#E74C3C"], [0.5, "#F39C12"], [1, "#27AE60"]],
            cmin=0, cmax=1,
            colorbar=dict(title="版権収入比率", x=1.02, len=0.5),
            opacity=1.0,
            line=dict(width=1, color="white"),
        ),
        text=[s["name"] for s in merged_rev],
        textposition=text_positions_rev,
        textfont=dict(size=9),
        hovertext=hover_texts_rev,
        hoverinfo="text",
        name="収益データ公開企業",
    )
    traces.append(tr_rev)
    trace_point_maps[len(traces) - 1] = build_point_map(revenue_studios, "operating_margin", "revenue_billion_yen")
    visibility_map["revenue"].append(len(traces) - 1)


# --- ビュー7: 所有構造・企業グループマップ ---
# X: original_score, Y: size_current_num, Color: ownership_type
visibility_map["ownership"] = []
for tr in make_categorical_scatter(
    studios, "ownership_type",
    COLOR_PALETTES["ownership_type"],
    LABEL_NAMES["ownership_type"],
    x_key="original_score",
    y_key="size_current_num",
):
    traces.append(tr)
    cat_label = tr.name
    cat_key = None
    for k, v in LABEL_NAMES["ownership_type"].items():
        if v == cat_label:
            cat_key = k
            break
    if cat_key:
        cat_studios = [s for s in studios if s.get("ownership_type") == cat_key]
        trace_point_maps[len(traces) - 1] = build_point_map(cat_studios, "original_score", "size_current_num")
    visibility_map["ownership"].append(len(traces) - 1)


# --- ビュー8: 配信PF関係マップ ---
# X: original_score, Y: size_current_num, Color: primary_platform top
visibility_map["platform"] = []
pf_groups = {}
for s in studios:
    pf = get_primary_platform(s)
    pf_groups.setdefault(pf, []).append(s)

for pf_name, pf_studios in pf_groups.items():
    color = COLOR_PALETTES["primary_platform_color"].get(pf_name, "#95A5A6")
    merged = merge_overlapping(pf_studios, "original_score", "size_current_num")
    text_positions = resolve_label_positions(merged, "size_current_num", "original_score")

    hover_texts = []
    for s in merged:
        if "_hover_parts" in s:
            hover_texts.append("<br>───────────<br>".join(hover_text(part, "size_current_num") for part in s["_hover_parts"]))
        else:
            hover_texts.append(hover_text(s, "size_current_num"))

    tr = go.Scatter(
        x=[s.get("original_score", 0) for s in merged],
        y=[s.get("size_current_num", 10) or 10 for s in merged],
        mode="markers+text",
        marker=dict(
            size=MARKER_SIZE,
            color=color,
            opacity=1.0,
            line=dict(width=1, color="white"),
            symbol="circle",
        ),
        text=[s["name"] for s in merged],
        textposition=text_positions,
        textfont=dict(size=9, color=color),
        hovertext=hover_texts,
        hoverinfo="text",
        name=pf_name,
    )
    traces.append(tr)
    trace_point_maps[len(traces) - 1] = build_point_map(pf_studios, "original_score", "size_current_num")
    visibility_map["platform"].append(len(traces) - 1)


# --- ビュー9: 設立年・黒字化分析マップ ---
# X: founded, Y: size_current_num
visibility_map["profitability"] = []

# 黒字化データありスタジオ
prof_studios = [s for s in studios if s.get("years_to_profitability") is not None]
# 黒字化データなしスタジオ
nonprof_studios = [s for s in studios if s.get("years_to_profitability") is None]

if nonprof_studios:
    merged_np = merge_overlapping(nonprof_studios, "founded", "size_current_num")
    text_positions_np = resolve_label_positions(merged_np, "size_current_num", "founded")
    hover_texts_np = []
    for s in merged_np:
        if "_hover_parts" in s:
            hover_texts_np.append("<br>───────────<br>".join(hover_text(part, "size_current_num") for part in s["_hover_parts"]))
        else:
            hover_texts_np.append(hover_text(s, "size_current_num"))

    tr_np = go.Scatter(
        x=[s.get("founded", 2000) for s in merged_np],
        y=[s.get("size_current_num", 10) or 10 for s in merged_np],
        mode="markers+text",
        marker=dict(
            size=MARKER_SIZE,
            color="#BDBDBD",
            opacity=0.5,
            line=dict(width=1, color="white"),
        ),
        text=[s["name"] for s in merged_np],
        textposition=text_positions_np,
        textfont=dict(size=8, color="#999"),
        hovertext=hover_texts_np,
        hoverinfo="text",
        name="黒字化データなし",
    )
    traces.append(tr_np)
    trace_point_maps[len(traces) - 1] = build_point_map(nonprof_studios, "founded", "size_current_num")
    visibility_map["profitability"].append(len(traces) - 1)

if prof_studios:
    merged_p = merge_overlapping(prof_studios, "founded", "size_current_num")
    text_positions_p = resolve_label_positions(merged_p, "size_current_num", "founded")
    hover_texts_p = []
    texts_p = []
    for s in merged_p:
        if "_hover_parts" in s:
            hover_texts_p.append("<br>───────────<br>".join(hover_text(part, "size_current_num") for part in s["_hover_parts"]))
            texts_p.append("<br>".join(f"{p['name']} ({p.get('years_to_profitability','?')}年)" for p in s["_hover_parts"]))
        else:
            hover_texts_p.append(hover_text(s, "size_current_num"))
            ytp = s.get("years_to_profitability", "?")
            texts_p.append(f"{s['name']} ({ytp}年)")

    tr_p = go.Scatter(
        x=[s.get("founded", 2000) for s in merged_p],
        y=[s.get("size_current_num", 10) or 10 for s in merged_p],
        mode="markers+text",
        marker=dict(
            size=14,
            color="#4CAF50",
            opacity=1.0,
            line=dict(width=2, color="#2E7D32"),
            symbol="star",
        ),
        text=texts_p,
        textposition=text_positions_p,
        textfont=dict(size=9, color="#2E7D32"),
        hovertext=hover_texts_p,
        hoverinfo="text",
        name="黒字化データあり",
    )
    traces.append(tr_p)
    trace_point_maps[len(traces) - 1] = build_point_map(prof_studios, "founded", "size_current_num")
    visibility_map["profitability"].append(len(traces) - 1)


# ==================================================================
# ボタンで9ビュー切替
# ==================================================================
total_traces = len(traces)

# ビューキー一覧（growth_linesは除外）
VIEW_KEYS = ["founded", "current", "growth", "business_model", "ai_adoption",
             "revenue", "ownership", "platform", "profitability"]


def make_visibility(view_key):
    vis = [False] * total_traces
    for idx in visibility_map[view_key]:
        vis[idx] = True
    return vis


titles = {
    "founded": "設立時マップ — 全29社を設立時の規模でプロット",
    "current": "現在マップ — 全29社を現在の規模でプロット",
    "growth": "成長軌跡マップ — 設立時→現在",
    "business_model": "ビジネスモデル分析 — オリジナルスコア × IP保有率",
    "ai_adoption": "AI活用度マップ — オリジナルスコア × 人数規模",
    "revenue": "収益・規模マップ — 営業利益率 × 売上高（上場企業等の公開データのみ）",
    "ownership": "所有構造マップ — オリジナルスコア × 人数規模",
    "platform": "配信PF関係マップ — オリジナルスコア × 人数規模",
    "profitability": "設立年・黒字化分析 — 設立年 × 現在規模",
}

# 軸設定
axis_configs = {
    "founded": {
        "xaxis.title.text": "← 受託          オリジナル →",
        "xaxis.range": AXIS_RANGE_X,
        "xaxis.dtick": 0.1,
        "xaxis.tickformat": ".1f",
        "yaxis.title.text": "人数規模（人）",
        "yaxis.type": "log",
        "yaxis.range": AXIS_RANGE_Y_LOG,
        "yaxis.dtick": None,
        "yaxis.tickformat": ",d",
    },
    "current": {
        "xaxis.title.text": "← 受託          オリジナル →",
        "xaxis.range": AXIS_RANGE_X,
        "xaxis.dtick": 0.1,
        "xaxis.tickformat": ".1f",
        "yaxis.title.text": "人数規模（人）",
        "yaxis.type": "log",
        "yaxis.range": AXIS_RANGE_Y_LOG,
        "yaxis.dtick": None,
        "yaxis.tickformat": ",d",
    },
    "growth": {
        "xaxis.title.text": "← 受託          オリジナル →",
        "xaxis.range": AXIS_RANGE_X,
        "xaxis.dtick": 0.1,
        "xaxis.tickformat": ".1f",
        "yaxis.title.text": "人数規模（人）",
        "yaxis.type": "log",
        "yaxis.range": AXIS_RANGE_Y_LOG,
        "yaxis.dtick": None,
        "yaxis.tickformat": ",d",
    },
    "business_model": {
        "xaxis.title.text": "← 受託          オリジナル →",
        "xaxis.range": AXIS_RANGE_X,
        "xaxis.dtick": 0.1,
        "xaxis.tickformat": ".1f",
        "yaxis.title.text": "IP保有率スコア",
        "yaxis.type": "linear",
        "yaxis.range": [-0.05, 1.05],
        "yaxis.dtick": 0.1,
        "yaxis.tickformat": ".1f",
    },
    "ai_adoption": {
        "xaxis.title.text": "← 受託          オリジナル →",
        "xaxis.range": AXIS_RANGE_X,
        "xaxis.dtick": 0.1,
        "xaxis.tickformat": ".1f",
        "yaxis.title.text": "人数規模（人）",
        "yaxis.type": "log",
        "yaxis.range": AXIS_RANGE_Y_LOG,
        "yaxis.dtick": None,
        "yaxis.tickformat": ",d",
    },
    "revenue": {
        "xaxis.title.text": "営業利益率",
        "xaxis.range": [-0.05, 0.40],
        "xaxis.dtick": 0.05,
        "xaxis.tickformat": ".0%",
        "yaxis.title.text": "売上高（億円）",
        "yaxis.type": "log",
        "yaxis.range": [1.0, 3.5],
        "yaxis.dtick": None,
        "yaxis.tickformat": ",d",
    },
    "ownership": {
        "xaxis.title.text": "← 受託          オリジナル →",
        "xaxis.range": AXIS_RANGE_X,
        "xaxis.dtick": 0.1,
        "xaxis.tickformat": ".1f",
        "yaxis.title.text": "人数規模（人）",
        "yaxis.type": "log",
        "yaxis.range": AXIS_RANGE_Y_LOG,
        "yaxis.dtick": None,
        "yaxis.tickformat": ",d",
    },
    "platform": {
        "xaxis.title.text": "← 受託          オリジナル →",
        "xaxis.range": AXIS_RANGE_X,
        "xaxis.dtick": 0.1,
        "xaxis.tickformat": ".1f",
        "yaxis.title.text": "人数規模（人）",
        "yaxis.type": "log",
        "yaxis.range": AXIS_RANGE_Y_LOG,
        "yaxis.dtick": None,
        "yaxis.tickformat": ",d",
    },
    "profitability": {
        "xaxis.title.text": "設立年",
        "xaxis.range": [1940, 2025],
        "xaxis.dtick": 10,
        "xaxis.tickformat": "d",
        "yaxis.title.text": "現在の人数規模（人）",
        "yaxis.type": "log",
        "yaxis.range": AXIS_RANGE_Y_LOG,
        "yaxis.dtick": None,
        "yaxis.tickformat": ",d",
    },
}

# M&Aアノテーション（ビュー7用）
ownership_annotations = [
    dict(
        x=0.55, y=51, xref="x", yref="y",
        text="2024: 東宝→SARU買収",
        showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=1,
        arrowcolor="#666", ax=40, ay=-30,
        font=dict(size=10, color="#666"),
        bgcolor="rgba(255,255,255,0.8)",
    ),
]

# ビュー6用アノテーション
revenue_annotations = [
    dict(
        x=0.5, y=1.07, xref="paper", yref="paper",
        text="* 上場企業等の公開データのみ表示。マーカーサイズは社員数、色は版権収入比率",
        showarrow=False,
        font=dict(size=10, color="#999"),
    ),
]


# ボタン作成
buttons_row1 = []
buttons_row2 = []

button_configs = [
    ("founded", "1. 設立時"),
    ("current", "2. 現在"),
    ("growth", "3. 成長軌跡"),
    ("business_model", "4. ビジネスモデル"),
    ("ai_adoption", "5. AI活用度"),
    ("revenue", "6. 収益・規模"),
    ("ownership", "7. 所有構造"),
    ("platform", "8. 配信PF"),
    ("profitability", "9. 黒字化"),
]

for i, (view_key, label) in enumerate(button_configs):
    ac = axis_configs[view_key]
    annotations = []
    if view_key == "ownership":
        annotations = ownership_annotations
    elif view_key == "revenue":
        annotations = revenue_annotations

    btn = dict(
        label=f"  {label}  ",
        method="update",
        args=[
            {"visible": make_visibility(view_key)},
            dict(
                **{"title.text": titles[view_key], "annotations": annotations},
                **ac,
            ),
        ],
    )
    if i < 5:
        buttons_row1.append(btn)
    else:
        buttons_row2.append(btn)


# ==================================================================
# 図の作成
# ==================================================================
fig = go.Figure(data=traces)

# 初期状態: ビュー1（設立時マップ）
initial_vis = make_visibility("founded")
for i, tr in enumerate(fig.data):
    tr.visible = initial_vis[i]

fig.update_layout(
    **make_layout(titles["founded"]),
    updatemenus=[
        dict(
            type="buttons",
            direction="right",
            x=0.5, xanchor="center",
            y=1.17,
            showactive=True,
            buttons=buttons_row1,
            bgcolor="#f8f8f8",
            bordercolor="#999",
            font=dict(size=12),
            pad=dict(t=3, b=3, l=6, r=6),
        ),
        dict(
            type="buttons",
            direction="right",
            x=0.5, xanchor="center",
            y=1.09,
            showactive=True,
            buttons=buttons_row2,
            bgcolor="#f0f0f0",
            bordercolor="#999",
            font=dict(size=12),
            pad=dict(t=3, b=3, l=6, r=6),
        ),
    ],
)

# --- フィルタ用JSデータ生成 ---
studios_js = json.dumps([{
    "idx": i,
    "name": s["name"],
    "name_en": s.get("name_en", ""),
    "region": s["region"],
    "founded": s.get("founded"),
    "size_founded_num": s.get("size_founded_num") or 10,
    "size_current_num": s.get("size_current_num"),
    "notable_works": s.get("notable_works", []),
    "parent_company": s.get("parent_company"),
    "ownership_type": s.get("ownership_type"),
    "business_model": s.get("business_model"),
    "ai_adoption_level": s.get("ai_adoption_level"),
    "ai_adoption_detail": s.get("ai_adoption_detail"),
    "primary_platform": s.get("primary_platform", []),
    "ip_ownership_score": s.get("ip_ownership_score"),
    "revenue_billion_yen": s.get("revenue_billion_yen"),
    "operating_margin": s.get("operating_margin"),
    "years_to_profitability": s.get("years_to_profitability"),
} for i, s in enumerate(studios)], ensure_ascii=False)

trace_point_maps_js = json.dumps({str(k): v for k, v in trace_point_maps.items()})
growth_line_studio_js = json.dumps({str(k): v for k, v in growth_line_studio_indices.items()})
visibility_map_js = json.dumps(visibility_map)

# --- 出力 ---
chart_div = fig.to_html(
    include_plotlyjs="cdn",
    full_html=False,
    config={"displayModeBar": True, "scrollZoom": True},
)

full_html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>アニメスタジオ ポジショニングマップ</title>
<style>
  body {{ margin: 0; padding: 0; font-family: sans-serif; }}
  .controls-bar {{
    display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
    padding: 8px 16px; background: #f5f5f5;
    border-bottom: 1px solid #ddd; font-size: 13px; color: #555;
  }}
  .controls-bar input[type="number"] {{
    width: 70px; padding: 4px 8px; border: 1px solid #ccc;
    border-radius: 4px; font-size: 13px; text-align: right;
  }}
  .controls-bar button {{
    padding: 4px 14px; border: 1px solid #999; border-radius: 4px;
    background: #fff; cursor: pointer; font-size: 13px;
  }}
  .controls-bar button:hover {{ background: #e8e8e8; }}
  .controls-bar .toggle-btn {{
    padding: 4px 14px; border: 1px solid #999; border-radius: 4px;
    cursor: pointer; font-size: 13px;
  }}
  .controls-bar .toggle-btn.on {{ background: #d0e8ff; border-color: #69a; }}
  .controls-bar .toggle-btn.off {{ background: #f0f0f0; color: #999; }}
  .sep {{ border-left: 1px solid #ccc; height: 20px; margin: 0 4px; }}
  .filter-bar {{
    display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
    padding: 8px 16px; background: #fafafa;
    border-bottom: 1px solid #ddd; font-size: 13px; color: #555;
  }}
  .filter-bar label {{ white-space: nowrap; }}
  .filter-bar input[type="number"] {{
    width: 60px; padding: 3px 6px; border: 1px solid #ccc;
    border-radius: 4px; font-size: 12px; text-align: right;
  }}
  .filter-bar input[type="text"] {{
    width: 120px; padding: 3px 6px; border: 1px solid #ccc;
    border-radius: 4px; font-size: 12px;
  }}
  .filter-bar input[type="checkbox"] {{ margin: 0 2px 0 0; }}
  .filter-bar button {{
    padding: 3px 12px; border: 1px solid #999; border-radius: 4px;
    background: #fff; cursor: pointer; font-size: 12px;
  }}
  .filter-bar button:hover {{ background: #e8e8e8; }}
  .filter-bar .filter-count {{
    margin-left: auto; font-weight: bold; color: #333;
  }}
  .filter-section {{
    display: inline-flex; align-items: center; gap: 4px;
    padding: 2px 6px; border: 1px solid #e0e0e0; border-radius: 4px;
    background: #f8f8f8;
  }}
  .filter-section-label {{
    font-size: 11px; color: #888; font-weight: bold;
  }}
  .main-content {{
    display: flex; height: calc(100vh - 130px);
  }}
  .chart-area {{
    flex: 1; min-width: 0; overflow: hidden;
  }}
  .chart-area .plotly-graph-div {{
    width: 100% !important;
  }}
  .studio-list-panel {{
    width: 300px; border-left: 1px solid #ddd;
    display: flex; flex-direction: column; flex-shrink: 0;
  }}
  .studio-list-header {{
    padding: 10px 12px; background: #f5f5f5;
    border-bottom: 1px solid #ddd; font-weight: bold; font-size: 13px;
  }}
  .studio-list-body {{
    overflow-y: auto; flex: 1;
  }}
  .studio-item {{
    padding: 8px 12px; border-bottom: 1px solid #eee;
    font-size: 12px; cursor: pointer;
  }}
  .studio-item:hover {{ background: #f0f8ff; }}
  .studio-item.hidden {{ display: none; }}
  .studio-item .name {{ font-weight: bold; }}
  .studio-item .meta {{ color: #888; font-size: 11px; margin-top: 2px; }}
  .studio-item .works {{ color: #666; font-size: 11px; margin-top: 2px; }}
  .studio-item .badges {{ margin-top: 3px; display: flex; gap: 4px; flex-wrap: wrap; }}
  .studio-item .badge {{
    display: inline-block; padding: 1px 6px; border-radius: 3px;
    font-size: 10px; font-weight: bold; color: white;
  }}
  .studio-item .badge-ai-none {{ background: #BDBDBD; }}
  .studio-item .badge-ai-experimental {{ background: #FFC107; color: #333; }}
  .studio-item .badge-ai-production {{ background: #4CAF50; }}
  .studio-item .badge-ai-core {{ background: #FFD700; color: #333; }}
  .studio-item .badge-own-independent {{ background: #27AE60; }}
  .studio-item .badge-own-subsidiary {{ background: #2980B9; }}
  .studio-item .badge-own-group {{ background: #8E44AD; }}
  .studio-item .region-dot {{
    display: inline-block; width: 8px; height: 8px;
    border-radius: 50%; margin-right: 4px; vertical-align: middle;
  }}
</style>
</head>
<body>
<div class="controls-bar">
  <label>Width:</label>
  <input type="number" id="chart-width" value="{CHART_WIDTH}" min="400" step="50">
  <label>Height:</label>
  <input type="number" id="chart-height" value="{CHART_HEIGHT}" min="300" step="50">
  <button onclick="resizeChart()">適用</button>
  <span class="sep"></span>
  <label>Text:</label>
  <input type="number" id="text-size" value="9" min="4" max="24" step="1" style="width:50px;">
  <button onclick="applyTextSize()">適用</button>
  <span class="sep"></span>
  <button id="toggle-lines" class="toggle-btn on" onclick="toggleLines()">軌跡線: ON</button>
  <span class="sep"></span>
  <button id="toggle-yscale" class="toggle-btn on" onclick="toggleYScale()">Y軸: 対数</button>
  <button onclick="resetMapPosition()">位置リセット</button>
</div>
<div class="filter-bar">
  <label>設立年:</label>
  <input type="number" id="filter-year-min" placeholder="min" min="1900" max="2030">
  <span>〜</span>
  <input type="number" id="filter-year-max" placeholder="max" min="1900" max="2030">
  <span class="sep"></span>
  <label><input type="checkbox" id="filter-domestic" checked> 国内</label>
  <label><input type="checkbox" id="filter-international" checked> 海外</label>
  <span class="sep"></span>
  <label>社員数:</label>
  <input type="number" id="filter-size-min" placeholder="min" min="0">
  <span>〜</span>
  <input type="number" id="filter-size-max" placeholder="max" min="0">
  <span class="sep"></span>
  <label>検索:</label>
  <input type="text" id="filter-search" placeholder="名前・作品...">
  <span class="sep"></span>
  <div class="filter-section">
    <span class="filter-section-label">AI:</span>
    <label><input type="checkbox" id="filter-ai-none" checked> なし</label>
    <label><input type="checkbox" id="filter-ai-experimental" checked> 実験的</label>
    <label><input type="checkbox" id="filter-ai-production" checked> 本番</label>
    <label><input type="checkbox" id="filter-ai-core" checked> コア</label>
  </div>
  <span class="sep"></span>
  <div class="filter-section">
    <span class="filter-section-label">所有:</span>
    <label><input type="checkbox" id="filter-own-independent" checked> 独立</label>
    <label><input type="checkbox" id="filter-own-subsidiary" checked> 子会社</label>
    <label><input type="checkbox" id="filter-own-group" checked> グループ</label>
  </div>
  <span class="sep"></span>
  <button onclick="applyFilters()">適用</button>
  <button onclick="resetFilters()">リセット</button>
  <span class="filter-count" id="filter-count">表示: {len(studios)}/{len(studios)}社</span>
</div>
<div class="main-content">
  <div class="chart-area">{chart_div}</div>
  <div class="studio-list-panel">
    <div class="studio-list-header">企業一覧 (<span id="list-count">{len(studios)}</span>社)</div>
    <div class="studio-list-body" id="studio-list-body"></div>
  </div>
</div>
<script>
var AXIS_RANGE_X = {json.dumps(AXIS_RANGE_X)};
var AXIS_RANGE_Y_LINEAR = {json.dumps(AXIS_RANGE_Y_LINEAR)};
var AXIS_RANGE_Y_LOG = {json.dumps(AXIS_RANGE_Y_LOG)};
var isLogScale = true;
var STUDIOS = {studios_js};
var TRACE_POINT_MAP = {trace_point_maps_js};
var GROWTH_LINE_STUDIOS = {growth_line_studio_js};
var VISIBILITY_MAP = {visibility_map_js};
var growthLineIndices = {json.dumps(visibility_map["growth_lines"])};
var linesVisible = true;
var totalStudios = STUDIOS.length;

var AI_LABELS = {json.dumps(LABEL_NAMES["ai_adoption_level"], ensure_ascii=False)};
var OWN_LABELS = {json.dumps(LABEL_NAMES["ownership_type"], ensure_ascii=False)};

// --- 企業リストパネル ---
function buildStudioList() {{
  var container = document.getElementById('studio-list-body');
  if (!container) return;
  var html = '';
  for (var i = 0; i < STUDIOS.length; i++) {{
    var s = STUDIOS[i];
    var dotColor = s.region === 'domestic' ? '{COLOR_DOMESTIC}' : '{COLOR_INTERNATIONAL}';
    var regionLabel = s.region === 'domestic' ? '国内' : '海外';
    var works = s.notable_works.slice(0, 2).join(', ');
    var sizeText = s.size_current_num ? s.size_current_num + '人' : '?人';
    var foundedText = s.founded ? s.founded + '年' : '?年';

    var parentText = s.parent_company ? ' | ' + s.parent_company : '';

    // AI バッジ
    var aiLevel = s.ai_adoption_level || 'none';
    var aiBadgeClass = 'badge-ai-' + aiLevel;
    var aiLabel = AI_LABELS[aiLevel] || aiLevel;

    // 所有形態バッジ
    var ownType = s.ownership_type || 'independent';
    var ownBadgeClass = 'badge-own-' + (ownType === 'group_company' ? 'group' : ownType);
    var ownLabel = OWN_LABELS[ownType] || ownType;

    html += '<div class="studio-item" data-idx="' + i + '">'
      + '<div class="name"><span class="region-dot" style="background:' + dotColor + '"></span>' + s.name + '</div>'
      + '<div class="meta">' + regionLabel + ' | ' + foundedText + ' | ' + sizeText + parentText + '</div>'
      + '<div class="badges">'
      + '<span class="badge ' + aiBadgeClass + '">AI: ' + aiLabel + '</span>'
      + '<span class="badge ' + ownBadgeClass + '">' + ownLabel + '</span>'
      + '</div>'
      + (works ? '<div class="works">' + works + '</div>' : '')
      + '</div>';
  }}
  container.innerHTML = html;
}}

function updateStudioList(matchResults) {{
  var items = document.querySelectorAll('.studio-item');
  var visibleCount = 0;
  for (var i = 0; i < items.length; i++) {{
    var idx = parseInt(items[i].getAttribute('data-idx'));
    if (matchResults[idx]) {{
      items[i].classList.remove('hidden');
      visibleCount++;
    }} else {{
      items[i].classList.add('hidden');
    }}
  }}
  document.getElementById('list-count').textContent = visibleCount;
}}

// 元データ保存用
var _originalData = {{}};

function initOriginalData() {{
  var plotDiv = document.querySelector('.plotly-graph-div');
  if (!plotDiv) return;
  for (var i = 0; i < plotDiv.data.length; i++) {{
    var d = plotDiv.data[i];
    _originalData[i] = {{
      x: d.x ? d.x.slice() : null,
      y: d.y ? d.y.slice() : null,
      hovertext: d.hovertext ? d.hovertext.slice() : null,
      text: d.text ? d.text.slice() : null,
      marker_opacity: d.marker ? (Array.isArray(d.marker.opacity) ? d.marker.opacity.slice() : d.marker.opacity) : null,
      textfont_color: d.textfont ? (Array.isArray(d.textfont.color) ? d.textfont.color.slice() : d.textfont.color) : null,
    }};
  }}
}}

function getCurrentView() {{
  var plotDiv = document.querySelector('.plotly-graph-div');
  if (!plotDiv) return 'founded';
  for (var i = 0; i < plotDiv.data.length; i++) {{
    if (plotDiv.data[i].visible === true) {{
      for (var view in VISIBILITY_MAP) {{
        if (view === 'growth_lines') continue;
        if (VISIBILITY_MAP[view].indexOf(i) !== -1) return view;
      }}
    }}
  }}
  return 'founded';
}}

function studioMatchesFilter(studio) {{
  var yearMin = document.getElementById('filter-year-min').value;
  var yearMax = document.getElementById('filter-year-max').value;
  var showDom = document.getElementById('filter-domestic').checked;
  var showIntl = document.getElementById('filter-international').checked;
  var sizeMin = document.getElementById('filter-size-min').value;
  var sizeMax = document.getElementById('filter-size-max').value;
  var searchText = document.getElementById('filter-search').value.toLowerCase().trim();

  // 地域フィルタ
  if (studio.region === 'domestic' && !showDom) return false;
  if (studio.region === 'international' && !showIntl) return false;

  // 設立年フィルタ
  if (yearMin && studio.founded && studio.founded < parseInt(yearMin)) return false;
  if (yearMax && studio.founded && studio.founded > parseInt(yearMax)) return false;

  // 社員数フィルタ
  var view = getCurrentView();
  var sizeVal = (view === 'founded') ? studio.size_founded_num : studio.size_current_num;
  if (sizeMin && sizeVal < parseInt(sizeMin)) return false;
  if (sizeMax && sizeVal > parseInt(sizeMax)) return false;

  // 文字列検索
  if (searchText) {{
    var haystack = (studio.name + ' ' + studio.name_en + ' ' + studio.notable_works.join(' ')).toLowerCase();
    if (haystack.indexOf(searchText) === -1) return false;
  }}

  // AI活用レベルフィルタ
  var aiLevel = studio.ai_adoption_level || 'none';
  var aiNone = document.getElementById('filter-ai-none').checked;
  var aiExp = document.getElementById('filter-ai-experimental').checked;
  var aiProd = document.getElementById('filter-ai-production').checked;
  var aiCore = document.getElementById('filter-ai-core').checked;
  if (aiLevel === 'none' && !aiNone) return false;
  if (aiLevel === 'experimental' && !aiExp) return false;
  if (aiLevel === 'production' && !aiProd) return false;
  if (aiLevel === 'core' && !aiCore) return false;

  // 所有形態フィルタ
  var ownType = studio.ownership_type || 'independent';
  var ownIndep = document.getElementById('filter-own-independent').checked;
  var ownSub = document.getElementById('filter-own-subsidiary').checked;
  var ownGroup = document.getElementById('filter-own-group').checked;
  if (ownType === 'independent' && !ownIndep) return false;
  if (ownType === 'subsidiary' && !ownSub) return false;
  if (ownType === 'group_company' && !ownGroup) return false;

  return true;
}}

function applyFilters() {{
  var plotDiv = document.querySelector('.plotly-graph-div');
  if (!plotDiv) return;

  var matchResults = STUDIOS.map(function(s) {{ return studioMatchesFilter(s); }});
  var matchCount = matchResults.filter(function(m) {{ return m; }}).length;
  document.getElementById('filter-count').textContent = '表示: ' + matchCount + '/' + totalStudios + '社';

  updateStudioList(matchResults);

  // スキャッタートレースのフィルタ適用
  for (var trIdx in TRACE_POINT_MAP) {{
    var ti = parseInt(trIdx);
    var pointMap = TRACE_POINT_MAP[trIdx];
    var orig = _originalData[ti];
    if (!orig || !orig.x) continue;

    var newOpacity = [];
    var newTextColor = [];
    var newHovertext = [];
    var baseTextColor = orig.textfont_color;
    var baseOpacity = orig.marker_opacity;

    for (var pi = 0; pi < pointMap.length; pi++) {{
      var studioIndices = pointMap[pi];
      var anyMatch = studioIndices.some(function(si) {{ return matchResults[si]; }});

      if (anyMatch) {{
        newOpacity.push(typeof baseOpacity === 'number' ? baseOpacity : (baseOpacity ? baseOpacity[pi] : 1));
        newTextColor.push(typeof baseTextColor === 'string' ? baseTextColor : (baseTextColor ? baseTextColor[pi] : '#000'));
        if (studioIndices.length > 1 && orig.hovertext) {{
          var parts = orig.hovertext[pi].split('<br>───────────<br>');
          var filtered = [];
          for (var si = 0; si < studioIndices.length; si++) {{
            if (matchResults[studioIndices[si]] && parts[si]) {{
              filtered.push(parts[si]);
            }}
          }}
          newHovertext.push(filtered.join('<br>───────────<br>'));
        }} else {{
          newHovertext.push(orig.hovertext ? orig.hovertext[pi] : '');
        }}
      }} else {{
        newOpacity.push(0);
        newTextColor.push('rgba(0,0,0,0)');
        newHovertext.push('');
      }}
    }}

    Plotly.restyle(plotDiv, {{
      'marker.opacity': [newOpacity],
      'textfont.color': [newTextColor],
      'hovertext': [newHovertext],
    }}, [ti]);
  }}

  // 成長軌跡線のフィルタ適用
  for (var glIdx in GROWTH_LINE_STUDIOS) {{
    var gli = parseInt(glIdx);
    var studioList = GROWTH_LINE_STUDIOS[glIdx];
    var orig = _originalData[gli];
    if (!orig || !orig.x) continue;

    var newX = orig.x.slice();
    var newY = orig.y.slice();

    for (var si = 0; si < studioList.length; si++) {{
      if (!matchResults[studioList[si]]) {{
        newX[si * 3] = null;
        newX[si * 3 + 1] = null;
        newY[si * 3] = null;
        newY[si * 3 + 1] = null;
      }}
    }}

    Plotly.restyle(plotDiv, {{
      x: [newX],
      y: [newY],
    }}, [gli]);
  }}
}}

function resetFilters() {{
  document.getElementById('filter-year-min').value = '';
  document.getElementById('filter-year-max').value = '';
  document.getElementById('filter-domestic').checked = true;
  document.getElementById('filter-international').checked = true;
  document.getElementById('filter-size-min').value = '';
  document.getElementById('filter-size-max').value = '';
  document.getElementById('filter-search').value = '';
  document.getElementById('filter-ai-none').checked = true;
  document.getElementById('filter-ai-experimental').checked = true;
  document.getElementById('filter-ai-production').checked = true;
  document.getElementById('filter-ai-core').checked = true;
  document.getElementById('filter-own-independent').checked = true;
  document.getElementById('filter-own-subsidiary').checked = true;
  document.getElementById('filter-own-group').checked = true;

  var plotDiv = document.querySelector('.plotly-graph-div');
  if (!plotDiv) return;

  for (var trIdx in TRACE_POINT_MAP) {{
    var ti = parseInt(trIdx);
    var orig = _originalData[ti];
    if (!orig) continue;
    var baseOpacity = orig.marker_opacity;
    var opArr = [];
    if (typeof baseOpacity === 'number') {{
      for (var p = 0; p < orig.x.length; p++) opArr.push(baseOpacity);
    }} else if (Array.isArray(baseOpacity)) {{
      opArr = baseOpacity.slice();
    }}
    Plotly.restyle(plotDiv, {{
      'marker.opacity': [opArr.length > 0 ? opArr : orig.marker_opacity],
      'textfont.color': [orig.textfont_color],
      'hovertext': [orig.hovertext],
    }}, [ti]);
  }}

  for (var glIdx in GROWTH_LINE_STUDIOS) {{
    var gli = parseInt(glIdx);
    var orig = _originalData[gli];
    if (!orig) continue;
    Plotly.restyle(plotDiv, {{
      x: [orig.x],
      y: [orig.y],
    }}, [gli]);
  }}

  document.getElementById('filter-count').textContent = '表示: ' + totalStudios + '/' + totalStudios + '社';

  var allItems = document.querySelectorAll('.studio-item');
  for (var ai = 0; ai < allItems.length; ai++) {{ allItems[ai].classList.remove('hidden'); }}
  document.getElementById('list-count').textContent = totalStudios;
}}

function resizeChart() {{
  var w = parseInt(document.getElementById('chart-width').value);
  var h = parseInt(document.getElementById('chart-height').value);
  var plotDiv = document.querySelector('.plotly-graph-div');
  if (plotDiv && w >= 400 && h >= 300) {{
    Plotly.relayout(plotDiv, {{ width: w, height: h }});
  }}
}}

function applyTextSize() {{
  var size = parseInt(document.getElementById('text-size').value);
  if (isNaN(size) || size < 4 || size > 24) return;
  var plotDiv = document.querySelector('.plotly-graph-div');
  if (!plotDiv) return;
  var indices = [];
  for (var i = 0; i < plotDiv.data.length; i++) {{
    if (plotDiv.data[i].mode && plotDiv.data[i].mode.indexOf('text') !== -1) {{
      indices.push(i);
    }}
  }}
  if (indices.length > 0) {{
    Plotly.restyle(plotDiv, {{ 'textfont.size': size }}, indices);
  }}
}}

function toggleLines() {{
  var plotDiv = document.querySelector('.plotly-graph-div');
  if (!plotDiv) return;
  linesVisible = !linesVisible;
  var vis = linesVisible ? true : false;
  Plotly.restyle(plotDiv, {{ visible: vis }}, growthLineIndices);
  var btn = document.getElementById('toggle-lines');
  btn.textContent = linesVisible ? '軌跡線: ON' : '軌跡線: OFF';
  btn.className = 'toggle-btn ' + (linesVisible ? 'on' : 'off');
}}

function toggleYScale() {{
  var plotDiv = document.querySelector('.plotly-graph-div');
  if (!plotDiv) return;
  isLogScale = !isLogScale;
  Plotly.relayout(plotDiv, {{
    'yaxis.type': isLogScale ? 'log' : 'linear',
    'yaxis.range': isLogScale ? AXIS_RANGE_Y_LOG.slice() : AXIS_RANGE_Y_LINEAR.slice(),
    'yaxis.dtick': isLogScale ? null : 500,
  }});
  var btn = document.getElementById('toggle-yscale');
  btn.textContent = isLogScale ? 'Y軸: 対数' : 'Y軸: 線形';
  btn.className = 'toggle-btn ' + (isLogScale ? 'on' : 'off');
}}

function resetMapPosition() {{
  var plotDiv = document.querySelector('.plotly-graph-div');
  if (!plotDiv) return;
  Plotly.relayout(plotDiv, {{
    'xaxis.range': AXIS_RANGE_X.slice(),
    'yaxis.range': isLogScale ? AXIS_RANGE_Y_LOG.slice() : AXIS_RANGE_Y_LINEAR.slice(),
  }});
}}

// --- 近接ポイント同時ホバー表示 ---
var isProximityHover = false;

function setupProximityHover() {{
  var plotDiv = document.querySelector('.plotly-graph-div');
  if (!plotDiv) return;

  plotDiv.on('plotly_hover', function(data) {{
    if (isProximityHover) return;
    var xaxis = plotDiv._fullLayout.xaxis;
    var yaxis = plotDiv._fullLayout.yaxis;
    var hoverPt = data.points[0];
    var hx = xaxis.d2p(hoverPt.x);
    var hy = yaxis.d2p(hoverPt.y);
    var threshold = 50;

    var nearbyPoints = [];
    plotDiv.data.forEach(function(trace, ci) {{
      if (!trace.visible || trace.visible === false) return;
      if (!trace.x || !trace.hovertext) return;
      trace.x.forEach(function(x, pi) {{
        if (x == null) return;
        var px = xaxis.d2p(x);
        var py = yaxis.d2p(trace.y[pi]);
        var dist = Math.sqrt(Math.pow(px - hx, 2) + Math.pow(py - hy, 2));
        if (dist <= threshold) {{
          nearbyPoints.push({{curveNumber: ci, pointNumber: pi}});
        }}
      }});
    }});

    if (nearbyPoints.length > 1) {{
      isProximityHover = true;
      Plotly.Fx.hover(plotDiv, nearbyPoints);
      isProximityHover = false;
    }}
  }});
}}

// ビュー切替時にフィルタ再適用
function setupViewChangeListener() {{
  var plotDiv = document.querySelector('.plotly-graph-div');
  if (!plotDiv) return;
  plotDiv.on('plotly_buttonclicked', function() {{
    setTimeout(function() {{ applyFilters(); }}, 100);
  }});
}}

// 初期化
window.addEventListener('load', function() {{
  setTimeout(function() {{
    buildStudioList();
    initOriginalData();
    setupProximityHover();
    setupViewChangeListener();
  }}, 500);
}});
</script>
</body>
</html>"""

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write(full_html)

print(f"HTML出力完了: {OUTPUT_PATH}")
print(f"トレース数: {total_traces}")
print(f"ビュー数: {len(VIEW_KEYS)}")
