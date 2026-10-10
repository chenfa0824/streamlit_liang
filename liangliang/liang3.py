import streamlit as st
import pandas as pd
import numpy as np
import io
import zipfile
import hashlib
from datetime import datetime
import plotly.graph_objects as go
import plotly.io as pio

st.set_page_config(
    page_title="CSV 批量转 Excel + 应力应变曲线",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============ 全局 CSS 美化 ============
st.markdown(
    """
    <style>
    .stApp { background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%); }
    .block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1400px; }
    h1, h2, h3 { color: #0f172a; letter-spacing: 0.2px; }
    h1 { font-weight: 800; }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #ffffff; border-radius: 14px;
        box-shadow: 0 2px 10px rgba(15, 23, 42, 0.05);
        border: 1px solid #e8edf3; padding: 6px 4px;
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #ffffff 0%, #f4f8ff 100%);
        border: 1px solid #e3ebf6; border-radius: 12px;
        padding: 12px 14px; box-shadow: 0 1px 4px rgba(15, 23, 42, 0.04);
    }
    div[data-testid="stMetricLabel"] { color: #64748b; font-weight: 600; }
    div[data-testid="stMetricValue"] { color: #1d4ed8; font-weight: 700; }

    button[data-baseweb="tab"] {
        font-weight: 600; color: #475569;
        padding-top: 0.6rem; padding-bottom: 0.6rem;
    }
    button[data-baseweb="tab"][aria-selected="true"] { color: #1d4ed8; }
    div[data-baseweb="tab-list"] {
        gap: 6px; background: #ffffff; padding: 6px 8px;
        border-radius: 12px; border: 1px solid #e8edf3;
        box-shadow: 0 1px 4px rgba(15, 23, 42, 0.03);
    }

    div[data-testid="stDownloadButton"] > button {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        color: #ffffff; border: none; border-radius: 10px;
        font-weight: 600; padding: 0.5rem 1rem;
        box-shadow: 0 2px 6px rgba(37, 99, 235, 0.25);
        transition: all 0.15s ease; width: 100%;
    }
    div[data-testid="stDownloadButton"] > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35);
    }

    div[data-testid="stButton"] > button { border-radius: 10px; font-weight: 600; }

    section[data-testid="stSidebar"] {
        background: #ffffff; border-right: 1px solid #e8edf3;
    }
    section[data-testid="stSidebar"] .block-container { padding-top: 1.2rem; }

    section[data-testid="stFileUploaderDropzone"] {
        background: #f8fafc; border: 2px dashed #cbd5e1;
        border-radius: 12px; transition: all 0.2s ease;
    }
    section[data-testid="stFileUploaderDropzone"]:hover {
        border-color: #2563eb; background: #f0f7ff;
    }

    hr { border-color: #e8edf3; margin: 1rem 0; }

    .hero-card {
        background: linear-gradient(135deg, #ffffff 0%, #eef4ff 100%);
        border: 1px solid #dbe7ff; border-radius: 18px;
        padding: 22px 26px; box-shadow: 0 6px 22px rgba(37, 99, 235, 0.08);
        margin-bottom: 18px;
    }
    .hero-title {
        font-size: 1.75rem; font-weight: 800; color: #0f172a;
        margin: 0 0 6px 0; letter-spacing: 0.3px;
    }
    .hero-sub { color: #64748b; font-size: 0.95rem; margin: 0 0 14px 0; }
    .hero-badges { display: flex; gap: 10px; flex-wrap: wrap; }
    .hero-badge {
        display: inline-flex; align-items: center; gap: 6px;
        background: #ffffff; border: 1px solid #dbe7ff; color: #1d4ed8;
        font-weight: 600; font-size: 0.82rem; padding: 6px 12px;
        border-radius: 999px; box-shadow: 0 1px 3px rgba(37, 99, 235, 0.06);
    }
    .hero-badge .dot { width: 7px; height: 7px; border-radius: 50%; background: #2563eb; }

    .formula-box {
        margin-top: 14px; padding: 12px 16px; background: #ffffff;
        border: 1px solid #dbe7ff; border-radius: 12px;
        font-family: 'Cambria Math', 'Times New Roman', serif;
        font-size: 1.05rem; color: #0f172a;
    }
    .frac { display: inline-block; text-align: center; vertical-align: middle; margin: 0 4px; }
    .frac .num { border-bottom: 1.5px solid #0f172a; padding: 0 6px; display: block; }
    .frac .den { padding: 0 6px; display: block; }

    .side-group {
        display: flex; align-items: center; gap: 8px;
        font-weight: 700; color: #0f172a; font-size: 0.95rem; margin: 4px 0 8px 0;
    }
    .side-group .ico {
        display: inline-flex; align-items: center; justify-content: center;
        width: 24px; height: 24px; border-radius: 8px;
        background: #eef4ff; color: #2563eb; font-size: 0.85rem;
    }

    .file-head {
        display: flex; align-items: center; justify-content: space-between;
        gap: 10px; margin-bottom: 6px;
    }
    .file-name { font-weight: 700; color: #0f172a; word-break: break-all; }
    .badge {
        display: inline-block; padding: 3px 10px; border-radius: 999px;
        font-size: 0.75rem; font-weight: 700;
    }
    .badge-ok { background: #dcfce7; color: #15803d; }
    .badge-warn { background: #fef3c7; color: #b45309; }
    .badge-err { background: #fee2e2; color: #b91c1c; }

    .empty-state {
        text-align: center; padding: 60px 20px; background: #ffffff;
        border: 1px dashed #cbd5e1; border-radius: 16px; color: #64748b;
    }
    .empty-state .icon { font-size: 2.4rem; margin-bottom: 8px; }
    .empty-state .title { font-weight: 700; color: #334155; font-size: 1.05rem; }

    .chart-title {
        font-weight: 700; color: #0f172a; font-size: 1.0rem; margin: 4px 0 2px 2px;
    }
    .chart-sub {
        color: #64748b; font-size: 0.82rem; margin: 0 0 6px 2px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============ 固定字段 ============
X_FIELD = "Axial Strain (%)"
Y_FIELD = "Axial Stress (kPa)"

# ============ 应力换算参数（直径 50 cm） ============
SPECIMEN_DIAMETER_CM = 50.0
SPECIMEN_RADIUS_CM = SPECIMEN_DIAMETER_CM / 2
SPECIMEN_AREA_CM2 = 3.14 * SPECIMEN_RADIUS_CM ** 2
Y_FIELD_PLOT = "Axial Stress (MPa)"


def kpa_to_mpa(stress_kpa):
    return stress_kpa / SPECIMEN_AREA_CM2


# ============ 公式 HTML ============
FORMULA_HTML = (
    "<span style=\"font-family:'Cambria Math','Times New Roman',serif;font-size:1.05rem;\">"
    "Axial Stress (MPa) = "
    "<span class=\"frac\">"
    "<span class=\"num\">Axial Stress (kPa)</span>"
    "<span class=\"den\">3.14 × (50 / 2)<sup>2</sup></span>"
    "</span>"
    "<span style=\"color:#64748b;font-size:0.9rem;\">"
    f"&nbsp;（试件直径 50 cm，半径 25 cm，截面积 ≈ {SPECIMEN_AREA_CM2:.1f} cm²）"
    "</span>"
    "</span>"
)

# ============ 侧边栏 ============
with st.sidebar:
    st.markdown("## ⚙️ 控制面板")
    st.caption("所有设置实时生效")

    st.markdown('<div class="side-group"><span class="ico">🔄</span>转换设置</div>', unsafe_allow_html=True)
    encoding_option = st.selectbox(
        "文件编码",
        ["自动识别", "utf-8", "utf-8-sig", "gbk", "gb18030", "latin1"],
        index=0,
    )
    delimiter_option = st.selectbox(
        "分隔符", ["自动识别", ",", ";", "\\t", "|"], index=0
    )
    sheet_name = st.text_input("工作表名称", value="Sheet1")

    st.divider()

    st.markdown('<div class="side-group"><span class="ico">📊</span>绘图设置</div>', unsafe_allow_html=True)
    st.caption(f"X 轴固定：**{X_FIELD}**")
    st.caption(f"原始 Y：**{Y_FIELD}**")
    st.caption(f"换算 Y：**{Y_FIELD_PLOT}**")
    plot_type = st.radio("图类型", ["折线", "散点", "折线+散点"], index=0, horizontal=True)
    downsample = st.slider("抽样点数（0=不抽样）", 0, 5000, 0, step=500)
    show_fill = st.checkbox("曲线下方填充", value=False)

    st.divider()
    trim_enabled = st.checkbox("启用行裁剪", value=True)
    col_a, col_b = st.columns(2)
    with col_a:
        trim_head = st.number_input(
            "去除前 N 行", min_value=0, max_value=100000, value=10, step=1
        )
    with col_b:
        trim_tail = st.number_input(
            "去除后 N 行", min_value=0, max_value=100000, value=20, step=1
        )

# ============ 裁剪参数的 session_state 初始化 ============
if "trim_head_use" not in st.session_state:
    st.session_state["trim_head_use"] = int(trim_head)
if "trim_tail_use" not in st.session_state:
    st.session_state["trim_tail_use"] = int(trim_tail)


# ============ 工具函数 ============
def _try_read(file_bytes, enc, sep, engine):
    return pd.read_csv(io.BytesIO(file_bytes), encoding=enc, sep=sep, engine=engine)


@st.cache_data(show_spinner=False, max_entries=64)
def read_csv_smart(file_bytes: bytes, encoding_opt: str, delimiter_opt: str):
    encodings = (
        ["utf-8-sig", "utf-8", "gb18030", "gbk", "latin1"]
        if encoding_opt == "自动识别"
        else [encoding_opt]
    )
    seps = (
        [",", ";", "\t", "|"]
        if delimiter_opt == "自动识别"
        else [delimiter_option]
    )

    last_err = None
    for enc in encodings:
        for sep in seps:
            try:
                df = _try_read(file_bytes, enc, sep, engine="c")
                if df.shape[1] >= 1:
                    return df, enc, sep
            except Exception as e:
                last_err = e

    for enc in encodings:
        try:
            df = _try_read(file_bytes, enc, None, engine="python")
            if df.shape[1] >= 1:
                return df, enc, None
        except Exception as e:
            last_err = e

    raise ValueError(f"无法解析该 CSV：{last_err}")


@st.cache_data(show_spinner=False, max_entries=128)
def df_to_excel_bytes_cached(df: pd.DataFrame, sheet_name: str) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name=(sheet_name[:31] or "Sheet1"))
    return output.getvalue()


def find_fixed_columns(df: pd.DataFrame):
    def normalize(s):
        return str(s).strip().lower()

    tx, ty = normalize(X_FIELD), normalize(Y_FIELD)
    x_col = y_col = None
    for c in df.columns:
        nc = normalize(c)
        if x_col is None and nc == tx:
            x_col = c
        if y_col is None and nc == ty:
            y_col = c
    return x_col, y_col


def trim_dataframe(df: pd.DataFrame, head_n: int, tail_n: int):
    total = len(df)
    head_n = int(max(0, head_n))
    tail_n = int(max(0, tail_n))

    if head_n + tail_n >= total:
        return df, {
            "ok": False,
            "msg": (
                f"共 {total} 行，去除前 {head_n} 行 + 后 {tail_n} 行后无数据可绘，"
                "请减小裁剪行数。"
            ),
            "original": total,
            "trimmed": total,
        }

    end = total - tail_n if tail_n > 0 else total
    trimmed = df.iloc[head_n:end].reset_index(drop=True)
    return trimmed, {
        "ok": True,
        "msg": (
            f"原 {total} 行 → 去除前 {head_n} 行、后 {tail_n} 行 → "
            f"绘图使用 {len(trimmed)} 行"
        ),
        "original": total,
        "trimmed": len(trimmed),
    }


def _base_axis_style(is_y_axis=False):
    style = dict(
        showgrid=False, zeroline=False, showline=True,
        linecolor="black", linewidth=1.3, mirror=True,
        ticks="outside", ticklen=5, tickwidth=1.1, tickcolor="black",
        showticklabels=True,
        tickfont=dict(family="Times New Roman, 'Songti SC', SimSun, serif",
                      size=13, color="black"),
        title_font=dict(family="Times New Roman, 'Songti SC', SimSun, serif",
                        size=15, color="black"),
    )
    if is_y_axis:
        style.update(tickformat=",.0f", exponentformat="none")
    return style


def _base_layout(x_title, y_title):
    return dict(
        title=None,
        xaxis=dict(title=dict(text=str(x_title), standoff=12),
                   **_base_axis_style(False)),
        yaxis=dict(title=dict(text=str(y_title), standoff=12),
                   **_base_axis_style(True)),
        template="simple_white",
        paper_bgcolor="white", plot_bgcolor="white",
        hovermode="x unified", height=520,
        margin=dict(l=90, r=30, t=30, b=80),
        font=dict(family="Times New Roman, 'Songti SC', SimSun, serif",
                  size=13, color="black"),
        showlegend=False,
    )


def make_plot_raw(df, x_col, y_col, plot_type, downsample, show_fill=False):
    data = df[[x_col, y_col]].dropna().copy()
    if downsample and len(data) > downsample:
        data = data.iloc[:: max(1, len(data) // downsample)]

    mode = {"折线": "lines", "散点": "markers", "折线+散点": "lines+markers"}[plot_type]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data[x_col], y=data[y_col], mode=mode, name=str(y_col),
        line=dict(color="black", width=1.1, shape="linear"),
        marker=dict(size=4, color="black", symbol="circle", line=dict(width=0)),
        fill="tozeroy" if (show_fill and "lines" in mode) else None,
        fillcolor="rgba(0, 0, 0, 0.04)",
        hovertemplate=f"<b>{x_col}</b>: %{{x:.4g}}<br>"
                      f"<b>{y_col}</b>: %{{y:.0f}}<extra></extra>",
    ))
    fig.update_layout(**_base_layout(x_col, y_col))
    return fig


def make_plot_mpa(df, x_col, y_col, plot_type, downsample, show_fill=False):
    data = df[[x_col, y_col]].dropna().copy()
    data[y_col] = kpa_to_mpa(data[y_col])
    if downsample and len(data) > downsample:
        data = data.iloc[:: max(1, len(data) // downsample)]

    mode = {"折线": "lines", "散点": "markers", "折线+散点": "lines+markers"}[plot_type]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data[x_col], y=data[y_col], mode=mode, name=str(Y_FIELD_PLOT),
        line=dict(color="black", width=1.1, shape="linear"),
        marker=dict(size=4, color="black", symbol="circle", line=dict(width=0)),
        fill="tozeroy" if (show_fill and "lines" in mode) else None,
        fillcolor="rgba(0, 0, 0, 0.04)",
        hovertemplate=f"<b>{x_col}</b>: %{{x:.4g}}<br>"
                      f"<b>{Y_FIELD_PLOT}</b>: %{{y:.4g}}<extra></extra>",
    ))
    fig.update_layout(**_base_layout(x_col, Y_FIELD_PLOT))
    return fig


@st.cache_data(show_spinner=False, max_entries=64)
def fig_json_to_png(fig_json: str, scale: int = 2) -> bytes:
    fig = pio.from_json(fig_json)
    return fig.to_image(format="png", scale=scale)


def build_zip(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


def excel_name_from_csv(name: str) -> str:
    return f"{name.rsplit('.', 1)[0]}.xlsx"


def file_key(name: str, data: bytes) -> str:
    h = hashlib.md5(data).hexdigest()[:10]
    return f"{name}__{h}"


def render_badge(text, kind="ok"):
    return f'<span class="badge badge-{kind}">{text}</span>'


# ============ Hero 区 ============
st.markdown(f"""
<div class="hero-card">
    <div class="hero-title">📈 含孔蠕变应力应变处理</div>
    <div class="hero-sub">批量上传 CSV / TXT → 自动解析转换 Excel → 一键绘制应力应变曲线</div>
    <div class="hero-badges">
        <span class="hero-badge"><span class="dot"></span>X 轴：{X_FIELD}</span>
        <span class="hero-badge"><span class="dot"></span>原始 Y：{Y_FIELD}</span>
        <span class="hero-badge"><span class="dot"></span>换算 Y：{Y_FIELD_PLOT}</span>
        <span class="hero-badge"><span class="dot"></span>试件直径 50 cm</span>
        <span class="hero-badge"><span class="dot"></span>支持批量导出 ZIP</span>
    </div>
    <div class="formula-box">
        <b>应力换算公式：</b><br>
        {FORMULA_HTML}
    </div>
</div>
""", unsafe_allow_html=True)

# ============ 上传区 ============
with st.container(border=True):
    st.markdown("#### 📤 上传数据文件")
    uploaded_files = st.file_uploader(
        "拖拽或点击选择 CSV / TXT 文件（支持多选）",
        type=["csv", "txt"],
        accept_multiple_files=True,
        help="支持 csv / txt，自动识别编码与分隔符",
        label_visibility="collapsed",
    )

if not uploaded_files:
    st.markdown("""
<div class="empty-state">
    <div class="icon">📁</div>
    <div class="title">还没有上传文件</div>
    <div style="margin-top:6px;">请在上方区域选择一个或多个 CSV / TXT 文件开始处理</div>
</div>
""", unsafe_allow_html=True)
    st.stop()

# ============ 批量解析 ============
parsed = []
progress = st.progress(0.0, text="正在解析文件...")
n = len(uploaded_files)

for i, uf in enumerate(uploaded_files):
    data = uf.getvalue()
    item = {
        "name": uf.name, "key": file_key(uf.name, data),
        "df": None, "excel_bytes": None, "enc": None, "sep": None,
        "ok": False, "err": None, "x_col": None, "y_col": None,
    }
    try:
        df, enc, sep = read_csv_smart(data, encoding_option, delimiter_option)
        item.update(df=df, enc=enc, sep=sep, ok=True)
        item["excel_bytes"] = df_to_excel_bytes_cached(df, sheet_name)
        x_col, y_col = find_fixed_columns(df)
        item["x_col"] = x_col
        item["y_col"] = y_col
    except Exception as e:
        item["err"] = str(e)
    parsed.append(item)
    progress.progress((i + 1) / n, text=f"已解析 {i + 1}/{n}：{uf.name}")

progress.empty()

ok_items = [p for p in parsed if p["ok"]]
fail_items = [p for p in parsed if not p["ok"]]
plottable_items = [p for p in ok_items if p["x_col"] and p["y_col"]]

# ============ 汇总信息 ============
with st.container(border=True):
    total_rows = sum(len(p["df"]) for p in ok_items)
    total_cols = sum(p["df"].shape[1] for p in ok_items)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📁 文件总数", len(parsed))
    c2.metric("✅ 解析成功", len(ok_items))
    c3.metric("📈 可绘图", len(plottable_items))
    c4.metric("📊 总行数", f"{total_rows:,}")
    c5.metric("📋 总列数", f"{total_cols:,}")

    if fail_items:
        st.warning("以下文件解析失败：" + "、".join(f"`{p['name']}`" for p in fail_items))
    if not ok_items:
        st.error("没有任何文件解析成功，请检查编码/分隔符设置。")
        st.stop()

# ============ 主体 Tabs ============
tab_plot, tab_files, tab_data, tab_download = st.tabs(
    ["📈 应力应变曲线", "📦 批量文件", "🔍 数据预览", "⬇️ 批量下载"]
)

# ---------- 曲线 ----------
with tab_plot:
    if not plottable_items:
        st.error(
            f"没有任何文件同时包含 `{X_FIELD}` 和 `{Y_FIELD}` 两列，无法绘图。\n\n"
            "请在「🔍 数据预览」中确认列名是否完全一致（含单位与括号）。"
        )
    else:
        # ===== 1. 文件选择 + 动态裁剪参数（同一行展示） =====
        c_file, c_head, c_tail = st.columns([2.2, 1, 1])

        with c_file:
            file_names = [p["name"] for p in plottable_items]
            sel_name = st.selectbox(
                "选择要绘图的文件", file_names, index=0, key="plot_file"
            )

        with c_head:
            trim_head_use = st.number_input(
                "去除前 N 行",
                min_value=0, max_value=100000,
                value=int(st.session_state["trim_head_use"]),
                step=1, key="trim_head_use_input",
            )

        with c_tail:
            trim_tail_use = st.number_input(
                "去除后 N 行",
                min_value=0, max_value=100000,
                value=int(st.session_state["trim_tail_use"]),
                step=1, key="trim_tail_use_input",
            )

        # 写回 session_state
        st.session_state["trim_head_use"] = int(trim_head_use)
        st.session_state["trim_tail_use"] = int(trim_tail_use)

        st.caption(
            f"可绘图文件：**{len(plottable_items)}** 个 ｜ "
            f"当前裁剪：前 **{st.session_state['trim_head_use']}** 行、"
            f"后 **{st.session_state['trim_tail_use']}** 行"
        )

        # ===== 2. 绘图说明 =====
        st.markdown(f"""
<div style="background:#ffffff;border:1px solid #e3ebf6;border-radius:12px;
            padding:14px 18px;margin:12px 0;">
    <div style="font-weight:700;color:#0f172a;margin-bottom:6px;">
        📐 绘图说明
    </div>
    <div style="color:#334155;font-size:0.95rem;line-height:1.9;">
        X 轴固定：<code>{X_FIELD}</code>（不变）<br>
        <b>左图（原始）</b>：Y 轴直接使用 <code>{Y_FIELD}</code>，不做换算；<br>
        <b>右图（换算）</b>：Y 轴按下列公式换算为 <b>{Y_FIELD_PLOT}</b>：<br>
        {FORMULA_HTML}
    </div>
</div>
""", unsafe_allow_html=True)

        # ===== 3. 绘图 =====
        sel = next(p for p in plottable_items if p["name"] == sel_name)
        df = sel["df"]
        x_col, y_col = sel["x_col"], sel["y_col"]

        with st.container(border=True):
            plot_df = df
            if trim_enabled:
                plot_df, status = trim_dataframe(
                    df,
                    st.session_state["trim_head_use"],
                    st.session_state["trim_tail_use"],
                )
                if not status["ok"]:
                    st.error(f"文件 `{sel_name}`：{status['msg']}")
                    st.stop()
                st.caption(f"✂️ 已裁剪：{status['msg']}")
            else:
                st.caption("未启用行裁剪，使用完整数据绘图。")

            col_left, col_right = st.columns(2)

            with col_left:
                st.markdown('<div class="chart-title">图 1 · 原始应力应变曲线</div>',
                            unsafe_allow_html=True)
                st.markdown(
                    f'<div class="chart-sub">Y 轴：<code>{y_col}</code>（未处理，完整数字刻度）</div>',
                    unsafe_allow_html=True)
                fig_raw = make_plot_raw(
                    plot_df, x_col, y_col, plot_type, downsample, show_fill=show_fill
                )
                st.plotly_chart(
                    fig_raw, use_container_width=True, theme=None,
                    config={"displaylogo": False, "displayModeBar": False,
                            "staticPlot": False, "responsive": True},
                    key="chart_raw",
                )

            with col_right:
                st.markdown('<div class="chart-title">图 2 · 换算后应力应变曲线</div>',
                            unsafe_allow_html=True)
                st.markdown(
                    f'<div class="chart-sub">Y 轴：<code>{Y_FIELD_PLOT}</code>'
                    f'（= {y_col} / [3.14 × (50/2)²]）</div>',
                    unsafe_allow_html=True)
                fig_mpa = make_plot_mpa(
                    plot_df, x_col, y_col, plot_type, downsample, show_fill=show_fill
                )
                st.plotly_chart(
                    fig_mpa, use_container_width=True, theme=None,
                    config={"displaylogo": False, "displayModeBar": False,
                            "staticPlot": False, "responsive": True},
                    key="chart_mpa",
                )

            # PNG 下载
            png_col1, png_col2 = st.columns(2)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = sel_name.rsplit(".", 1)[0]

            with png_col1:
                try:
                    png_raw = fig_json_to_png(pio.to_json(fig_raw), scale=2)
                    st.download_button(
                        label="🖼️ 下载图 1 (原始 kPa)",
                        data=png_raw,
                        file_name=f"{base_name}_kPa_{ts}.png",
                        mime="image/png", key="dl_png_raw",
                    )
                except Exception:
                    st.caption("提示：导出 PNG 需要安装 kaleido：`pip install kaleido`")

            with png_col2:
                try:
                    png_mpa = fig_json_to_png(pio.to_json(fig_mpa), scale=2)
                    st.download_button(
                        label="🖼️ 下载图 2 (换算 MPa)",
                        data=png_mpa,
                        file_name=f"{base_name}_MPa_{ts}.png",
                        mime="image/png", key="dl_png_mpa",
                    )
                except Exception:
                    st.caption("提示：导出 PNG 需要安装 kaleido：`pip install kaleido`")

        skipped = [p["name"] for p in ok_items if not (p["x_col"] and p["y_col"])]
        if skipped:
            st.caption("以下文件缺少固定字段，未列入绘图：" + "、".join(f"`{s}`" for s in skipped))

# ---------- 批量文件 ----------
with tab_files:
    st.markdown(f"**共 {len(parsed)} 个文件 · 成功 {len(ok_items)} · 失败 {len(fail_items)}**")
    st.caption("每个文件的状态与单独下载")

    for i, p in enumerate(parsed):
        with st.container(border=True):
            if p["ok"]:
                has_plot = bool(p["x_col"] and p["y_col"])
                badge = render_badge("可绘图", "ok") if has_plot else render_badge("缺字段", "warn")
                st.markdown(
                    f'<div class="file-head">'
                    f'<span class="file-name">✅ {p["name"]}</span>{badge}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                cc1, cc2, cc3, cc4 = st.columns([1, 1, 1, 1.4])
                cc1.metric("行数", f"{len(p['df']):,}")
                cc2.metric("列数", p["df"].shape[1])
                cc3.metric("编码", p["enc"])
                cc4.metric("分隔符", p["sep"] if p["sep"] else "自动")

                if not has_plot:
                    missing = []
                    if not p["x_col"]:
                        missing.append(X_FIELD)
                    if not p["y_col"]:
                        missing.append(Y_FIELD)
                    st.caption(f"⚠️ 缺少固定字段：{'、'.join(missing)}（该文件不参与绘图）")

                out_name = excel_name_from_csv(p["name"])
                st.download_button(
                    label=f"📥 下载 {out_name}",
                    data=p["excel_bytes"],
                    file_name=out_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_file_{i}_{p['key']}",
                )
            else:
                st.markdown(
                    f'<div class="file-head">'
                    f'<span class="file-name">❌ {p["name"]}</span>{render_badge("解析失败", "err")}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.caption(p["err"])

# ---------- 数据预览 ----------
with tab_data:
    file_names = [p["name"] for p in ok_items]
    sel_name = st.selectbox("选择要预览的文件", file_names, index=0)
    sel = next(p for p in ok_items if p["name"] == sel_name)
    df = sel["df"]

    st.caption(f"当前文件：`{sel_name}` | 行数 `{len(df)}` | 列数 `{df.shape[1]}`")

    preview_mode = st.radio(
        "预览内容",
        ["原始数据", "裁剪后数据（绘图用）", "应力换算后（MPa）"],
        index=0, horizontal=True, key=f"preview_mode_{sel_name}",
    )

    if preview_mode == "原始数据":
        st.dataframe(df.head(30), use_container_width=True, height=420)

    elif preview_mode == "裁剪后数据（绘图用）":
        if trim_enabled:
            trimmed_df, status = trim_dataframe(
                df,
                st.session_state["trim_head_use"],
                st.session_state["trim_tail_use"],
            )
            if status["ok"]:
                st.caption(f"✂️ {status['msg']}")
                st.dataframe(trimmed_df.head(30), use_container_width=True, height=420)
            else:
                st.error(status["msg"])
        else:
            st.info("当前未启用行裁剪，显示与原始数据相同。")
            st.dataframe(df.head(30), use_container_width=True, height=420)

    else:
        if not (sel["x_col"] and sel["y_col"]):
            st.error(f"该文件缺少 `{X_FIELD}` 或 `{Y_FIELD}`，无法换算。")
        else:
            show_df = df.copy()
            if trim_enabled:
                trimmed_df, status = trim_dataframe(
                    df,
                    st.session_state["trim_head_use"],
                    st.session_state["trim_tail_use"],
                )
                if status["ok"]:
                    show_df = trimmed_df.copy()
                    st.caption(f"✂️ {status['msg']}")
                else:
                    st.warning(status["msg"])
            show_df[Y_FIELD_PLOT] = kpa_to_mpa(show_df[sel["y_col"]])
            st.caption(
                f"已按公式换算：{Y_FIELD_PLOT} = {Y_FIELD} / "
                f"[3.14 × (50/2)²]（直径 50 cm，截面积 ≈ {SPECIMEN_AREA_CM2:.1f} cm²）"
            )
            st.dataframe(show_df.head(30), use_container_width=True, height=420)

    with st.expander("查看所有列名与类型"):
        st.dataframe(
            pd.DataFrame({"列名": df.columns, "类型": df.dtypes.astype(str).values}),
            use_container_width=True,
        )

# ---------- 批量下载 ----------
with tab_download:
    if not ok_items:
        st.warning("没有解析成功的文件，无法下载。")
    else:
        apply_trim_to_excel = st.checkbox(
            "导出的 Excel 也应用行裁剪（前 N 行 / 后 N 行）",
            value=False,
            help="不勾选时导出完整数据；勾选时导出与绘图一致的裁剪后数据。",
            key="apply_trim_to_excel",
        )
        if apply_trim_to_excel and not trim_enabled:
            st.warning("侧边栏未启用行裁剪，导出仍为完整数据。")
            apply_trim_to_excel = False

        st.markdown("#### ① 一键打包下载全部 Excel")

        zip_files = {}
        used_names = {}
        trim_notes = []
        for p in ok_items:
            export_df = p["df"]
            if apply_trim_to_excel:
                export_df, status = trim_dataframe(
                    p["df"],
                    st.session_state["trim_head_use"],
                    st.session_state["trim_tail_use"],
                )
                if not status["ok"]:
                    trim_notes.append(f"`{p['name']}`：{status['msg']}")
                    export_df = p["df"]
            excel_bytes = df_to_excel_bytes_cached(export_df, sheet_name)

            base = excel_name_from_csv(p["name"])
            if base in used_names:
                used_names[base] += 1
                stem, ext = base.rsplit(".", 1)
                out_name = f"{stem}_{used_names[base]}.{ext}"
            else:
                used_names[base] = 0
                out_name = base
            zip_files[out_name] = excel_bytes

        st.caption("将打包以下文件：" + "、".join(f"`{n}`" for n in zip_files.keys()))
        if trim_notes:
            st.warning("以下文件裁剪失败，已回退为完整数据导出：" + "；".join(trim_notes))

        zip_bytes = build_zip(zip_files)
        st.download_button(
            label=f"📦 下载全部 Excel（{len(zip_files)} 个文件，ZIP）",
            data=zip_bytes,
            file_name="csv_to_excel.zip",
            mime="application/zip",
            key="download_all_zip",
        )

        st.divider()
        st.markdown("#### ② 逐个下载 Excel")

        for i, p in enumerate(ok_items):
            export_df = p["df"]
            if apply_trim_to_excel:
                export_df, status = trim_dataframe(
                    p["df"],
                    st.session_state["trim_head_use"],
                    st.session_state["trim_tail_use"],
                )
                if not status["ok"]:
                    export_df = p["df"]
            excel_bytes = df_to_excel_bytes_cached(export_df, sheet_name)

            out_name = excel_name_from_csv(p["name"])
            st.download_button(
                label=f"📥 {out_name}",
                data=excel_bytes,
                file_name=out_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"download_single_{i}_{p['key']}",
            )

        st.caption(
            "Excel 文件名与上传的 CSV 文件名相同，仅扩展名改为 .xlsx；"
            "内容为对应 CSV 的数据，列名保持不变。"
        )