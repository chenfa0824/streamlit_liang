import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="井下巷道智能支护方案设计系统",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem; font-weight: bold; color: #2c3e50;
        text-align: center; padding: 1rem 0;
        border-bottom: 3px solid #e67e22; margin-bottom: 1.5rem;
    }
    .result-card {
        background: linear-gradient(135deg, #e67e22 0%, #d35400 100%);
        padding: 1.5rem; border-radius: 10px; color: white; margin: 1rem 0;
    }
    .warning-box {
        background: #fff3cd; border-left: 4px solid #ffc107;
        padding: 1rem; border-radius: 5px; margin: 1rem 0;
    }
    .danger-box {
        background: #f8d7da; border-left: 4px solid #dc3545;
        padding: 1rem; border-radius: 5px; margin: 1rem 0;
    }
    .success-box {
        background: #d4edda; border-left: 4px solid #28a745;
        padding: 1rem; border-radius: 5px; margin: 1rem 0;
    }
    .param-table { font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)

# ==================== 常量库 ====================
ROCK_CLASSES = {
    "I级（坚硬完整）":   {"BQ": 600, "Rc": 120, "f": 15, "Kv": 0.90, "desc": "坚硬完整岩体"},
    "II级（坚硬较完整）": {"BQ": 480, "Rc": 90,  "f": 10, "Kv": 0.75, "desc": "坚硬较完整岩体"},
    "III级（较坚硬）":    {"BQ": 380, "Rc": 60,  "f": 7,  "Kv": 0.55, "desc": "较坚硬岩体"},
    "IV级（较软弱）":     {"BQ": 280, "Rc": 30,  "f": 4,  "Kv": 0.40, "desc": "较软弱岩体"},
    "V级（软弱破碎）":    {"BQ": 180, "Rc": 15,  "f": 2,  "Kv": 0.25, "desc": "软弱破碎岩体"},
}

# 锚杆规格库（GB/T 35056-2018）
BOLT_SPECS = {
    "Φ18 (BHRB400)": {"d": 18, "σs": 400, "A": 254.5, "Q_yield": 101.8, "Q_design": 80},
    "Φ20 (BHRB400)": {"d": 20, "σs": 400, "A": 314.2, "Q_yield": 125.7, "Q_design": 100},
    "Φ22 (BHRB400)": {"d": 22, "σs": 400, "A": 380.1, "Q_yield": 152.1, "Q_design": 120},
    "Φ22 (BHRB500)": {"d": 22, "σs": 500, "A": 380.1, "Q_yield": 190.1, "Q_design": 150},
    "Φ25 (BHRB500)": {"d": 25, "σs": 500, "A": 490.9, "Q_yield": 245.4, "Q_design": 190},
}

# 锚索规格库
CABLE_SPECS = {
    "Φ15.24 (1×7)": {"d": 15.24, "A": 140, "Q_ult": 260, "Q_design": 200},
    "Φ17.8 (1×7)":  {"d": 17.8,  "A": 191, "Q_ult": 355, "Q_design": 270},
    "Φ21.6 (1×7)":  {"d": 21.6,  "A": 285, "Q_ult": 530, "Q_design": 400},
}

# U型钢规格库
U_STEEL_SPECS = {
    "25U": {"A": 31.7, "Ix": 850,  "承载能力": 280},
    "29U": {"A": 37.0, "Ix": 1220, "承载能力": 380},
    "36U": {"A": 45.7, "Ix": 1950, "承载能力": 520},
}

SECTION_SHAPES = ["直墙半圆拱", "三心拱", "矩形", "梯形", "马蹄形", "圆形"]
SUPPORT_TYPES = ["锚杆支护", "锚网喷支护", "锚网喷+锚索", "锚网喷+钢架",
                 "U型钢可缩性支架", "锚网喷+锚索+钢架联合", "砌碹支护"]

# ==================== 侧边栏 ====================
with st.sidebar:
    st.markdown("## ⛏️ 巷道设计参数")
    st.markdown("### 1️⃣ 巷道几何")
    tunnel_name = st.text_input("巷道名称", value="运输大巷")
    B = st.number_input("净宽 B (m)", 1.5, 12.0, 4.5, 0.1)
    H = st.number_input("净高 H (m)", 1.5, 12.0, 3.5, 0.1)
    section_shape = st.selectbox("断面形状", SECTION_SHAPES, index=0)
    depth = st.number_input("埋深 h (m)", 50.0, 2000.0, 500.0, 10.0)

    st.markdown("### 2️⃣ 围岩条件")
    rock_class = st.selectbox("围岩级别", list(ROCK_CLASSES.keys()), index=3)
    gamma_rock = st.number_input("岩石容重 γ (kN/m³)", 15.0, 32.0, 25.0, 0.5)
    Rc = st.number_input("饱和抗压强度 Rc (MPa)", 1.0, 200.0, 30.0, 1.0)
    Kv = st.number_input("岩体完整性系数 Kv", 0.10, 1.00, 0.40, 0.05)
    c_r = st.number_input("围岩黏聚力 cr (MPa)", 0.0, 50.0, 2.0, 0.1)
    phi = st.number_input("围岩内摩擦角 φ (°)", 5.0, 60.0, 30.0, 1.0)

    st.markdown("### 3️⃣ 地应力与构造")
    stress_regime = st.selectbox("地应力状态",
        ["低应力区", "中等应力区", "高地应力区", "极高应力区"], index=1)
    lam = st.number_input("侧压系数 λ", 0.3, 3.0, 1.0, 0.1)
    has_water = st.checkbox("是否有涌水", value=False)
    has_fault = st.checkbox("是否穿越断层/破碎带", value=False)
    dynamic_pressure = st.checkbox("是否受采动影响", value=False)

    st.markdown("### 4️⃣ 设计偏好")
    service_life = st.selectbox("服务年限",
        ["<3年（临时）", "3-10年（一般）", ">10年（永久）"], index=1)
    design_pref = st.selectbox("支护类型偏好", ["自动推荐"] + SUPPORT_TYPES)

    run_button = st.button("🚀 生成支护方案", type="primary", use_container_width=True)


# ==================== 核心计算引擎 ====================

def calc_bq_index(Rc_val, Kv_val):
    """岩体基本质量指标 BQ（GB/T 50218-2014）"""
    Rc_used = min(Rc_val, 90 * Kv_val + 30)
    Kv_used = min(Kv_val, 0.04 * Rc_val + 0.4)
    BQ = 100 + 3 * Rc_used + 250 * Kv_used
    return round(BQ, 1), round(Rc_used, 1), round(Kv_used, 2)


def calc_rock_pressure(B_val, H_val, depth_val, rock_class_val, gamma_val, lam_val,
                       has_water_val, has_fault_val, dynamic_val, phi_val):
    """围岩压力计算（普氏压力拱理论 + 修正系数）"""
    f = ROCK_CLASSES[rock_class_val]["f"]

    # 原岩应力
    sigma_v = gamma_val * depth_val  # kPa
    sigma_h = lam_val * sigma_v

    # 塌落拱半宽
    b = B_val / 2 + H_val * np.tan(np.radians(45 - phi_val / 2))
    # 塌落拱高度
    h1 = b / max(f, 0.5)

    # 竖直/水平围岩压力
    q = gamma_val * h1
    e = q * np.tan(np.radians(45 - phi_val / 2)) ** 2

    # 修正系数
    k_water = 1.15 if has_water_val else 1.00
    k_fault = 1.25 if has_fault_val else 1.00
    k_dynamic = 1.35 if dynamic_val else 1.00

    q_design = q * k_water * k_fault * k_dynamic
    e_design = e * k_water * k_fault * k_dynamic

    return {
        "原岩竖直应力 σv(kPa)": round(sigma_v, 1),
        "原岩水平应力 σh(kPa)": round(sigma_h, 1),
        "塌落拱半宽 b(m)": round(b, 2),
        "塌落拱高度 h1(m)": round(h1, 2),
        "竖直围岩压力 q(kPa)": round(q, 1),
        "水平围岩压力 e(kPa)": round(e, 1),
        "修正后设计竖直压力 qd(kPa)": round(q_design, 1),
        "修正后设计水平压力 ed(kPa)": round(e_design, 1),
        "修正系数(水/构造/动压)": f"{k_water:.2f}/{k_fault:.2f}/{k_dynamic:.2f}",
        "普氏系数 f": f,
    }


def calc_bolt_diameter(Q_design_kN, sigma_s_MPa):
    """锚杆直径反算：Φ = √(4Q / (π·σs))"""
    Q_N = Q_design_kN * 1000.0
    sigma_s_Pa = sigma_s_MPa * 1e6
    d_m = np.sqrt(4.0 * Q_N / (np.pi * sigma_s_Pa))
    return round(d_m * 1000.0, 1)


def calc_bolt_length(B_val, H_val, f_val, phi_val):
    """锚杆长度计算（顶/帮分开）"""
    L1 = 0.1
    L3 = 0.8

    if f_val >= 3:
        L2_top = B_val / (2 * f_val)
    else:
        L2_top = B_val / 2 + H_val * (1 / np.tan(np.radians(45 + phi_val / 2)))

    L2_side = B_val / (2 * f_val) + H_val / (2 * f_val)

    return {
        "顶锚杆有效长度 L2(m)": round(L2_top, 2),
        "帮锚杆有效长度 L2(m)": round(L2_side, 2),
        "顶锚杆总长(m)": round(L1 + L2_top + L3, 1),
        "帮锚杆总长(m)": round(L1 + L2_side + L3, 1),
    }


def calc_bolt_spacing(Q_design_kN, L2_m, gamma_rock_kN, K_safety=2.0):
    """按悬吊重量校核间排距：a_max = √(Q/(K·γ·L2))"""
    denom = K_safety * gamma_rock_kN * L2_m
    if denom <= 0:
        return 1.0
    a_max = np.sqrt(Q_design_kN / denom)
    return round(min(a_max, 1.5), 2)


def calc_bolt_max_spacing_coupled(L_bolt_m, P_pre_kN, D_m, c_r_MPa, phi_deg,
                                  Q_design_kN, k=1.5):
    """围岩预紧力强化-组合拱耦合理论锚杆最大间距

    参数：
        L_bolt_m    : 锚杆长度 (m)
        P_pre_kN    : 预紧力 (kN)
        D_m         : 锚杆直径 (m)  ⚠ 单位必须是 m
        c_r_MPa     : 围岩黏聚力 (MPa)
        phi_deg     : 内摩擦角 (°)
        Q_design_kN : 锚杆设计承载力 (kN)
        k           : 安全系数
    """
    L = float(L_bolt_m)
    D = float(D_m)
    phi_rad = np.radians(phi_deg)

    # 预紧力强化系数 a = D·L³ / [π(D²/4 + L²/4)²] · tanφ
    denom = np.pi * (D ** 2 / 4 + L ** 2 / 4) ** 2
    a_coef = (D * L ** 3 / denom) * np.tan(phi_rad) if denom > 0 else 0.0

    # 锚杆等效黏聚力（简化经验）
    cb = c_r_MPa + 0.5

    # 锚固体黏聚力 c = cr + nS(cb-cr) + a·P/D
    n_density = 1.0                         # 1 根/m²
    S_bolt = np.pi * (D / 2) ** 2           # m²
    c_bolted = c_r_MPa + n_density * S_bolt * (cb - c_r_MPa) + a_coef * P_pre_kN / max(D, 1e-6)

    # 耦合理论支护力 q_min (kPa)
    sin_phi = np.sin(phi_rad)
    denom_q = max(1 - sin_phi, 1e-6)
    q_min = 2 * c_bolted * np.cos(phi_rad) / denom_q * 1000.0

    # 由 Q_design 反算最大间距
    if q_min > 0 and Q_design_kN > 0:
        a_coupled = np.sqrt(Q_design_kN / (k * q_min / 100.0))
        a_coupled = min(a_coupled, 1.5)
    else:
        a_coupled = 1.5
    return round(a_coupled, 2)


def calc_shotcrete_params(rock_class_val, q_design_kPa, has_water_val,
                          has_fault_val, span_m):
    """喷射混凝土参数"""
    base = {
        "I级（坚硬完整）":   {"t": 80,  "grade": "C20", "mesh": "φ6@200×200"},
        "II级（坚硬较完整）": {"t": 100, "grade": "C20", "mesh": "φ6@200×200"},
        "III级（较坚硬）":    {"t": 120, "grade": "C25", "mesh": "φ6@150×150"},
        "IV级（较软弱）":     {"t": 150, "grade": "C25", "mesh": "φ8@150×150"},
        "V级（软弱破碎）":    {"t": 180, "grade": "C30", "mesh": "φ8@100×100"},
    }[rock_class_val]

    t = base["t"]
    if has_water_val: t += 20
    if has_fault_val: t += 30
    if span_m > 5:    t += 20

    f_c = {"C20": 20, "C25": 25, "C30": 30}[base["grade"]]
    f_t = 0.1 * f_c

    return {
        "设计喷层厚度(mm)": t,
        "混凝土强度等级": base["grade"],
        "钢筋网规格": base["mesh"],
        "喷层抗压强度(MPa)": f_c,
        "喷层抗拉强度(MPa)": round(f_t, 2),
        "喷射方式": "湿喷" if t >= 100 else "干喷",
    }


def calc_cable_params(q_design_kPa, B_val, H_val, rock_class_val, c_r_val, phi_val):
    """锚索参数"""
    if rock_class_val in ["I级（坚硬完整）", "II级（坚硬较完整）", "III级（较坚硬）"]:
        return None

    L_cable = 6.0 + B_val / 2 + 0.5 * H_val
    L_cable = round(np.ceil(L_cable * 2) / 2, 1)

    cable_spec = CABLE_SPECS["Φ17.8 (1×7)"]
    Q_design_cable = cable_spec["Q_design"]

    spacing = 1.6 if rock_class_val == "IV级（较软弱）" else 1.4
    row_spacing = spacing * 2
    n_per_row = int(np.ceil(B_val / spacing)) + 1

    return {
        "锚索规格": "Φ17.8 (1×7 钢绞线)",
        "锚索长度(m)": L_cable,
        "锚索间排距(m)": f"{spacing}×{row_spacing}",
        "每排锚索数量(根)": n_per_row,
        "设计承载力(kN/根)": Q_design_cable,
        "预紧力(kN)": round(Q_design_cable * 0.6, 0),
        "锚固方式": "树脂锚固剂（Z2360）×2",
    }


def calc_steel_arch_params(rock_class_val, B_val, H_val, dyn_val,
                           fault_val, life_val):
    """U型钢可缩性支架参数"""
    if rock_class_val in ["I级（坚硬完整）", "II级（坚硬较完整）"]:
        return None

    if dyn_val or rock_class_val == "V级（软弱破碎）":
        spec_name = "36U"; spacing = 0.6
    elif rock_class_val == "IV级（较软弱）":
        spec_name = "29U"; spacing = 0.7
    else:
        spec_name = "25U"; spacing = 0.8

    spec = U_STEEL_SPECS[spec_name]

    overlap = 350 if B_val < 3 else (400 if B_val < 5 else 450)
    compress = 400 if dyn_val else (200 if life_val == ">10年（永久）" else 300)

    return {
        "钢架型号": f"{spec_name} 型钢",
        "截面积(cm²)": spec["A"],
        "截面惯性矩(cm⁴)": spec["Ix"],
        "单架承载能力(kN)": spec["承载能力"],
        "支架间距(m)": spacing,
        "搭接长度(mm)": overlap,
        "设计可缩量(mm)": compress,
        "卡缆预紧力矩(N·m)": 250,
        "拉杆规格": "Φ18 圆钢",
        "背板材料": "水泥背板 / 钢筋网",
    }


def calc_anchor_capacity_check(Q_design_kN, q_design_kPa, spacing, row_spacing):
    """锚杆承载力校核"""
    area_per_bolt = spacing * row_spacing
    load_per_bolt = q_design_kPa * area_per_bolt
    sf = Q_design_kN / max(load_per_bolt, 0.1)
    return {
        "单根锚杆承担面积(m²)": round(area_per_bolt, 2),
        "单根锚杆实际荷载(kN)": round(load_per_bolt, 1),
        "锚杆设计承载力(kN)": Q_design_kN,
        "锚杆安全系数": round(sf, 2),
        "校核结果": "✅ 满足" if sf >= 1.5 else "⚠️ 偏低",
    }


def recommend_support(rock_class_val, section_shape_val, service_life_val,
                      dyn_val, fault_val, water_val, design_pref_val, stability_val):
    """智能推荐支护方案"""
    reasons, warnings = [], []

    if rock_class_val == "I级（坚硬完整）":
        primary = "锚杆支护"
        alternatives = ["锚网喷支护", "素喷混凝土"]
        reasons.append("围岩坚硬完整，普氏系数 f≥10，锚杆可有效加固")
    elif rock_class_val == "II级（坚硬较完整）":
        primary = "锚网喷支护"
        alternatives = ["锚杆支护", "锚网喷+锚索"]
        reasons.append("围岩较完整，锚网喷可控制局部掉块")
    elif rock_class_val == "III级（较坚硬）":
        primary = "锚网喷支护"
        alternatives = ["锚网喷+锚索", "锚网喷+钢架"]
        reasons.append("围岩较坚硬，锚网喷可形成有效组合拱")
    elif rock_class_val == "IV级（较软弱）":
        primary = "锚网喷+锚索"
        alternatives = ["锚网喷+钢架", "U型钢可缩性支架", "联合支护"]
        reasons.append("围岩较软弱，需锚索悬吊至深部稳定岩层")
    else:
        primary = "锚网喷+锚索+钢架联合"
        alternatives = ["U型钢可缩性支架", "砌碹支护"]
        reasons.append("围岩软弱破碎，必须采用强支护+可缩性支架")

    if dyn_val and "钢架" not in primary:
        primary = "锚网喷+钢架"
        reasons.append("受采动影响，增加钢架提高抗动压能力")
        warnings.append("建议采用可缩性支架，允许一定变形释放压力")

    if fault_val and "钢架" not in primary:
        primary = "锚网喷+钢架"
        reasons.append("穿越断层破碎带，需钢架保证安全")
        warnings.append("建议采用超前管棚或小导管预支护")

    if service_life_val == ">10年（永久）" and rock_class_val in ["IV级（较软弱）", "V级（软弱破碎）"]:
        alternatives.insert(0, "砌碹支护（永久耐久）")

    if design_pref_val != "自动推荐":
        primary = design_pref_val
        reasons.append(f"用户指定：{design_pref_val}")

    if stability_val in ["不稳定", "极不稳定"]:
        warnings.append(f"⚠️ 围岩稳定性：{stability_val}，需加强监测和二次支护预案")
    if water_val:
        warnings.append("💧 存在涌水，需超前探放水及排水措施")
    if fault_val:
        warnings.append("⚠️ 穿越断层，需超前支护（管棚/小导管）")

    return {"推荐方案": primary, "备选方案": alternatives,
            "推荐理由": reasons, "安全预警": warnings}


def calc_stability_index(rock_class_val, depth_val, dyn_val, fault_val, water_val):
    base = {"I级（坚硬完整）": 95, "II级（坚硬较完整）": 85,
            "III级（较坚硬）": 70, "IV级（较软弱）": 50,
            "V级（软弱破碎）": 30}[rock_class_val]
    if depth_val > 800:    base -= 15
    elif depth_val > 500:  base -= 8
    elif depth_val > 300:  base -= 3
    if dyn_val:   base -= 15
    if fault_val: base -= 10
    if water_val: base -= 5
    return max(base, 5)


# ==================== 主页面 ====================
st.markdown('<div class="main-header">⛏️ 井下巷道智能支护方案设计系统</div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["📊 围岩分级", "📐 压力计算", "🎯 支护方案", "📄 设计报告"])


# ---------- Tab1 ----------
with tab1:
    st.markdown("### 岩体基本质量分级")
    BQ, Rc_used, Kv_used = calc_bq_index(Rc, Kv)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("BQ 值", BQ)
    col2.metric("Rc（修正）", f"{Rc_used} MPa")
    col3.metric("Kv（修正）", Kv_used)
    col4.metric("普氏系数 f", ROCK_CLASSES[rock_class]["f"])

    st.info(f"📌 **围岩描述：** {ROCK_CLASSES[rock_class]['desc']}")
    st.caption("BQ 计算公式：BQ = 100 + 3Rc + 250Kv（GB/T 50218-2014）")

    si = calc_stability_index(rock_class, depth, dynamic_pressure, has_fault, has_water)
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number", value=si, title={'text': "稳定性指数"},
        gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#2c3e50"},
               'steps': [
                   {'range': [0, 30], 'color': "#dc3545"},
                   {'range': [30, 50], 'color': "#fd7e14"},
                   {'range': [50, 70], 'color': "#ffc107"},
                   {'range': [70, 85], 'color': "#20c997"},
                   {'range': [85, 100], 'color': "#28a745"},
               ],
               'threshold': {'line': {'color': "red", 'width': 4},
                             'thickness': 0.75, 'value': 50}}))
    fig_gauge.update_layout(height=280)
    st.plotly_chart(fig_gauge, use_container_width=True)

    if si < 30:
        st.markdown('<div class="danger-box">🔴 <b>极不稳定</b>：强支护 + 超前支护 + 可缩性支架</div>', unsafe_allow_html=True)
    elif si < 50:
        st.markdown('<div class="warning-box">🟠 <b>不稳定</b>：锚网喷 + 锚索/钢架联合支护</div>', unsafe_allow_html=True)
    elif si < 70:
        st.markdown('<div class="warning-box">🟡 <b>中等稳定</b>：锚网喷为主，局部加强</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="success-box">🟢 <b>稳定</b>：常规锚杆/锚网喷即可</div>', unsafe_allow_html=True)


# ---------- Tab2 ----------
with tab2:
    if run_button:
        pressure = calc_rock_pressure(B, H, depth, rock_class, gamma_rock, lam,
                                      has_water, has_fault, dynamic_pressure, phi)
        stability_text = "稳定"
        si = calc_stability_index(rock_class, depth, dynamic_pressure, has_fault, has_water)
        if si < 30: stability_text = "极不稳定"
        elif si < 50: stability_text = "不稳定"
        elif si < 70: stability_text = "中等稳定"

        st.session_state['pressure'] = pressure
        st.session_state['stability_text'] = stability_text
        st.session_state['calc_done'] = True
        st.session_state['snapshot'] = {
            "name": tunnel_name, "B": B, "H": H, "depth": depth,
            "shape": section_shape, "rock": rock_class, "life": service_life,
            "water": has_water, "fault": has_fault, "dyn": dynamic_pressure,
            "phi": phi, "c_r": c_r, "gamma": gamma_rock,
        }

    if st.session_state.get('calc_done', False):
        p = st.session_state['pressure']
        st.success("✅ 围岩压力计算完成")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("设计竖直压力 qd", f"{p['修正后设计竖直压力 qd(kPa)']} kPa")
        col2.metric("设计水平压力 ed", f"{p['修正后设计水平压力 ed(kPa)']} kPa")
        col3.metric("塌落拱高度 h₁", f"{p['塌落拱高度 h1(m)']} m")
        col4.metric("塌落拱半宽 b", f"{p['塌落拱半宽 b(m)']} m")

        pdf = pd.DataFrame([{"项目": k, "数值": v} for k, v in p.items()])
        st.dataframe(pdf, use_container_width=True, hide_index=True)
    else:
        st.info("👈 请在左侧输入参数并点击「生成支护方案」")


# ---------- Tab3 ----------
with tab3:
    if st.session_state.get('calc_done', False):
        p = st.session_state['pressure']
        snap = st.session_state['snapshot']
        stability_text = st.session_state.get('stability_text', '中等稳定')

        support = recommend_support(
            snap['rock'], snap['shape'], snap['life'],
            snap['dyn'], snap['fault'], snap['water'],
            design_pref, stability_text
        )

        st.markdown(f"""
        <div class="result-card">
            <h2>🎯 推荐方案：{support['推荐方案']}</h2>
            <p>📋 {snap['name']} | {snap['rock']} | 埋深 {snap['depth']}m | 断面 {snap['B']}×{snap['H']}m</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### 💡 推荐理由")
        for r in support['推荐理由']:
            st.markdown(f"- {r}")

        for w in support['安全预警']:
            st.markdown(f'<div class="warning-box">{w}</div>', unsafe_allow_html=True)

        # ============ 锚杆参数 ============
        st.markdown("---")
        st.markdown("### 🔩 锚杆支护参数（GB/T 35056-2018）")

        f_val = ROCK_CLASSES[snap['rock']]['f']
        qd = p['修正后设计竖直压力 qd(kPa)']

        if f_val >= 7:
            bolt_key = "Φ18 (BHRB400)"
        elif f_val >= 4:
            bolt_key = "Φ20 (BHRB400)"
        else:
            bolt_key = "Φ22 (BHRB400)"
        bolt = BOLT_SPECS[bolt_key]

        # 直径反算校核
        d_calc = calc_bolt_diameter(bolt["Q_design"], bolt["σs"])

        # 长度计算
        bolt_len = calc_bolt_length(snap['B'], snap['H'], f_val, snap['phi'])

        # 悬吊理论间排距
        L2_top = bolt_len["顶锚杆有效长度 L2(m)"]
        a_max = calc_bolt_spacing(bolt["Q_design"], L2_top, snap['gamma'])

        # 耦合理论校核（注意：D 用 m，Q_design 传 kN）
        D_m = bolt["d"] / 1000.0
        a_coupled = calc_bolt_max_spacing_coupled(
            L_bolt_m=bolt_len["顶锚杆总长(m)"],
            P_pre_kN=60.0,
            D_m=D_m,
            c_r_MPa=snap['c_r'],
            phi_deg=snap['phi'],
            Q_design_kN=bolt["Q_design"],
        )

        # 取较保守值
        spacing_final = min(a_max, a_coupled, 1.2)
        spacing_final = round(max(spacing_final, 0.6), 1)
        row_spacing = spacing_final

        # 承载力校核
        check = calc_anchor_capacity_check(
            bolt["Q_design"], qd, spacing_final, row_spacing
        )

        bolt_rows = [
            {"参数": "锚杆规格", "取值": bolt_key, "说明": "左旋无纵筋螺纹钢"},
            {"参数": "杆体直径(mm)", "取值": bolt["d"], "说明": f"反算值 d_calc={d_calc}mm"},
            {"参数": "屈服强度(MPa)", "取值": bolt["σs"], "说明": "BHRB400"},
            {"参数": "截面积(mm²)", "取值": bolt["A"], "说明": ""},
            {"参数": "屈服荷载(kN)", "取值": bolt["Q_yield"], "说明": "≥锚固力要求"},
            {"参数": "设计锚固力(kN)", "取值": bolt["Q_design"], "说明": "规范要求≥屈服力80%"},
            {"参数": "顶锚杆有效长度 L2(m)", "取值": bolt_len["顶锚杆有效长度 L2(m)"], "说明": "f≥3: B/2f"},
            {"参数": "顶锚杆总长(m)", "取值": bolt_len["顶锚杆总长(m)"], "说明": "L1+L2+L3"},
            {"参数": "帮锚杆总长(m)", "取值": bolt_len["帮锚杆总长(m)"], "说明": ""},
            {"参数": "间排距(m×m)", "取值": f"{spacing_final}×{row_spacing}",
             "说明": f"悬吊校核 a_max={a_max}m，耦合校核 a_c={a_coupled}m"},
            {"参数": "单根锚杆荷载(kN)", "取值": check["单根锚杆实际荷载(kN)"], "说明": ""},
            {"参数": "安全系数", "取值": check["锚杆安全系数"], "说明": check["校核结果"]},
            {"参数": "预紧力(kN)", "取值": round(bolt["Q_design"] * 0.6, 0), "说明": "规范要求≥60kN"},
            {"参数": "锚固方式", "取值": "树脂锚固剂", "说明": "Z2360 + K2360 各1根"},
            {"参数": "托板规格", "取值": "150×150×8mm 拱形托板", "说明": ""},
            {"参数": "螺母", "取值": "M22 快速安装螺母", "说明": ""},
        ]
        bolt_df = pd.DataFrame(bolt_rows)
        st.dataframe(bolt_df, use_container_width=True, hide_index=True)

        # ============ 锚索 ============
        cable = calc_cable_params(qd, snap['B'], snap['H'], snap['rock'],
                                  snap['c_r'], snap['phi'])
        if cable:
            st.markdown("### 🎣 锚索支护参数")
            cable_df = pd.DataFrame([{"参数": k, "取值": v} for k, v in cable.items()])
            st.dataframe(cable_df, use_container_width=True, hide_index=True)

        # ============ 喷射混凝土 ============
        shot = calc_shotcrete_params(snap['rock'], qd, snap['water'],
                                     snap['fault'], snap['B'])
        st.markdown("### 🧱 喷射混凝土参数")
        shot_df = pd.DataFrame([{"参数": k, "取值": v} for k, v in shot.items()])
        st.dataframe(shot_df, use_container_width=True, hide_index=True)

        # ============ 钢架 ============
        steel = calc_steel_arch_params(snap['rock'], snap['B'], snap['H'],
                                       snap['dyn'], snap['fault'], snap['life'])
        if steel:
            st.markdown("### 🏗️ U型钢可缩性支架参数")
            steel_df = pd.DataFrame([{"参数": k, "取值": v} for k, v in steel.items()])
            st.dataframe(steel_df, use_container_width=True, hide_index=True)

        # ============ 布置示意图 ============
        st.markdown("### 📐 支护布置示意图")
        Bv, Hv = snap['B'], snap['H']
        fig = go.Figure()

        fig.add_shape(type="rect", x0=-Bv/2, y0=0, x1=Bv/2, y1=Hv,
                      line=dict(color="#2c3e50", width=3),
                      fillcolor="rgba(240,240,240,0.5)")

        n_top = int(Bv / spacing_final) + 1
        for i in range(n_top):
            x = -Bv/2 + i * (Bv / max(n_top - 1, 1))
            fig.add_shape(type="line", x0=x, y0=Hv, x1=x, y1=Hv + 0.35,
                          line=dict(color="#dc3545", width=3))

        n_side = int(Hv / row_spacing) + 1
        for j in range(n_side):
            y = j * (Hv / max(n_side - 1, 1))
            fig.add_shape(type="line", x0=-Bv/2, y0=y, x1=-Bv/2 - 0.35, y1=y,
                          line=dict(color="#dc3545", width=3))
            fig.add_shape(type="line", x0=Bv/2, y0=y, x1=Bv/2 + 0.35, y1=y,
                          line=dict(color="#dc3545", width=3))

        if cable:
            cable_sp = float(cable['锚索间排距(m)'].split("×")[0])
            n_cable = int(Bv / cable_sp) + 1
            for i in range(n_cable):
                x = -Bv/2 + i * (Bv / max(n_cable - 1, 1))
                fig.add_shape(type="line", x0=x, y0=Hv, x1=x, y1=Hv + 0.8,
                              line=dict(color="#8e44ad", width=3, dash="dot"))

        if steel:
            fig.add_shape(type="rect", x0=-Bv/2 + 0.12, y0=0.05,
                          x1=Bv/2 - 0.12, y1=Hv - 0.12,
                          line=dict(color="#3498db", width=2, dash="dash"))

        fig.add_shape(type="rect", x0=-Bv/2 - 0.04, y0=-0.04,
                      x1=Bv/2 + 0.04, y1=Hv + 0.04,
                      line=dict(color="#f39c12", width=2))

        fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines',
                                 line=dict(color="#dc3545", width=3), name='锚杆'))
        if cable:
            fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines',
                                     line=dict(color="#8e44ad", width=3, dash='dot'),
                                     name='锚索'))
        fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines',
                                 line=dict(color="#f39c12", width=2), name='喷层'))
        if steel:
            fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines',
                                     line=dict(color="#3498db", width=2, dash='dash'),
                                     name='钢架'))

        fig.update_layout(
            title=f"{support['推荐方案']} 布置示意图",
            xaxis=dict(title="宽度 (m)", range=[-Bv*1.2, Bv*1.2],
                       scaleanchor="y", scaleratio=1),
            yaxis=dict(title="高度 (m)", range=[-0.5, Hv + 1.2]),
            height=500,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig, use_container_width=True)

        # 存储
        st.session_state['support'] = support
        st.session_state['bolt_df'] = bolt_df
        st.session_state['shot'] = shot
        st.session_state['cable'] = cable
        st.session_state['steel'] = steel
    else:
        st.info("👈 请先点击「生成支护方案」")


# ---------- Tab4 ----------
with tab4:
    if st.session_state.get('calc_done', False) and 'support' in st.session_state:
        snap = st.session_state['snapshot']
        p = st.session_state['pressure']
        support = st.session_state['support']

        report = []
        report.append("# 井下巷道支护设计报告\n")
        report.append(f"**生成时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report.append("---\n")
        report.append("## 一、工程概况\n")
        report.append(f"- 巷道名称：{snap['name']}")
        report.append(f"- 断面尺寸：{snap['B']}m × {snap['H']}m（{snap['shape']}）")
        report.append(f"- 埋深：{snap['depth']}m")
        report.append(f"- 服务年限：{snap['life']}\n")

        report.append("## 二、围岩条件\n")
        report.append(f"- 围岩级别：{snap['rock']}")
        report.append(f"- 岩石容重：{snap['gamma']} kN/m³")
        report.append(f"- 围岩黏聚力：{snap['c_r']} MPa")
        report.append(f"- 内摩擦角：{snap['phi']}°\n")

        report.append("## 三、围岩压力\n")
        for k, v in p.items():
            report.append(f"- {k}：{v}")
        report.append("")

        report.append("## 四、推荐支护方案\n")
        report.append(f"**推荐方案：** {support['推荐方案']}\n")
        report.append("**推荐理由：**")
        for r in support['推荐理由']:
            report.append(f"- {r}")
        report.append("")

        report.append("### 4.1 锚杆支护参数\n")
        bolt_df = st.session_state.get('bolt_df')
        if bolt_df is not None:
            report.append("| 参数 | 取值 | 说明 |")
            report.append("|------|------|------|")
            for _, row in bolt_df.iterrows():
                report.append(f"| {row['参数']} | {row['取值']} | {row['说明']} |")
        report.append("")

        if st.session_state.get('cable'):
            report.append("### 4.2 锚索支护参数\n")
            for k, v in st.session_state['cable'].items():
                report.append(f"- {k}：{v}")
            report.append("")

        report.append("### 4.3 喷射混凝土参数\n")
        for k, v in st.session_state['shot'].items():
            report.append(f"- {k}：{v}")
        report.append("")

        if st.session_state.get('steel'):
            report.append("### 4.4 U型钢支架参数\n")
            for k, v in st.session_state['steel'].items():
                report.append(f"- {k}：{v}")
            report.append("")

        report.append("## 五、施工要点\n")
        report.append("1. 光面爆破，控制超挖 ≤150mm")
        report.append("2. 掘出后立即初喷 30~50mm 封闭围岩")
        report.append("3. 锚杆安装：钻眼→清孔→注树脂药卷→搅拌→固化→安装托板→预紧")
        report.append("4. 锚索张拉：注浆后等待 7 天，张拉至设计预紧力")
        report.append("5. 喷射混凝土：分层喷射，每层 ≤100mm")
        report.append("6. 监测：布设顶板离层仪、收敛计，每 50m 一个测站\n")

        report.append("---\n")
        report.append("*本报告依据 GB/T 35056-2018、GB 50419-2017 自动生成，供初步设计参考。*")

        full_report = "\n".join(report)
        st.markdown(full_report)

        st.download_button(
            "📥 下载设计报告 (Markdown)",
            data=full_report,
            file_name=f"巷道支护设计报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown", use_container_width=True
        )
    else:
        st.info("👈 请先生成支护方案")

st.markdown("---")
st.markdown(
    "<p style='text-align:center; color:#888;'>⛏️ 井下巷道智能支护方案设计系统 | "
    "依据 GB/T 35056-2018、GB 50419-2017 | 结果仅供参考</p>",
    unsafe_allow_html=True
)