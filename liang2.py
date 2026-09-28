import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import io
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import ezdxf
from ezdxf.enums import TextEntityAlignment
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

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
    .seg-badge {
        display: inline-block; padding: 4px 12px; border-radius: 12px;
        color: white; font-weight: bold; font-size: 0.85rem;
        margin-right: 6px;
    }
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

BOLT_SPECS = {
    "Φ18 (BHRB400)": {"d": 18, "σs": 400, "A": 254.5, "Q_yield": 101.8, "Q_design": 80},
    "Φ20 (BHRB400)": {"d": 20, "σs": 400, "A": 314.2, "Q_yield": 125.7, "Q_design": 100},
    "Φ22 (BHRB400)": {"d": 22, "σs": 400, "A": 380.1, "Q_yield": 152.1, "Q_design": 120},
    "Φ22 (BHRB500)": {"d": 22, "σs": 500, "A": 380.1, "Q_yield": 190.1, "Q_design": 150},
    "Φ25 (BHRB500)": {"d": 25, "σs": 500, "A": 490.9, "Q_yield": 245.4, "Q_design": 190},
}

CABLE_SPECS = {
    "Φ15.24 (1×7)": {"d": 15.24, "A": 140, "Q_ult": 260, "Q_design": 200},
    "Φ17.8 (1×7)":  {"d": 17.8,  "A": 191, "Q_ult": 355, "Q_design": 270},
    "Φ21.6 (1×7)":  {"d": 21.6,  "A": 285, "Q_ult": 530, "Q_design": 400},
}

U_STEEL_SPECS = {
    "25U": {"A": 31.7, "Ix": 850,  "承载能力": 280},
    "29U": {"A": 37.0, "Ix": 1220, "承载能力": 380},
    "36U": {"A": 45.7, "Ix": 1950, "承载能力": 520},
}

SECTION_SHAPES = ["直墙半圆拱", "三心拱", "矩形", "梯形", "马蹄形", "圆形"]
SUPPORT_TYPES = ["锚杆支护", "锚网喷支护", "锚网喷+锚索", "锚网喷+钢架",
                 "U型钢可缩性支架", "锚网喷+锚索+钢架联合", "砌碹支护"]

# 特殊段颜色映射（供多处复用）
REASON_COLORS = {
    "断层破碎带":     "#e74c3c",
    "涌水段":         "#3498db",
    "采动影响区":     "#e67e22",
    "交叉点/硐室":   "#9b59b6",
    "淋水段":         "#1abc9c",
    "岩性突变带":     "#7f8c8d",
    "高地应力岩爆段": "#c0392b",
    "软岩大变形段":   "#d35400",
    "其他":           "#f39c12",
}

REASON_ICONS = {
    "断层破碎带": "🔴",
    "涌水段": "💧",
    "采动影响区": "⚡",
    "交叉点/硐室": "🏗️",
    "淋水段": "💦",
    "岩性突变带": "🪨",
    "高地应力岩爆段": "💥",
    "软岩大变形段": "🌀",
    "其他": "⚠️",
}

# ==================== 侧边栏 ====================
with st.sidebar:
    st.markdown("## ⛏️ 巷道设计参数")
    st.markdown("### 1️⃣ 巷道几何")
    tunnel_name = st.text_input("巷道名称", value="运输大巷")
    B = st.number_input("净宽 B (m)", 1.5, 12.0, 4.5, 0.1)
    H = st.number_input("净高 H (m)", 1.5, 12.0, 3.5, 0.1)
    section_shape = st.selectbox("断面形状", SECTION_SHAPES, index=0)
    depth = st.number_input("埋深 h (m)", 50.0, 2000.0, 500.0, 10.0)
    total_length = st.number_input("巷道全长 L (m)", 50.0, 10000.0, 2000.0, 50.0)

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
    Rc_used = min(Rc_val, 90 * Kv_val + 30)
    Kv_used = min(Kv_val, 0.04 * Rc_val + 0.4)
    BQ = 100 + 3 * Rc_used + 250 * Kv_used
    return round(BQ, 1), round(Rc_used, 1), round(Kv_used, 2)


def calc_rock_pressure(B_val, H_val, depth_val, rock_class_val, gamma_val, lam_val,
                       has_water_val, has_fault_val, dynamic_val, phi_val):
    f = ROCK_CLASSES[rock_class_val]["f"]
    sigma_v = gamma_val * depth_val
    sigma_h = lam_val * sigma_v
    b = B_val / 2 + H_val * np.tan(np.radians(45 - phi_val / 2))
    h1 = b / max(f, 0.5)
    q = gamma_val * h1
    e = q * np.tan(np.radians(45 - phi_val / 2)) ** 2
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
    Q_N = Q_design_kN * 1000.0
    sigma_s_Pa = sigma_s_MPa * 1e6
    d_m = np.sqrt(4.0 * Q_N / (np.pi * sigma_s_Pa))
    return round(d_m * 1000.0, 1)


def calc_bolt_length(B_val, H_val, f_val, phi_val):
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
    denom = K_safety * gamma_rock_kN * L2_m
    if denom <= 0:
        return 1.0
    a_max = np.sqrt(Q_design_kN / denom)
    return round(min(a_max, 1.5), 2)


def calc_bolt_max_spacing_coupled(L_bolt_m, P_pre_kN, D_m, c_r_MPa, phi_deg,
                                  Q_design_kN, k=1.5):
    L = float(L_bolt_m)
    D = float(D_m)
    phi_rad = np.radians(phi_deg)
    denom = np.pi * (D ** 2 / 4 + L ** 2 / 4) ** 2
    a_coef = (D * L ** 3 / denom) * np.tan(phi_rad) if denom > 0 else 0.0
    cb = c_r_MPa + 0.5
    n_density = 1.0
    S_bolt = np.pi * (D / 2) ** 2
    c_bolted = c_r_MPa + n_density * S_bolt * (cb - c_r_MPa) + a_coef * P_pre_kN / max(D, 1e-6)
    sin_phi = np.sin(phi_rad)
    denom_q = max(1 - sin_phi, 1e-6)
    q_min = 2 * c_bolted * np.cos(phi_rad) / denom_q * 1000.0
    if q_min > 0 and Q_design_kN > 0:
        a_coupled = np.sqrt(Q_design_kN / (k * q_min / 100.0))
        a_coupled = min(a_coupled, 1.5)
    else:
        a_coupled = 1.5
    return round(a_coupled, 2)


def calc_shotcrete_params(rock_class_val, q_design_kPa, has_water_val,
                          has_fault_val, span_m):
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


# ==================== 特殊段加强参数计算 ====================

def calc_segment_reinforced_params(base_snap, base_qd, seg):
    """根据基础参数和加强系数，计算特殊段的加强支护参数"""
    f_boost = seg['factor']
    B_val = base_snap['B']
    H_val = base_snap['H']
    gamma_val = base_snap['gamma']
    phi_val = base_snap['phi']
    rock_val = base_snap['rock']

    f_val = ROCK_CLASSES[rock_val]['f']
    qd_boost = base_qd * (1 + f_boost)

    if f_val >= 7:
        bolt_key = "Φ18 (BHRB400)"
    elif f_val >= 4:
        bolt_key = "Φ20 (BHRB400)"
    else:
        bolt_key = "Φ22 (BHRB400)"
    bolt = BOLT_SPECS[bolt_key]
    bolt_len = calc_bolt_length(B_val, H_val, f_val, phi_val)

    L2_top = bolt_len["顶锚杆有效长度 L2(m)"]
    a_max = calc_bolt_spacing(bolt["Q_design"], L2_top, gamma_val)
    D_m = bolt["d"] / 1000.0
    a_coupled = calc_bolt_max_spacing_coupled(
        L_bolt_m=bolt_len["顶锚杆总长(m)"],
        P_pre_kN=60.0,
        D_m=D_m,
        c_r_MPa=base_snap['c_r'],
        phi_deg=phi_val,
        Q_design_kN=bolt["Q_design"],
    )
    spacing_normal = min(a_max, a_coupled, 1.2)
    spacing_normal = round(max(spacing_normal, 0.6), 1)

    spacing_boost = max(round(spacing_normal / (1 + f_boost * 0.5), 2), 0.5)

    shot_normal = calc_shotcrete_params(rock_val, base_qd, False, False, B_val)
    t_normal = shot_normal['设计喷层厚度(mm)']
    t_boost = int(round(t_normal * (1 + f_boost * 0.3), -1))

    pre_normal = round(bolt["Q_design"] * 0.6, 0)
    pre_boost = round(pre_normal * (1 + f_boost * 0.4), 0)

    steel_normal = calc_steel_arch_params(rock_val, B_val, H_val, False, False, "3-10年（一般）")
    steel_sp_normal = steel_normal['支架间距(m)'] if steel_normal else 0.8
    steel_sp_boost = max(round(steel_sp_normal / (1 + f_boost * 0.6), 2), 0.4)

    cable_normal = calc_cable_params(base_qd, B_val, H_val, rock_val,
                                     base_snap['c_r'], phi_val)
    if cable_normal:
        cable_sp_normal_str = cable_normal['锚索间排距(m)']
        sp_n, rsp_n = cable_sp_normal_str.split("×")
        cable_sp_boost = max(round(float(sp_n) / (1 + f_boost * 0.4), 1), 1.0)
        cable_rsp_boost = max(round(float(rsp_n) / (1 + f_boost * 0.4), 1), 2.0)
        cable_len_boost = round(cable_normal['锚索长度(m)'] * (1 + f_boost * 0.15), 1)
    else:
        cable_sp_boost = None
        cable_rsp_boost = None
        cable_len_boost = None

    deform_normal = 100
    deform_boost = int(round(deform_normal * (1 + f_boost * 1.5), -1))

    return {
        "bolt_spec": bolt_key,
        "bolt_length_top": bolt_len['顶锚杆总长(m)'],
        "bolt_spacing_normal": spacing_normal,
        "bolt_spacing_boost": spacing_boost,
        "shot_normal": t_normal,
        "shot_boost": t_boost,
        "pre_normal": pre_normal,
        "pre_boost": pre_boost,
        "steel_sp_normal": steel_sp_normal,
        "steel_sp_boost": steel_sp_boost,
        "cable_sp_boost": cable_sp_boost,
        "cable_rsp_boost": cable_rsp_boost,
        "cable_len_boost": cable_len_boost,
        "deform_normal": deform_normal,
        "deform_boost": deform_boost,
        "qd_boost": round(qd_boost, 1),
    }


# ==================== 断面几何统一描述 ====================

def get_section_geometry(shape, B, H, offset=0.0):
    if shape == "矩形":
        x0, x1 = -B / 2 - offset, B / 2 + offset
        y0, y1 = -offset, H + offset
        lines = [(x0, y0, x1, y0), (x1, y0, x1, y1),
                 (x1, y1, x0, y1), (x0, y1, x0, y0)]
        n = 20
        top_path = [(x0 + i * (x1 - x0) / n, y1, 90.0) for i in range(n + 1)]
        side_left = [(x0, y1 - i * (y1 - y0) / 20) for i in range(21)]
        side_right = [(x1, y1 - i * (y1 - y0) / 20) for i in range(21)]
        return {"lines": lines, "arcs": [], "top_path": top_path,
                "side_lines": {"left": side_left, "right": side_right},
                "wall_h": y1}

    elif shape == "直墙半圆拱":
        r = B / 2 + offset
        wall_h = H - B / 2
        x0, x1 = -B / 2 - offset, B / 2 + offset
        y0 = -offset
        lines = [(x0, y0, x0, wall_h), (x1, wall_h, x1, y0), (x1, y0, x0, y0)]
        arcs = [(0, wall_h, r, 0, 180)]
        n = 24
        top_path = []
        for i in range(n + 1):
            a = 180.0 * i / n
            rad = np.radians(a)
            top_path.append((r * np.cos(rad), wall_h + r * np.sin(rad), a))
        side_left = [(x0, wall_h - i * (wall_h - y0) / 10) for i in range(11)]
        side_right = [(x1, wall_h - i * (wall_h - y0) / 10) for i in range(11)]
        return {"lines": lines, "arcs": arcs, "top_path": top_path,
                "side_lines": {"left": side_left, "right": side_right},
                "wall_h": wall_h}

    elif shape == "三心拱":
        R1 = B / 2 + offset
        R2 = B / 4
        wall_h = H - R1 * 0.7
        x0, x1 = -B / 2 - offset, B / 2 + offset
        y0 = -offset
        cy1 = wall_h + R1 * 0.3
        cx2_left = -B / 2 - offset + R2
        cy2 = wall_h
        lines = [(x0, y0, x0, wall_h), (x1, wall_h, x1, y0), (x1, y0, x0, y0)]
        arcs = [(0, cy1, R1, 30, 150),
                (cx2_left, cy2, R2, 90, 180),
                (-cx2_left, cy2, R2, 0, 90)]
        n = 30
        top_path = []
        for i in range(n + 1):
            a = 180.0 * i / n
            rad = np.radians(a)
            top_path.append((R1 * np.cos(rad), cy1 + R1 * np.sin(rad), a))
        side_left = [(x0, wall_h - i * (wall_h - y0) / 10) for i in range(11)]
        side_right = [(x1, wall_h - i * (wall_h - y0) / 10) for i in range(11)]
        return {"lines": lines, "arcs": arcs, "top_path": top_path,
                "side_lines": {"left": side_left, "right": side_right},
                "wall_h": wall_h}

    elif shape == "梯形":
        top_w = B * 0.75 + 2 * offset
        x0, x1 = -B / 2 - offset, B / 2 + offset
        y0, y1 = -offset, H + offset
        lines = [(x0, y0, x1, y0), (x0, y0, -top_w / 2, y1),
                 (-top_w / 2, y1, top_w / 2, y1), (top_w / 2, y1, x1, y0)]
        n = 15
        top_path = [(-top_w / 2 + i * top_w / n, y1, 90.0) for i in range(n + 1)]
        side_left = [(x0 + i * (-top_w / 2 - x0) / 10,
                      y0 + i * (y1 - y0) / 10) for i in range(11)]
        side_right = [(x1 + i * (top_w / 2 - x1) / 10,
                       y0 + i * (y1 - y0) / 10) for i in range(11)]
        return {"lines": lines, "arcs": [], "top_path": top_path,
                "side_lines": {"left": side_left, "right": side_right},
                "wall_h": y1}

    elif shape == "马蹄形":
        r_top = B / 2 + offset
        r_bot = B / 2 + offset
        wall_h = H - B / 2
        x0, x1 = -B / 2 - offset, B / 2 + offset
        lines = [(x0, 0, x0, wall_h), (x1, wall_h, x1, 0)]
        arcs = [(0, wall_h, r_top, 0, 180), (0, 0, r_bot, 180, 360)]
        n = 24
        top_path = []
        for i in range(n + 1):
            a = 180.0 * i / n
            rad = np.radians(a)
            top_path.append((r_top * np.cos(rad),
                             wall_h + r_top * np.sin(rad), a))
        side_left = [(x0, wall_h - i * wall_h / 10) for i in range(11)]
        side_right = [(x1, wall_h - i * wall_h / 10) for i in range(11)]
        return {"lines": lines, "arcs": arcs, "top_path": top_path,
                "side_lines": {"left": side_left, "right": side_right},
                "wall_h": wall_h}

    elif shape == "圆形":
        r = max(B, H) / 2 + offset
        cy = max(B, H) / 2
        if r < 0.01:
            r = 0.01
        arcs = [(0, cy, r, 0, 360)]
        n = 36
        top_path = []
        for i in range(n + 1):
            a = 180.0 * i / n
            rad = np.radians(a)
            top_path.append((r * np.cos(rad), cy + r * np.sin(rad), a))
        side_left, side_right = [], []
        for i in range(6):
            a1 = 180 - i * 18
            a2 = i * 18
            side_left.append((r * np.cos(np.radians(a1)),
                              cy + r * np.sin(np.radians(a1))))
            side_right.append((r * np.cos(np.radians(a2)),
                               cy + r * np.sin(np.radians(a2))))
        return {"lines": [], "arcs": arcs, "top_path": top_path,
                "side_lines": {"left": side_left, "right": side_right},
                "wall_h": cy}

    x0, x1 = -B / 2 - offset, B / 2 + offset
    y0, y1 = -offset, H + offset
    lines = [(x0, y0, x1, y0), (x1, y0, x1, y1),
             (x1, y1, x0, y1), (x0, y1, x0, y0)]
    return {"lines": lines, "arcs": [], "top_path": [],
            "side_lines": {"left": [], "right": []}, "wall_h": y1}


# ==================== 通用：绘制断面加强示意图（Tab5 用） ====================

def draw_section_on_figure(fig, base_x, shape, Bv, Hv, spacing,
                            shot_t_mm, draw_cable, cable_sp,
                            draw_steel, steel_sp, title, is_boost):
    """
    在给定的 Plotly fig 上，以 base_x 为中心绘制一张巷道断面示意图。
    返回 (x_min, x_max, y_min, y_max)，用于坐标范围自适应。
    """
    geom = get_section_geometry(shape, Bv, Hv, offset=0.0)
    color_contour = "#2c3e50"
    color_bolt = "#e74c3c"
    color_shot = "#f39c12"
    color_cable = "#9b59b6"
    color_steel = "#3498db"

    # ---- 1) 内部填充：用闭合多边形填充断面，让图更好看 ----
    poly_x, poly_y = [], []
    # 用轮廓线构造简单闭合路径
    for (x1, y1, x2, y2) in geom["lines"]:
        poly_x += [x1 + base_x, x2 + base_x]
        poly_y += [y1, y2]
    # 如果有拱形，用顶部路径补充
    if geom["arcs"]:
        for (cx, cy, r, a1, a2) in geom["arcs"]:
            if r <= 0:
                continue
            if abs(a2 - a1) >= 359.9:
                theta = np.linspace(0, 2 * np.pi, 120)
            else:
                theta = np.linspace(np.radians(a1), np.radians(a2), 80)
            fig.add_trace(go.Scatter(
                x=base_x + cx + r * np.cos(theta),
                y=cy + r * np.sin(theta),
                mode="lines", line=dict(color=color_contour, width=3.5),
                showlegend=False, hoverinfo="skip",
            ))
        # 顶部区域色块（用直墙半圆拱简化：以 wall_h 为基座的矩形+拱形）
        if shape in ("直墙半圆拱", "三心拱"):
            r_arc = Bv / 2
            wall_h = Hv - Bv / 2 if shape == "直墙半圆拱" else Hv - Bv * 0.7 * 0.7
            theta_fill = np.linspace(0, np.pi, 80)
            fill_x = base_x + r_arc * np.cos(theta_fill)
            fill_y = wall_h + r_arc * np.sin(theta_fill)
            fig.add_trace(go.Scatter(
                x=np.concatenate([[base_x - Bv / 2], fill_x, [base_x + Bv / 2]]),
                y=np.concatenate([[0], fill_y, [0]]),
                fill="toself",
                fillcolor="rgba(236,240,241,0.5)",
                line=dict(width=0),
                showlegend=False, hoverinfo="skip",
            ))
    else:
        # 矩形断面直接填充
        fig.add_trace(go.Scatter(
            x=[base_x - Bv / 2, base_x + Bv / 2,
               base_x + Bv / 2, base_x - Bv / 2,
               base_x - Bv / 2],
            y=[0, 0, Hv, Hv, 0],
            fill="toself",
            fillcolor="rgba(236,240,241,0.5)",
            line=dict(color=color_contour, width=3.5),
            showlegend=False, hoverinfo="skip",
        ))

    # ---- 2) 矩形/梯形等直线段轮廓 ----
    for (x1, y1, x2, y2) in geom["lines"]:
        fig.add_shape(
            type="line",
            x0=x1 + base_x, y0=y1, x1=x2 + base_x, y1=y2,
            line=dict(color=color_contour, width=3.5),
        )

    # ---- 3) 喷层（用稍大的外轮廓虚线表示） ----
    t_m = shot_t_mm / 1000.0
    geom_shot = get_section_geometry(shape, Bv, Hv, offset=t_m)
    for (x1, y1, x2, y2) in geom_shot["lines"]:
        fig.add_shape(
            type="line",
            x0=x1 + base_x, y0=y1, x1=x2 + base_x, y1=y2,
            line=dict(color=color_shot, width=2.5),
        )
    for (cx, cy, r, a1, a2) in geom_shot["arcs"]:
        if r <= 0:
            continue
        if abs(a2 - a1) >= 359.9:
            theta = np.linspace(0, 2 * np.pi, 100)
        else:
            theta = np.linspace(np.radians(a1), np.radians(a2), 60)
        fig.add_trace(go.Scatter(
            x=base_x + cx + r * np.cos(theta),
            y=cy + r * np.sin(theta),
            mode="lines", line=dict(color=color_shot, width=2.5),
            showlegend=False, hoverinfo="skip",
        ))

    # ---- 4) 锚杆（顶部 + 两帮） ----
    L_bolt_draw = max(min(2.2, 0.55 * Bv), 0.7)

    # 顶部锚杆
    top_path = geom["top_path"]
    if len(top_path) >= 2:
        seg_lens_t = []
        for i in range(len(top_path) - 1):
            seg_lens_t.append(np.hypot(
                top_path[i+1][0] - top_path[i][0],
                top_path[i+1][1] - top_path[i][1]))
        total_t = sum(seg_lens_t)
        n_t = max(int(total_t / spacing) + 1, 3)
        targets_t = np.linspace(0, total_t, n_t)
        for tt in targets_t:
            acc = 0.0
            for i, s_ in enumerate(seg_lens_t):
                if acc + s_ >= tt or i == len(seg_lens_t) - 1:
                    frac = (tt - acc) / max(s_, 1e-6)
                    frac = min(max(frac, 0.0), 1.0)
                    x0 = top_path[i][0] + frac * (
                        top_path[i+1][0] - top_path[i][0])
                    y0 = top_path[i][1] + frac * (
                        top_path[i+1][1] - top_path[i][1])
                    ang = top_path[i][2]
                    rad = np.radians(ang)
                    x1 = x0 + L_bolt_draw * np.cos(rad)
                    y1 = y0 + L_bolt_draw * np.sin(rad)
                    fig.add_shape(
                        type="line",
                        x0=x0 + base_x, y0=y0,
                        x1=x1 + base_x, y1=y1,
                        line=dict(color=color_bolt, width=3),
                    )
                    # 锚杆托盘
                    fig.add_shape(
                        type="circle",
                        x0=x0 + base_x - 0.06, y0=y0 - 0.06,
                        x1=x0 + base_x + 0.06, y1=y0 + 0.06,
                        fillcolor=color_bolt,
                        line=dict(color=color_bolt, width=1),
                    )
                    break
                acc += s_

    # 两帮锚杆
    for side in ("left", "right"):
        path_s = geom["side_lines"][side]
        if len(path_s) < 2:
            continue
        seg_lens_s = []
        for i in range(len(path_s) - 1):
            seg_lens_s.append(np.hypot(
                path_s[i+1][0] - path_s[i][0],
                path_s[i+1][1] - path_s[i][1]))
        total_s = sum(seg_lens_s)
        n_s = max(int(total_s / spacing) + 1, 2)
        targets_s = np.linspace(0, total_s, n_s)
        for tt in targets_s:
            acc = 0.0
            for i, s_ in enumerate(seg_lens_s):
                if acc + s_ >= tt or i == len(seg_lens_s) - 1:
                    frac = (tt - acc) / max(s_, 1e-6)
                    frac = min(max(frac, 0.0), 1.0)
                    x0 = path_s[i][0] + frac * (
                        path_s[i+1][0] - path_s[i][0])
                    y0 = path_s[i][1] + frac * (
                        path_s[i+1][1] - path_s[i][1])
                    nx = 1.0 if x0 >= 0 else -1.0
                    x1 = x0 + L_bolt_draw * nx
                    fig.add_shape(
                        type="line",
                        x0=x0 + base_x, y0=y0,
                        x1=x1 + base_x, y1=y0,
                        line=dict(color=color_bolt, width=3),
                    )
                    fig.add_shape(
                        type="circle",
                        x0=x0 + base_x - 0.06, y0=y0 - 0.06,
                        x1=x0 + base_x + 0.06, y1=y0 + 0.06,
                        fillcolor=color_bolt,
                        line=dict(color=color_bolt, width=1),
                    )
                    break
                acc += s_

    # ---- 5) 锚索 ----
    if draw_cable and cable_sp and len(top_path) >= 2:
        L_cable_draw = max(min(3.5, 1.0 * Bv), 1.0)
        seg_lens_c = []
        for i in range(len(top_path) - 1):
            seg_lens_c.append(np.hypot(
                top_path[i+1][0] - top_path[i][0],
                top_path[i+1][1] - top_path[i][1]))
        total_c = sum(seg_lens_c)
        n_c = max(int(total_c / cable_sp) + 1, 3)
        targets_c = np.linspace(0, total_c, n_c)
        for tt in targets_c:
            acc = 0.0
            for i, s_ in enumerate(seg_lens_c):
                if acc + s_ >= tt or i == len(seg_lens_c) - 1:
                    frac = (tt - acc) / max(s_, 1e-6)
                    frac = min(max(frac, 0.0), 1.0)
                    x0 = top_path[i][0] + frac * (
                        top_path[i+1][0] - top_path[i][0])
                    y0 = top_path[i][1] + frac * (
                        top_path[i+1][1] - top_path[i][1])
                    ang = top_path[i][2]
                    rad = np.radians(ang)
                    x1 = x0 + L_cable_draw * np.cos(rad)
                    y1 = y0 + L_cable_draw * np.sin(rad)
                    fig.add_shape(
                        type="line",
                        x0=x0 + base_x, y0=y0,
                        x1=x1 + base_x, y1=y1,
                        line=dict(color=color_cable, width=3.5,
                                  dash="dot"),
                    )
                    # 锚索端部锚具（三角）
                    fig.add_trace(go.Scatter(
                        x=[x1 + base_x, x1 + base_x - 0.15,
                           x1 + base_x + 0.15, x1 + base_x],
                        y=[y1, y1 - 0.15, y1 - 0.15, y1],
                        fill="toself",
                        fillcolor=color_cable,
                        mode="lines",
                        line=dict(color=color_cable, width=1),
                        showlegend=False, hoverinfo="skip",
                    ))
                    break
                acc += s_

    # ---- 6) 钢架（内侧虚线双线） ----
    if draw_steel and steel_sp:
        geom_steel = get_section_geometry(shape, Bv, Hv, offset=-0.15)
        for (x1, y1, x2, y2) in geom_steel["lines"]:
            fig.add_shape(
                type="line",
                x0=x1 + base_x, y0=y1, x1=x2 + base_x, y1=y2,
                line=dict(color=color_steel, width=2, dash="dash"),
            )
        for (cx, cy, r, a1, a2) in geom_steel["arcs"]:
            if r <= 0:
                continue
            if abs(a2 - a1) >= 359.9:
                theta = np.linspace(0, 2 * np.pi, 100)
            else:
                theta = np.linspace(np.radians(a1), np.radians(a2), 60)
            fig.add_trace(go.Scatter(
                x=base_x + cx + r * np.cos(theta),
                y=cy + r * np.sin(theta),
                mode="lines",
                line=dict(color=color_steel, width=2, dash="dash"),
                showlegend=False, hoverinfo="skip",
            ))

    # ---- 7) 断面标题 ----
    title_color = "#e67e22" if is_boost else "#2c3e50"
    fig.add_annotation(
        x=base_x, y=Hv + max(L_bolt_draw, 3.5) + 0.8,
        text=f"<b>{title}</b>",
        showarrow=False,
        font=dict(size=14, color=title_color, family="Microsoft YaHei"),
        bgcolor="rgba(255,255,255,0.9)",
        bordercolor=title_color,
        borderwidth=2,
        borderpad=6,
    )
    # 尺寸标注
    fig.add_annotation(
        x=base_x, y=-0.6,
        text=f"B={Bv:.1f}m × H={Hv:.1f}m",
        showarrow=False,
        font=dict(size=11, color="#555"),
    )

    return (base_x - Bv / 2 - L_bolt_draw - 0.5,
            base_x + Bv / 2 + L_bolt_draw + 0.5,
            -1.2,
            Hv + max(L_bolt_draw, 3.5) + 1.5)


# ==================== DXF 图纸生成引擎 ====================

VALID_LINEWEIGHTS = {
    0, 5, 9, 13, 15, 18, 20, 25, 30, 35, 40, 50, 53, 60,
    70, 80, 90, 100, 106, 120, 140, 158, 200, 211,
}


def _safe_lineweight(lw):
    if lw in VALID_LINEWEIGHTS:
        return lw
    return min(VALID_LINEWEIGHTS, key=lambda x: abs(x - lw))


def setup_dxf_document():
    doc = ezdxf.new(dxfversion="R2010", setup=True)
    doc.header['$INSUNITS'] = 6
    doc.header['$LTSCALE'] = 0.1
    doc.header['$MEASUREMENT'] = 1

    try:
        if "HZ" not in doc.styles:
            doc.styles.add("HZ", font="simhei.ttf")
        else:
            doc.styles.get("HZ").dxf.font = "simhei.ttf"
    except Exception:
        pass

    try:
        if "MY_DIM" not in doc.dimstyles:
            ds = doc.dimstyles.add("MY_DIM")
            ds.dxf.dimtxt = 0.18
            ds.dxf.dimasz = 0.15
            ds.dxf.dimexe = 0.08
            ds.dxf.dimexo = 0.05
            ds.dxf.dimgap = 0.05
            ds.dxf.dimdec = 2
            ds.dxf.dimtad = 1
            ds.dxf.dimclrt = 3
            ds.dxf.dimclrd = 3
            ds.dxf.dimclre = 3
    except Exception:
        pass

    msp = doc.modelspace()

    layers = {
        "01_巷道轮廓":   {"color": 7,   "linetype": "CONTINUOUS", "lw": 50},
        "02_锚杆":       {"color": 1,   "linetype": "CONTINUOUS", "lw": 35},
        "03_锚索":       {"color": 6,   "linetype": "CONTINUOUS", "lw": 35},
        "04_钢架":       {"color": 5,   "linetype": "DASHED",     "lw": 35},
        "05_喷层":       {"color": 30,  "linetype": "CONTINUOUS", "lw": 50},
        "06_尺寸标注":   {"color": 3,   "linetype": "CONTINUOUS", "lw": 18},
        "07_文字说明":   {"color": 7,   "linetype": "CONTINUOUS", "lw": 18},
        "08_中心线":     {"color": 8,   "linetype": "CENTER",     "lw": 18},
        "09_图框":       {"color": 7,   "linetype": "CONTINUOUS", "lw": 70},
        "10_填充":       {"color": 252, "linetype": "CONTINUOUS", "lw": 9},
        "11_图例":       {"color": 7,   "linetype": "CONTINUOUS", "lw": 25},
        "12_图签":       {"color": 7,   "linetype": "CONTINUOUS", "lw": 35},
    }

    for name, cfg in layers.items():
        if name not in doc.layers:
            try:
                doc.layers.add(name, color=cfg["color"],
                               linetype=cfg["linetype"],
                               lineweight=_safe_lineweight(cfg["lw"]))
            except Exception:
                doc.layers.add(name, color=cfg["color"],
                               lineweight=_safe_lineweight(cfg["lw"]))
    return doc, msp


def _draw_geometry(msp, geom, layer):
    for (x1, y1, x2, y2) in geom["lines"]:
        msp.add_line((x1, y1), (x2, y2), dxfattribs={"layer": layer})
    for (cx, cy, r, a1, a2) in geom["arcs"]:
        if r <= 0:
            continue
        if abs(a2 - a1) >= 359.9:
            msp.add_circle(center=(cx, cy), radius=r,
                           dxfattribs={"layer": layer})
        else:
            msp.add_arc(center=(cx, cy), radius=r,
                        start_angle=a1, end_angle=a2,
                        dxfattribs={"layer": layer})


def _polyline_from_geometry(shape, B, H, offset=0.0, n_arc=24):
    if shape == "矩形":
        x0, x1 = -B/2 - offset, B/2 + offset
        y0, y1 = -offset, H + offset
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    if shape == "直墙半圆拱":
        r = B/2 + offset
        wall_h = H - B/2
        x0, x1 = -B/2 - offset, B/2 + offset
        y0 = -offset
        pts = [(x0, y0), (x0, wall_h)]
        for i in range(n_arc + 1):
            a = 180 - 180 * i / n_arc
            pts.append((r * np.cos(np.radians(a)),
                        wall_h + r * np.sin(np.radians(a))))
        pts += [(x1, wall_h), (x1, y0)]
        return pts
    if shape == "三心拱":
        R1 = B/2 + offset
        wall_h = H - R1 * 0.7
        cy1 = wall_h + R1 * 0.3
        x0, x1 = -B/2 - offset, B/2 + offset
        y0 = -offset
        pts = [(x0, y0), (x0, wall_h)]
        for i in range(n_arc + 1):
            a = 180 - 180 * i / n_arc
            pts.append((R1 * np.cos(np.radians(a)),
                        cy1 + R1 * np.sin(np.radians(a))))
        pts += [(x1, wall_h), (x1, y0)]
        return pts
    if shape == "梯形":
        top_w = B * 0.75 + 2 * offset
        x0, x1 = -B/2 - offset, B/2 + offset
        y0, y1 = -offset, H + offset
        return [(x0, y0), (x1, y0), (top_w/2, y1), (-top_w/2, y1)]
    if shape == "马蹄形":
        r = B/2 + offset
        wall_h = H - B/2
        pts = []
        for i in range(n_arc + 1):
            a = 180 + 180 * i / n_arc
            pts.append((r * np.cos(np.radians(a)), r * np.sin(np.radians(a))))
        pts.append((B/2 + offset, wall_h))
        for i in range(n_arc + 1):
            a = 0 + 180 * i / n_arc
            pts.append((r * np.cos(np.radians(a)),
                        wall_h + r * np.sin(np.radians(a))))
        pts.append((-B/2 - offset, 0))
        return pts
    if shape == "圆形":
        r = max(B, H)/2 + offset
        cy = max(B, H)/2
        pts = []
        for i in range(2 * n_arc + 1):
            a = 360 * i / (2 * n_arc)
            pts.append((r * np.cos(np.radians(a)),
                        cy + r * np.sin(np.radians(a))))
        return pts
    return []


def draw_tunnel_outline(msp, B, H, shape, t_shot):
    t_m = t_shot / 1000.0
    geom = get_section_geometry(shape, B, H, offset=0.0)
    _draw_geometry(msp, geom, "01_巷道轮廓")
    geom_out = get_section_geometry(shape, B, H, offset=t_m)
    _draw_geometry(msp, geom_out, "05_喷层")

    try:
        pts_inner = _polyline_from_geometry(shape, B, H, offset=0.0)
        if pts_inner:
            hatch = msp.add_hatch(color=254, dxfattribs={"layer": "10_填充"})
            hatch.set_solid_fill(color=254)
            hatch.paths.add_polyline_path(pts_inner, is_closed=True)
    except Exception:
        pass

    try:
        pts_outer = _polyline_from_geometry(shape, B, H, offset=t_m)
        if pts_outer:
            hatch2 = msp.add_hatch(color=30, dxfattribs={"layer": "10_填充"})
            hatch2.set_pattern_fill("ANSI31", scale=0.05, color=30)
            hatch2.paths.add_polyline_path(pts_outer, is_closed=True)
    except Exception:
        pass


def draw_centerlines(msp, B, H, shape):
    ext = H * 0.15
    try:
        msp.add_line((0, -ext), (0, H + ext),
                     dxfattribs={"layer": "08_中心线", "linetype": "CENTER"})
        msp.add_line((-B/2 - ext, H/2), (B/2 + ext, H/2),
                     dxfattribs={"layer": "08_中心线", "linetype": "CENTER"})
    except Exception:
        msp.add_line((0, -ext), (0, H + ext),
                     dxfattribs={"layer": "08_中心线"})
        msp.add_line((-B/2 - ext, H/2), (B/2 + ext, H/2),
                     dxfattribs={"layer": "08_中心线"})


def _place_along_path(msp, path, spacing, L_bolt, layer,
                      normal_mode="normal", draw_bolt=True, bolt_d=0.03):
    if len(path) < 2:
        return []
    seg_lens = []
    for i in range(len(path) - 1):
        seg_lens.append(np.hypot(path[i+1][0] - path[i][0],
                                 path[i+1][1] - path[i][1]))
    total_len = sum(seg_lens)
    if total_len <= 0:
        return []
    n = max(int(total_len / spacing) + 1, 2)
    targets = np.linspace(0, total_len, n)
    placed = []

    for t in targets:
        acc = 0.0
        for i, seg in enumerate(seg_lens):
            if acc + seg >= t or i == len(seg_lens) - 1:
                frac = (t - acc) / max(seg, 1e-6)
                frac = min(max(frac, 0.0), 1.0)
                x0 = path[i][0] + frac * (path[i+1][0] - path[i][0])
                y0 = path[i][1] + frac * (path[i+1][1] - path[i][1])

                if normal_mode == "top" and len(path[i]) >= 3:
                    ang = path[i][2]
                    rad = np.radians(ang)
                    nx, ny = np.cos(rad), np.sin(rad)
                else:
                    nx = 1.0 if x0 >= 0 else -1.0
                    ny = 0.0

                x1 = x0 + L_bolt * nx
                y1 = y0 + L_bolt * ny
                perp_x, perp_y = -ny, nx

                if draw_bolt:
                    half_d = bolt_d / 2
                    msp.add_line((x0 + half_d * perp_x, y0 + half_d * perp_y),
                                 (x1 + half_d * perp_x, y1 + half_d * perp_y),
                                 dxfattribs={"layer": layer})
                    msp.add_line((x0 - half_d * perp_x, y0 - half_d * perp_y),
                                 (x1 - half_d * perp_x, y1 - half_d * perp_y),
                                 dxfattribs={"layer": layer})
                    tray_w = 0.13
                    tray_h = 0.04
                    c = [
                        (x0 + half_d * perp_x - tray_h * nx,
                         y0 + half_d * perp_y - tray_h * ny),
                        (x0 + half_d * perp_x + tray_h * nx,
                         y0 + half_d * perp_y + tray_h * ny),
                        (x0 - half_d * perp_x + tray_h * nx,
                         y0 - half_d * perp_y + tray_h * ny),
                        (x0 - half_d * perp_x - tray_h * nx,
                         y0 - half_d * perp_y - tray_h * ny),
                    ]
                    msp.add_lwpolyline(c, dxfattribs={"layer": layer,
                                                      "closed": True})
                    tri_d = 0.09
                    msp.add_solid([(x1, y1),
                                   (x1 - tri_d * nx + tri_d * perp_x,
                                    y1 - tri_d * ny + tri_d * perp_y),
                                   (x1 - tri_d * nx - tri_d * perp_x,
                                    y1 - tri_d * ny - tri_d * perp_y)],
                                  dxfattribs={"layer": layer})
                else:
                    msp.add_line((x0, y0), (x1, y1),
                                 dxfattribs={"layer": layer})

                placed.append((x0, y0, x1, y1, nx, ny))
                break
            acc += seg
    return placed


def draw_rock_bolts(msp, B, H, shape, spacing, row_spacing, L_bolt):
    layer = "02_锚杆"
    spacing = max(spacing, 0.3)
    row_spacing = max(row_spacing, 0.3)
    L_draw = max(min(L_bolt, 0.55 * B), 0.6)

    geom = get_section_geometry(shape, B, H, offset=0.0)
    _place_along_path(msp, geom["top_path"], spacing, L_draw, layer,
                      normal_mode="top", draw_bolt=True)
    for side in ("left", "right"):
        _place_along_path(msp, geom["side_lines"][side], row_spacing,
                          L_draw, layer, normal_mode="side",
                          draw_bolt=True)


def _draw_break_line(msp, x, y, nx, ny, layer):
    perp_x, perp_y = -ny, nx
    w = 0.08
    pts = [
        (x + w * perp_x, y + w * perp_y),
        (x + w * 0.5 * nx - w * 0.4 * perp_x,
         y + w * 0.5 * ny - w * 0.4 * perp_y),
        (x - w * 0.5 * nx + w * 0.4 * perp_x,
         y - w * 0.5 * ny + w * 0.4 * perp_y),
        (x - w * perp_x, y - w * perp_y),
    ]
    msp.add_lwpolyline(pts, dxfattribs={"layer": layer})


def draw_cables(msp, B, H, shape, cable_spacing, L_cable):
    layer = "03_锚索"
    cable_spacing = max(cable_spacing, 0.3)
    L_draw = max(min(L_cable, 1.0 * B), 0.8)
    truncated = L_cable > L_draw + 1e-6

    geom = get_section_geometry(shape, B, H, offset=0.0)
    top_path = geom["top_path"]
    if len(top_path) < 2:
        return

    seg_lens = []
    for i in range(len(top_path) - 1):
        seg_lens.append(np.hypot(top_path[i+1][0] - top_path[i][0],
                                 top_path[i+1][1] - top_path[i][1]))
    total_len = sum(seg_lens)
    n_cables = max(int(total_len / cable_spacing) + 1, 3)
    targets = np.linspace(0, total_len, n_cables)

    for t in targets:
        acc = 0.0
        for i, seg in enumerate(seg_lens):
            if acc + seg >= t or i == len(seg_lens) - 1:
                frac = (t - acc) / max(seg, 1e-6)
                frac = min(max(frac, 0.0), 1.0)
                x0 = top_path[i][0] + frac * (top_path[i+1][0] - top_path[i][0])
                y0 = top_path[i][1] + frac * (top_path[i+1][1] - top_path[i][1])
                ang = top_path[i][2]
                rad = np.radians(ang)
                nx, ny = np.cos(rad), np.sin(rad)
                perp_x, perp_y = -ny, nx
                x1 = x0 + L_draw * nx
                y1 = y0 + L_draw * ny

                half_d = 0.02
                msp.add_line((x0 + half_d * perp_x, y0 + half_d * perp_y),
                             (x1 + half_d * perp_x, y1 + half_d * perp_y),
                             dxfattribs={"layer": layer})
                msp.add_line((x0 - half_d * perp_x, y0 - half_d * perp_y),
                             (x1 - half_d * perp_x, y1 - half_d * perp_y),
                             dxfattribs={"layer": layer})

                tray_len = 0.15
                tray_w = 0.08
                xb, yb = x0 + tray_len * nx, y0 + tray_len * ny
                c = [
                    (xb + tray_w * perp_x, yb + tray_w * perp_y),
                    (xb - tray_w * perp_x, yb - tray_w * perp_y),
                    (x1 - tray_w * perp_x, y1 - tray_w * perp_y),
                    (x1 + tray_w * perp_x, y1 + tray_w * perp_y),
                ]
                msp.add_lwpolyline(c, dxfattribs={"layer": layer, "closed": True})

                tri_d = 0.1
                msp.add_solid([(x1, y1),
                               (x1 - tri_d * nx + 0.06 * perp_x,
                                y1 - tri_d * ny + 0.06 * perp_y),
                               (x1 - tri_d * nx - 0.06 * perp_x,
                                y1 - tri_d * ny - 0.06 * perp_y)],
                              dxfattribs={"layer": layer})

                if truncated:
                    _draw_break_line(msp, x1, y1, nx, ny, layer)
                break
            acc += seg


def draw_steel_arch(msp, B, H, shape, spacing):
    layer = "04_钢架"
    offset = -0.15
    geom = get_section_geometry(shape, B, H, offset=offset)
    _draw_geometry(msp, geom, layer)
    geom2 = get_section_geometry(shape, B, H, offset=offset - 0.05)
    _draw_geometry(msp, geom2, layer)


def draw_dimensions(msp, B, H, shape):
    layer = "06_尺寸标注"
    offset = max(B * 0.10, 0.35)
    try:
        dim1 = msp.add_aligned_dim(p1=(-B/2, 0), p2=(B/2, 0),
                                   distance=-offset,
                                   dxfattribs={"layer": layer,
                                               "dimstyle": "MY_DIM"})
        dim1.render()
    except Exception:
        pass
    try:
        dim2 = msp.add_aligned_dim(p1=(B/2, 0), p2=(B/2, H),
                                   distance=-offset,
                                   dxfattribs={"layer": layer,
                                               "dimstyle": "MY_DIM"})
        dim2.render()
    except Exception:
        pass
    if shape in ("直墙半圆拱", "三心拱", "马蹄形"):
        wall_h = (H - B/2) if shape in ("直墙半圆拱", "马蹄形") else (H - B/2*0.7)
        try:
            dim3 = msp.add_aligned_dim(p1=(-B/2, wall_h), p2=(-B/2, 0),
                                       distance=offset,
                                       dxfattribs={"layer": layer,
                                                   "dimstyle": "MY_DIM"})
            dim3.render()
        except Exception:
            pass


def draw_text_annotations(msp, snap, support, bolt_df, shot, cable, steel,
                          B, H):
    layer = "07_文字说明"
    box_layer = "12_图签"

    text_h = max(B * 0.035, 0.13)
    line_h = text_h * 1.7
    box_w = max(B * 0.75, 2.8)
    x0 = B/2 + max(B * 0.28, 1.0)
    y0 = H + max(H * 0.15, 0.6)

    rows = [
        ("工程名称", snap['name']),
        ("断面形状", snap['shape']),
        ("断面尺寸", f"{B:.2f} × {H:.2f} m"),
        ("围岩级别", snap['rock'].split('（')[0]),
        ("埋深", f"{snap['depth']:.0f} m"),
        ("推荐支护", support['推荐方案']),
    ]
    bolt_kv = {}
    for _, row in bolt_df.iterrows():
        bolt_kv[row['参数']] = row['取值']
    rows += [
        ("锚杆规格", str(bolt_kv.get("锚杆规格", "-"))),
        ("顶锚杆长", f"{bolt_kv.get('顶锚杆总长(m)', '-')} m"),
        ("帮锚杆长", f"{bolt_kv.get('帮锚杆总长(m)', '-')} m"),
        ("间排距", f"{bolt_kv.get('间排距(m×m)', '-')} m"),
        ("预紧力", f"{bolt_kv.get('预紧力(kN)', '-')} kN"),
    ]
    if cable:
        rows += [
            ("锚索规格", str(cable['锚索规格'])),
            ("锚索长度", f"{cable['锚索长度(m)']} m"),
            ("锚索间排距", str(cable['锚索间排距(m)'])),
            ("锚索预紧力", f"{cable['预紧力(kN)']} kN"),
        ]
    rows += [
        ("喷层厚度", f"{shot['设计喷层厚度(mm)']} mm"),
        ("混凝土等级", str(shot['混凝土强度等级'])),
        ("钢筋网", str(shot['钢筋网规格'])),
    ]
    if steel:
        rows += [
            ("钢架型号", str(steel['钢架型号'])),
            ("支架间距", f"{steel['支架间距(m)']} m"),
            ("设计可缩量", f"{steel['设计可缩量(mm)']} mm"),
        ]

    n_rows = len(rows)
    box_h = line_h * (n_rows + 1) + 0.3
    y_top = y0
    y_bot = y0 - box_h

    msp.add_lwpolyline(
        [(x0, y_top), (x0 + box_w, y_top),
         (x0 + box_w, y_bot), (x0, y_bot), (x0, y_top)],
        dxfattribs={"layer": box_layer}
    )
    msp.add_line((x0, y_top - line_h), (x0 + box_w, y_top - line_h),
                 dxfattribs={"layer": box_layer})
    msp.add_line((x0 + box_w * 0.4, y_top - line_h),
                 (x0 + box_w * 0.4, y_bot),
                 dxfattribs={"layer": box_layer})

    try:
        msp.add_text("支护参数表", dxfattribs={"layer": layer,
                                              "height": text_h * 1.2,
                                              "style": "HZ"}
                     ).set_placement((x0 + box_w / 2,
                                      y_top - line_h * 0.75),
                                     align=TextEntityAlignment.MIDDLE_CENTER)
    except Exception:
        pass

    for i, (k, v) in enumerate(rows):
        y = y_top - line_h * (i + 1.5)
        try:
            msp.add_text(str(k), dxfattribs={"layer": layer,
                                            "height": text_h, "style": "HZ"}
                         ).set_placement((x0 + 0.1, y),
                                         align=TextEntityAlignment.LEFT)
            msp.add_text(str(v), dxfattribs={"layer": layer,
                                            "height": text_h, "style": "HZ"}
                         ).set_placement((x0 + box_w * 0.42, y),
                                         align=TextEntityAlignment.LEFT)
        except Exception:
            pass


def draw_legend(msp, B, H, has_cable, has_steel,
                x_start=None, y_start=None):
    layer = "11_图例"
    if x_start is None:
        x_start = -B/2 - max(B * 0.85, 2.5)
    if y_start is None:
        y_start = H + max(H * 0.15, 0.6)

    items = [("锚杆", "02_锚杆"),
             ("喷层", "05_喷层"),
             ("巷道轮廓", "01_巷道轮廓")]
    if has_cable:
        items.insert(1, ("锚索", "03_锚索"))
    if has_steel:
        items.insert(2, ("钢架", "04_钢架"))

    box_w = max(B * 0.4, 1.5)
    line_h = max(B * 0.09, 0.32)
    text_h = max(B * 0.035, 0.13)
    box_h = line_h * (len(items) + 1) + 0.2
    x0, y_top = x_start, y_start
    y_bot = y_top - box_h

    msp.add_lwpolyline(
        [(x0, y_top), (x0 + box_w, y_top),
         (x0 + box_w, y_bot), (x0, y_bot), (x0, y_top)],
        dxfattribs={"layer": layer}
    )
    try:
        msp.add_text("图例", dxfattribs={"layer": layer,
                                        "height": text_h * 1.3,
                                        "style": "HZ"}
                     ).set_placement((x0 + box_w/2, y_top - line_h*0.5),
                                     align=TextEntityAlignment.MIDDLE_CENTER)
    except Exception:
        pass

    for i, (name, lay) in enumerate(items):
        y = y_top - line_h * (i + 1.5)
        msp.add_line((x0 + 0.15, y), (x0 + box_w * 0.5, y),
                     dxfattribs={"layer": lay})
        try:
            msp.add_text(name, dxfattribs={"layer": layer,
                                           "height": text_h, "style": "HZ"}
                         ).set_placement((x0 + box_w * 0.55, y - text_h * 0.4),
                                         align=TextEntityAlignment.LEFT)
        except Exception:
            pass


def draw_title_block(msp, x_right, y_bottom, tunnel_name, shape_name, scale=1.0):
    layer = "12_图签"
    tb_w = 4.5 * scale
    tb_h = 1.6 * scale
    text_h = 0.14 * scale
    x0 = x_right - tb_w
    y0 = y_bottom

    msp.add_lwpolyline(
        [(x0, y0), (x0 + tb_w, y0), (x0 + tb_w, y0 + tb_h),
         (x0, y0 + tb_h), (x0, y0)],
        dxfattribs={"layer": layer}
    )
    for i in [0.25, 0.5, 0.75]:
        msp.add_line((x0, y0 + tb_h * i), (x0 + tb_w, y0 + tb_h * i),
                     dxfattribs={"layer": layer})
    msp.add_line((x0 + tb_w * 0.55, y0), (x0 + tb_w * 0.55, y0 + tb_h),
                 dxfattribs={"layer": layer})

    data = [
        ("图名", f"{shape_name} 支护断面图"),
        ("工程", tunnel_name),
        ("图号", f"SD-{datetime.now().strftime('%Y%m%d')}-01"),
        ("比例", "1:50"),
        ("日期", datetime.now().strftime('%Y-%m-%d')),
    ]
    for i, (k, v) in enumerate(data):
        y = y0 + tb_h - tb_h * 0.2 * (i + 0.5) * 1.25
        try:
            msp.add_text(k, dxfattribs={"layer": layer,
                                        "height": text_h, "style": "HZ"}
                         ).set_placement((x0 + 0.08 * scale, y),
                                         align=TextEntityAlignment.LEFT)
            msp.add_text(str(v), dxfattribs={"layer": layer,
                                            "height": text_h, "style": "HZ"}
                         ).set_placement((x0 + tb_w * 0.57, y),
                                         align=TextEntityAlignment.LEFT)
        except Exception:
            pass


def draw_frame(msp, min_x, min_y, max_x, max_y, title, scale=1.0):
    layer = "09_图框"
    margin = 0.5 * scale

    msp.add_lwpolyline(
        [(min_x - margin, min_y - margin),
         (max_x + margin, min_y - margin),
         (max_x + margin, max_y + margin),
         (min_x - margin, max_y + margin),
         (min_x - margin, min_y - margin)],
        dxfattribs={"layer": layer}
    )
    m2 = margin + 0.2 * scale
    msp.add_lwpolyline(
        [(min_x - m2, min_y - m2),
         (max_x + m2, min_y - m2),
         (max_x + m2, max_y + m2),
         (min_x - m2, max_y + m2),
         (min_x - m2, min_y - m2)],
        dxfattribs={"layer": layer}
    )
    try:
        msp.add_text(title,
                     dxfattribs={"layer": layer, "height": 0.35 * scale,
                                 "style": "HZ"}
                     ).set_placement(((min_x + max_x) / 2, max_y + margin - 0.4 * scale),
                                     align=TextEntityAlignment.CENTER)
    except Exception:
        pass


def generate_dxf(snap, support, bolt_df, shot, cable, steel, p):
    doc, msp = setup_dxf_document()

    B, H = snap['B'], snap['H']
    shape = snap['shape']
    t_shot = shot['设计喷层厚度(mm)']

    spacing, row_spacing = 0.8, 0.8
    L_bolt_top = 2.2
    for _, row in bolt_df.iterrows():
        if row['参数'] == "间排距(m×m)":
            s = str(row['取值'])
            if "×" in s:
                sp, rsp = s.split("×")
                try:
                    spacing = float(sp)
                    row_spacing = float(rsp)
                except Exception:
                    pass
        elif row['参数'] == "顶锚杆总长(m)":
            try:
                L_bolt_top = float(row['取值'])
            except Exception:
                pass

    L_bolt_draw = max(min(L_bolt_top, 0.55 * B), 0.6)
    L_cable_draw = 0.0
    L_cable_real = 0.0
    if cable:
        try:
            L_cable_real = float(cable['锚索长度(m)'])
            L_cable_draw = max(min(L_cable_real, 1.0 * B), 0.8)
        except Exception:
            pass

    draw_tunnel_outline(msp, B, H, shape, t_shot)
    draw_centerlines(msp, B, H, shape)
    draw_rock_bolts(msp, B, H, shape, spacing, row_spacing, L_bolt_top)

    if cable:
        try:
            cable_sp = float(cable['锚索间排距(m)'].split("×")[0])
            draw_cables(msp, B, H, shape, cable_sp, L_cable_real)
        except Exception:
            pass

    if steel:
        try:
            steel_sp = float(steel['支架间距(m)'])
            draw_steel_arch(msp, B, H, shape, steel_sp)
        except Exception:
            pass

    draw_dimensions(msp, B, H, shape)
    draw_text_annotations(msp, snap, support, bolt_df, shot, cable, steel, B, H)
    draw_legend(msp, B, H,
                has_cable=cable is not None,
                has_steel=steel is not None)

    extra = max(L_bolt_draw, L_cable_draw, 0.6)
    left_pad  = max(B * 0.85, 2.5)
    right_pad = max(B * 0.85, 3.0)
    top_pad   = max(H * 0.20, 0.8)
    bot_pad   = max(H * 0.25, 0.8)

    min_x = -B/2 - extra - left_pad
    max_x =  B/2 + extra + right_pad
    min_y = -extra - bot_pad
    max_y =  H + extra + top_pad

    scale = max(B / 4.5, 0.8)
    draw_frame(msp, min_x, min_y, max_x, max_y,
               f"{snap['name']} 支护断面图（{shape}）",
               scale=scale)
    draw_title_block(msp, max_x, min_y, snap['name'], shape, scale=scale)

    buf = io.StringIO()
    doc.write(buf)
    buf.seek(0)
    return io.BytesIO(buf.getvalue().encode("utf-8"))


# ==================== DXF → PNG 预览渲染 ====================

def dxf_to_png_bytes(dxf_buffer, dpi=150, figsize=(14, 10)):
    dxf_buffer.seek(0)
    text = dxf_buffer.read()
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="ignore")
    doc = ezdxf.read(io.StringIO(text))
    msp = doc.modelspace()

    fig = plt.figure(figsize=figsize, dpi=dpi, facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor("white")
    ax.set_axis_off()

    try:
        ctx = RenderContext(doc)
        backend = MatplotlibBackend(ax)
        Frontend(ctx, backend).draw_layout(msp, finalize=True)
    except Exception as e:
        plt.close(fig)
        raise e

    png_buf = io.BytesIO()
    fig.savefig(png_buf, format="png", facecolor="white",
                bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)
    png_buf.seek(0)
    return png_buf.getvalue()


# ==================== 主页面 ====================
st.markdown('<div class="main-header">⛏️ 井下巷道智能支护方案设计系统</div>',
            unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 围岩分级", "📐 压力计算",
    "🎯 支护方案", "📄 设计报告",
    "⚠️ 特殊段加强支护"
])


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

    si = calc_stability_index(rock_class, depth, dynamic_pressure,
                              has_fault, has_water)
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
        st.markdown('<div class="danger-box">🔴 <b>极不稳定</b>：强支护 + 超前支护 + 可缩性支架</div>',
                    unsafe_allow_html=True)
    elif si < 50:
        st.markdown('<div class="warning-box">🟠 <b>不稳定</b>：锚网喷 + 锚索/钢架联合支护</div>',
                    unsafe_allow_html=True)
    elif si < 70:
        st.markdown('<div class="warning-box">🟡 <b>中等稳定</b>：锚网喷为主，局部加强</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<div class="success-box">🟢 <b>稳定</b>：常规锚杆/锚网喷即可</div>',
                    unsafe_allow_html=True)


# ---------- Tab2 ----------
with tab2:
    if run_button:
        pressure = calc_rock_pressure(B, H, depth, rock_class, gamma_rock, lam,
                                      has_water, has_fault, dynamic_pressure, phi)
        stability_text = "稳定"
        si = calc_stability_index(rock_class, depth, dynamic_pressure,
                                  has_fault, has_water)
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
            "total_length": total_length,
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
            st.markdown(f'<div class="warning-box">{w}</div>',
                        unsafe_allow_html=True)

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

        d_calc = calc_bolt_diameter(bolt["Q_design"], bolt["σs"])
        bolt_len = calc_bolt_length(snap['B'], snap['H'], f_val, snap['phi'])

        L2_top = bolt_len["顶锚杆有效长度 L2(m)"]
        a_max = calc_bolt_spacing(bolt["Q_design"], L2_top, snap['gamma'])

        D_m = bolt["d"] / 1000.0
        a_coupled = calc_bolt_max_spacing_coupled(
            L_bolt_m=bolt_len["顶锚杆总长(m)"],
            P_pre_kN=60.0,
            D_m=D_m,
            c_r_MPa=snap['c_r'],
            phi_deg=snap['phi'],
            Q_design_kN=bolt["Q_design"],
        )

        spacing_final = min(a_max, a_coupled, 1.2)
        spacing_final = round(max(spacing_final, 0.6), 1)
        row_spacing = spacing_final

        check = calc_anchor_capacity_check(
            bolt["Q_design"], qd, spacing_final, row_spacing
        )

        bolt_rows = [
            {"参数": "锚杆规格", "取值": bolt_key, "说明": "左旋无纵筋螺纹钢"},
            {"参数": "杆体直径(mm)", "取值": bolt["d"],
             "说明": f"反算值 d_calc={d_calc}mm"},
            {"参数": "屈服强度(MPa)", "取值": bolt["σs"], "说明": "BHRB400"},
            {"参数": "截面积(mm²)", "取值": bolt["A"], "说明": ""},
            {"参数": "屈服荷载(kN)", "取值": bolt["Q_yield"],
             "说明": "≥锚固力要求"},
            {"参数": "设计锚固力(kN)", "取值": bolt["Q_design"],
             "说明": "规范要求≥屈服力80%"},
            {"参数": "顶锚杆有效长度 L2(m)",
             "取值": bolt_len["顶锚杆有效长度 L2(m)"], "说明": "f≥3: B/2f"},
            {"参数": "顶锚杆总长(m)", "取值": bolt_len["顶锚杆总长(m)"],
             "说明": "L1+L2+L3"},
            {"参数": "帮锚杆总长(m)", "取值": bolt_len["帮锚杆总长(m)"],
             "说明": ""},
            {"参数": "间排距(m×m)", "取值": f"{spacing_final}×{row_spacing}",
             "说明": f"悬吊校核 a_max={a_max}m，耦合校核 a_c={a_coupled}m"},
            {"参数": "单根锚杆荷载(kN)", "取值": check["单根锚杆实际荷载(kN)"],
             "说明": ""},
            {"参数": "安全系数", "取值": check["锚杆安全系数"],
             "说明": check["校核结果"]},
            {"参数": "预紧力(kN)", "取值": round(bolt["Q_design"] * 0.6, 0),
             "说明": "规范要求≥60kN"},
            {"参数": "锚固方式", "取值": "树脂锚固剂",
             "说明": "Z2360 + K2360 各1根"},
            {"参数": "托板规格", "取值": "150×150×8mm 拱形托板", "说明": ""},
            {"参数": "螺母", "取值": "M22 快速安装螺母", "说明": ""},
        ]
        bolt_df = pd.DataFrame(bolt_rows)
        st.dataframe(bolt_df, use_container_width=True, hide_index=True)

        cable = calc_cable_params(qd, snap['B'], snap['H'], snap['rock'],
                                  snap['c_r'], snap['phi'])
        if cable:
            st.markdown("### 🎣 锚索支护参数")
            cable_df = pd.DataFrame([{"参数": k, "取值": v}
                                     for k, v in cable.items()])
            st.dataframe(cable_df, use_container_width=True, hide_index=True)

        shot = calc_shotcrete_params(snap['rock'], qd, snap['water'],
                                     snap['fault'], snap['B'])
        st.markdown("### 🧱 喷射混凝土参数")
        shot_df = pd.DataFrame([{"参数": k, "取值": v}
                                for k, v in shot.items()])
        st.dataframe(shot_df, use_container_width=True, hide_index=True)

        steel = calc_steel_arch_params(snap['rock'], snap['B'], snap['H'],
                                       snap['dyn'], snap['fault'],
                                       snap['life'])
        if steel:
            st.markdown("### 🏗️ U型钢可缩性支架参数")
            steel_df = pd.DataFrame([{"参数": k, "取值": v}
                                     for k, v in steel.items()])
            st.dataframe(steel_df, use_container_width=True, hide_index=True)

        # Plotly 示意图
        st.markdown("### 📐 支护布置示意图")
        Bv, Hv = snap['B'], snap['H']
        fig = go.Figure()

        geom = get_section_geometry(snap['shape'], Bv, Hv, offset=0.0)
        for (x1, y1, x2, y2) in geom["lines"]:
            fig.add_shape(type="line", x0=x1, y0=y1, x1=x2, y1=y2,
                          line=dict(color="#2c3e50", width=3))
        for (cx, cy, r, a1, a2) in geom["arcs"]:
            if r <= 0:
                continue
            if abs(a2 - a1) >= 359.9:
                theta = np.linspace(0, 2 * np.pi, 100)
                fig.add_trace(go.Scatter(
                    x=cx + r * np.cos(theta), y=cy + r * np.sin(theta),
                    mode="lines", line=dict(color="#2c3e50", width=3),
                    showlegend=False))
            else:
                theta = np.linspace(np.radians(a1), np.radians(a2), 60)
                fig.add_trace(go.Scatter(
                    x=cx + r * np.cos(theta), y=cy + r * np.sin(theta),
                    mode="lines", line=dict(color="#2c3e50", width=3),
                    showlegend=False))

        L_bolt_draw = max(min(float(bolt_len["顶锚杆总长(m)"]), 0.55 * Bv), 0.6)
        top_path = geom["top_path"]
        if len(top_path) >= 2:
            seg_lens = []
            for i in range(len(top_path) - 1):
                seg_lens.append(np.hypot(top_path[i+1][0] - top_path[i][0],
                                         top_path[i+1][1] - top_path[i][1]))
            total_len = sum(seg_lens)
            n = max(int(total_len / spacing_final) + 1, 3)
            targets = np.linspace(0, total_len, n)
            for t in targets:
                acc = 0.0
                for i, seg in enumerate(seg_lens):
                    if acc + seg >= t or i == len(seg_lens) - 1:
                        frac = (t - acc) / max(seg, 1e-6)
                        frac = min(max(frac, 0.0), 1.0)
                        x0 = top_path[i][0] + frac * (top_path[i+1][0] - top_path[i][0])
                        y0 = top_path[i][1] + frac * (top_path[i+1][1] - top_path[i][1])
                        ang = top_path[i][2]
                        rad = np.radians(ang)
                        x1 = x0 + L_bolt_draw * np.cos(rad)
                        y1 = y0 + L_bolt_draw * np.sin(rad)
                        fig.add_shape(type="line", x0=x0, y0=y0, x1=x1, y1=y1,
                                      line=dict(color="#dc3545", width=3))
                        break
                    acc += seg

        for side in ("left", "right"):
            path = geom["side_lines"][side]
            if len(path) < 2:
                continue
            seg_lens = []
            for i in range(len(path) - 1):
                seg_lens.append(np.hypot(path[i+1][0] - path[i][0],
                                         path[i+1][1] - path[i][1]))
            total_len = sum(seg_lens)
            n = max(int(total_len / row_spacing) + 1, 2)
            targets = np.linspace(0, total_len, n)
            for t in targets:
                acc = 0.0
                for i, seg in enumerate(seg_lens):
                    if acc + seg >= t or i == len(seg_lens) - 1:
                        frac = (t - acc) / max(seg, 1e-6)
                        frac = min(max(frac, 0.0), 1.0)
                        x0 = path[i][0] + frac * (path[i+1][0] - path[i][0])
                        y0 = path[i][1] + frac * (path[i+1][1] - path[i][1])
                        nx = 1.0 if x0 >= 0 else -1.0
                        x1 = x0 + L_bolt_draw * nx
                        fig.add_shape(type="line", x0=x0, y0=y0, x1=x1, y1=y0,
                                      line=dict(color="#dc3545", width=3))
                        break
                    acc += seg

        if cable:
            L_cable_draw = max(min(float(cable['锚索长度(m)']), 1.0 * Bv), 0.8)
            cable_sp = float(cable['锚索间排距(m)'].split("×")[0])
            if len(top_path) >= 2:
                seg_lens = []
                for i in range(len(top_path) - 1):
                    seg_lens.append(np.hypot(top_path[i+1][0] - top_path[i][0],
                                             top_path[i+1][1] - top_path[i][1]))
                total_len = sum(seg_lens)
                n = max(int(total_len / cable_sp) + 1, 3)
                targets = np.linspace(0, total_len, n)
                for t in targets:
                    acc = 0.0
                    for i, seg in enumerate(seg_lens):
                        if acc + seg >= t or i == len(seg_lens) - 1:
                            frac = (t - acc) / max(seg, 1e-6)
                            frac = min(max(frac, 0.0), 1.0)
                            x0 = top_path[i][0] + frac * (top_path[i+1][0] - top_path[i][0])
                            y0 = top_path[i][1] + frac * (top_path[i+1][1] - top_path[i][1])
                            ang = top_path[i][2]
                            rad = np.radians(ang)
                            x1 = x0 + L_cable_draw * np.cos(rad)
                            y1 = y0 + L_cable_draw * np.sin(rad)
                            fig.add_shape(type="line", x0=x0, y0=y0, x1=x1, y1=y1,
                                          line=dict(color="#8e44ad", width=3,
                                                    dash="dot"))
                            break
                        acc += seg

        if steel:
            geom_in = get_section_geometry(snap['shape'], Bv, Hv, offset=-0.12)
            for (x1, y1, x2, y2) in geom_in["lines"]:
                fig.add_shape(type="line", x0=x1, y0=y1, x1=x2, y1=y2,
                              line=dict(color="#3498db", width=2, dash="dash"))
            for (cx, cy, r, a1, a2) in geom_in["arcs"]:
                if r <= 0:
                    continue
                theta = np.linspace(np.radians(a1), np.radians(a2), 60)
                fig.add_trace(go.Scatter(
                    x=cx + r * np.cos(theta), y=cy + r * np.sin(theta),
                    mode="lines",
                    line=dict(color="#3498db", width=2, dash="dash"),
                    showlegend=False))

        geom_out = get_section_geometry(snap['shape'], Bv, Hv, offset=0.05)
        for (x1, y1, x2, y2) in geom_out["lines"]:
            fig.add_shape(type="line", x0=x1, y0=y1, x1=x2, y1=y2,
                          line=dict(color="#f39c12", width=2))
        for (cx, cy, r, a1, a2) in geom_out["arcs"]:
            if r <= 0:
                continue
            if abs(a2 - a1) >= 359.9:
                theta = np.linspace(0, 2 * np.pi, 100)
                fig.add_trace(go.Scatter(
                    x=cx + r * np.cos(theta), y=cy + r * np.sin(theta),
                    mode="lines", line=dict(color="#f39c12", width=2),
                    showlegend=False))
            else:
                theta = np.linspace(np.radians(a1), np.radians(a2), 60)
                fig.add_trace(go.Scatter(
                    x=cx + r * np.cos(theta), y=cy + r * np.sin(theta),
                    mode="lines", line=dict(color="#f39c12", width=2),
                    showlegend=False))

        fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines',
                                 line=dict(color="#dc3545", width=3),
                                 name='锚杆'))
        if cable:
            fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines',
                                     line=dict(color="#8e44ad", width=3,
                                               dash='dot'),
                                     name='锚索'))
        fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines',
                                 line=dict(color="#f39c12", width=2),
                                 name='喷层'))
        if steel:
            fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines',
                                     line=dict(color="#3498db", width=2,
                                               dash='dash'),
                                     name='钢架'))

        x_extent = Bv/2 + L_bolt_draw + 0.3
        y_top_ext = Hv + L_bolt_draw + 0.3
        if cable:
            L_cable_draw_v = max(min(float(cable['锚索长度(m)']), 1.0 * Bv), 0.8)
            y_top_ext = Hv + L_cable_draw_v + 0.3

        fig.update_layout(
            title=f"{support['推荐方案']} 布置示意图（{snap['shape']}）",
            xaxis=dict(title="宽度 (m)",
                       range=[-x_extent, x_extent],
                       scaleanchor="y", scaleratio=1),
            yaxis=dict(title="高度 (m)",
                       range=[-0.5, y_top_ext + 0.3]),
            height=550,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig, use_container_width=True)

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
        report.append(f"- 巷道全长：{snap.get('total_length', 0):.0f} m")
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

        special_segs = st.session_state.get('special_segments', [])
        if special_segs:
            report.append("## 五、特殊段加强支护\n")
            report.append(f"巷道全长 {snap.get('total_length', 0):.0f} m，"
                          f"其中特殊段 {len(special_segs)} 处：\n")
            sorted_specials = sorted(special_segs, key=lambda x: x['start'])
            report.append("| 序号 | 起点(m) | 终点(m) | 段长(m) | 加强原因 | 加强等级 | 加强系数 | 备注 |")
            report.append("|------|---------|---------|---------|---------|---------|---------|------|")
            for i, seg in enumerate(sorted_specials, 1):
                report.append(
                    f"| {i} | {seg['start']:.0f} | {seg['end']:.0f} | "
                    f"{seg['length']:.0f} | {seg['reason']} | {seg['level']} | "
                    f"+{seg['factor']*100:.0f}% | {seg.get('note', '') or '—'} |"
                )
            report.append("")

        report.append("## 六、施工要点\n")
        report.append("1. 光面爆破，控制超挖 ≤150mm")
        report.append("2. 掘出后立即初喷 30~50mm 封闭围岩")
        report.append("3. 锚杆安装：钻眼→清孔→注树脂药卷→搅拌→固化→安装托板→预紧")
        report.append("4. 锚索张拉：注浆后等待 7 天，张拉至设计预紧力")
        report.append("5. 喷射混凝土：分层喷射，每层 ≤100mm")
        report.append("6. 特殊段按设计要求加强，加密监测（每 20~30m 一测站）")
        report.append("7. 常规段监测：布设顶板离层仪、收敛计，每 50m 一个测站\n")

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

        # ========== CAD 图纸在线预览 + 下载 ==========
        st.markdown("---")
        st.markdown("### 📐 CAD 图纸导出与预览")

        col_a, col_b = st.columns([3, 1])
        with col_b:
            preview_dpi = st.slider("预览清晰度 (DPI)", 80, 300, 150, 10)
            preview_size = st.slider("预览图尺寸", 8, 20, 12, 1)

        try:
            dxf_buffer = generate_dxf(
                snap=snap,
                support=support,
                bolt_df=st.session_state['bolt_df'],
                shot=st.session_state['shot'],
                cable=st.session_state.get('cable'),
                steel=st.session_state.get('steel'),
                p=p,
            )
            dxf_bytes = dxf_buffer.getvalue()

            st.markdown("#### 🔍 DXF 图纸在线预览")
            try:
                with st.spinner("正在渲染图纸预览..."):
                    ratio = max(snap['B'], snap['H']) / min(snap['B'], snap['H'])
                    fig_h = preview_size / max(ratio, 1.0)
                    fig_w = preview_size
                    if ratio > 1.5:
                        fig_h = preview_size / ratio

                    png_bytes = dxf_to_png_bytes(
                        io.BytesIO(dxf_bytes),
                        dpi=preview_dpi,
                        figsize=(fig_w, fig_h)
                    )
                st.image(png_bytes, caption=f"DXF 预览（{snap['shape']}，"
                                            f"{preview_dpi} DPI）",
                         use_container_width=True)

                st.download_button(
                    "🖼️ 下载预览图 (PNG)",
                    data=png_bytes,
                    file_name=f"巷道支护预览_{snap['shape']}_{snap['name']}_"
                              f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                    mime="image/png",
                    use_container_width=True,
                )
            except Exception as e_preview:
                st.warning(f"⚠️ DXF 预览渲染失败，已降级为 Plotly 示意图。"
                           f"（原因：{e_preview}）")

            st.markdown("#### 📥 DXF 图纸下载")
            st.caption(
                "生成的 DXF 文件可用 AutoCAD / 浩辰CAD / 中望CAD 打开并编辑。"
                "超长锚索已按比例截断并加折断线标识。"
            )
            st.download_button(
                "📥 下载 CAD 图纸 (DXF)",
                data=dxf_bytes,
                file_name=f"巷道支护断面图_{snap['shape']}_{snap['name']}_"
                          f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.dxf",
                mime="application/dxf",
                use_container_width=True,
                type="primary",
            )
            st.success(f"✅ DXF 图纸已生成（{snap['shape']}）")
        except Exception as e:
            st.error(f"❌ 图纸生成失败：{e}")
            st.exception(e)

        # ========== 上传 DXF 文件并在线预览 ==========
        st.markdown("---")
        st.markdown("### 📤 上传 DXF 文件在线预览")
        st.caption("支持上传本系统生成的 DXF 图纸，或其他标准 DXF 文件（R12 ~ R2018）进行在线预览。")

        uploaded_dxf = st.file_uploader(
            "选择 DXF 文件",
            type=["dxf"],
            accept_multiple_files=False,
            key="uploaded_dxf_file",
        )

        if uploaded_dxf is not None:
            try:
                dxf_bytes_up = uploaded_dxf.read()
                file_size_kb = len(dxf_bytes_up) / 1024.0

                st.success(f"✅ 已上传：**{uploaded_dxf.name}** （{file_size_kb:.1f} KB）")

                col_up_a, col_up_b = st.columns([3, 1])
                with col_up_b:
                    up_dpi = st.slider("上传预览清晰度 (DPI)", 80, 300, 150, 10,
                                       key="up_dxf_dpi")
                    up_size = st.slider("上传预览图尺寸", 8, 24, 14, 1,
                                        key="up_dxf_size")

                try:
                    with st.spinner("正在解析并渲染上传的 DXF 文件..."):
                        try:
                            _txt = dxf_bytes_up
                            if isinstance(_txt, bytes):
                                _txt = _txt.decode("utf-8", errors="ignore")
                            _doc = ezdxf.read(io.StringIO(_txt))
                            _msp = _doc.modelspace()
                            n_entities = len(list(_msp))
                            dxf_version = _doc.dxfversion
                        except Exception:
                            n_entities = None
                            dxf_version = None

                        if n_entities is not None:
                            info_cols = st.columns(3)
                            info_cols[0].metric("DXF 版本", str(dxf_version))
                            info_cols[1].metric("模型空间图元数", n_entities)
                            info_cols[2].metric("文件大小 (KB)",
                                                f"{file_size_kb:.1f}")

                        png_bytes_up = dxf_to_png_bytes(
                            io.BytesIO(dxf_bytes_up),
                            dpi=up_dpi,
                            figsize=(up_size, up_size * 0.72),
                        )

                    st.image(
                        png_bytes_up,
                        caption=f"上传文件预览：{uploaded_dxf.name}（{up_dpi} DPI）",
                        use_container_width=True,
                    )

                    st.download_button(
                        "🖼️ 下载上传文件的预览图 (PNG)",
                        data=png_bytes_up,
                        file_name=f"{Path(uploaded_dxf.name).stem}_preview_"
                                  f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                        mime="image/png",
                        use_container_width=True,
                    )

                except Exception as e_up_preview:
                    st.error(f"❌ 上传的 DXF 文件渲染失败：{e_up_preview}")
                    st.info(
                        "💡 可能原因：\n"
                        "- 文件不是有效的 DXF（可能是 DWG，需先用 CAD 另存为 DXF）\n"
                        "- 使用了不兼容的高版本特性\n"
                        "- 文件内容位于布局空间（PaperSpace）而非模型空间\n"
                        "- 字体/样式缺失导致解析异常"
                    )
                    with st.expander("查看异常详情"):
                        st.exception(e_up_preview)

            except Exception as e_upload:
                st.error(f"❌ 文件读取失败：{e_upload}")
    else:
        st.info("👈 请先生成支护方案")


# ---------- Tab5 特殊段加强支护 ----------
with tab5:
    st.markdown("### ⚠️ 特殊段加强支护设计")
    st.caption(
        "对于断层破碎带、涌水段、采动影响区、交叉点等特殊区段，"
        "需要在常规支护基础上进行加强。可在此划分多个分段，"
        "系统将自动给出加强支护参数和纵剖面示意图。"
    )

    if 'special_segments' not in st.session_state:
        st.session_state['special_segments'] = []

    # ---- 顶部输入区 ----
    col_l1, col_l2, col_l3 = st.columns([2, 1, 1])
    with col_l1:
        total_length_input = st.number_input(
            "巷道全长 L (m)", 50.0, 10000.0,
            float(st.session_state.get('snapshot', {}).get(
                'total_length', total_length)),
            50.0, key="tab5_total_length"
        )
    with col_l2:
        st.metric("已划分特殊段",
                  f"{len(st.session_state['special_segments'])} 段")
    with col_l3:
        st.metric("巷道全长", f"{total_length_input:.0f} m")

    st.markdown("---")
    st.markdown("#### ➕ 添加特殊段")

    with st.form("add_special_segment", clear_on_submit=False):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            start_m = st.number_input("起点里程 (m)", 0.0,
                                      float(total_length_input),
                                      500.0, 10.0, key="seg_start")
        with c2:
            end_m = st.number_input("终点里程 (m)", 0.0,
                                    float(total_length_input),
                                    650.0, 10.0, key="seg_end")
        with c3:
            seg_reason = st.selectbox(
                "加强原因",
                ["断层破碎带", "涌水段", "采动影响区",
                 "交叉点/硐室", "淋水段", "岩性突变带",
                 "高地应力岩爆段", "软岩大变形段", "其他"],
                key="seg_reason"
            )
        with c4:
            seg_level = st.selectbox(
                "加强等级",
                ["一级加强（+30%）", "二级加强（+50%）",
                 "三级加强（+80%）", "特级加强（+120%）"],
                index=1, key="seg_level"
            )

        seg_note = st.text_input(
            "补充说明（可选）", value="",
            placeholder="例如：F5断层，落差8m，围岩V级",
            key="seg_note"
        )

        submitted = st.form_submit_button(
            "➕ 添加到特殊段清单", type="primary",
            use_container_width=True
        )

    if submitted:
        if end_m <= start_m:
            st.error("❌ 终点里程必须大于起点里程")
        elif end_m > total_length_input:
            st.error(f"❌ 终点里程不能超过巷道全长 {total_length_input} m")
        else:
            overlap = False
            for seg in st.session_state['special_segments']:
                if not (end_m <= seg['start'] or start_m >= seg['end']):
                    overlap = True
                    st.error(
                        f"❌ 与已有特殊段 "
                        f"[{seg['start']:.0f}~{seg['end']:.0f}m] 重叠，"
                        f"请调整里程"
                    )
                    break

            if not overlap:
                level_map = {
                    "一级加强（+30%）": 0.30,
                    "二级加强（+50%）": 0.50,
                    "三级加强（+80%）": 0.80,
                    "特级加强（+120%）": 1.20,
                }
                st.session_state['special_segments'].append({
                    "start": float(start_m),
                    "end": float(end_m),
                    "length": float(end_m - start_m),
                    "reason": seg_reason,
                    "level": seg_level,
                    "factor": level_map[seg_level],
                    "note": seg_note,
                })
                st.success(f"✅ 已添加特殊段 "
                           f"{start_m:.0f}~{end_m:.0f}m（{seg_reason}）")
                st.rerun()

    segments = st.session_state['special_segments']

    if segments:
        st.markdown("---")
        st.markdown("#### 📋 特殊段清单")

        sorted_segs = sorted(segments, key=lambda x: x['start'])

        # 计算常规段（补集）
        normal_segs = []
        cursor = 0.0
        for seg in sorted_segs:
            if seg['start'] > cursor:
                normal_segs.append({
                    "start": cursor, "end": seg['start'],
                    "length": seg['start'] - cursor,
                    "reason": "常规段", "level": "—", "factor": 0.0,
                    "note": ""
                })
            cursor = max(cursor, seg['end'])
        if cursor < total_length_input:
            normal_segs.append({
                "start": cursor, "end": total_length_input,
                "length": total_length_input - cursor,
                "reason": "常规段", "level": "—", "factor": 0.0,
                "note": ""
            })

        all_segs = sorted(sorted_segs + normal_segs,
                          key=lambda x: x['start'])

        table_rows = []
        for i, seg in enumerate(all_segs, 1):
            is_special = seg['reason'] != "常规段"
            table_rows.append({
                "序号": i,
                "起点(m)": f"{seg['start']:.0f}",
                "终点(m)": f"{seg['end']:.0f}",
                "长度(m)": f"{seg['length']:.0f}",
                "段类型": "⚠️ 特殊段" if is_special else "✅ 常规段",
                "加强原因": seg['reason'],
                "加强等级": seg['level'],
                "加强系数": f"+{seg['factor']*100:.0f}%" if is_special else "—",
                "备注": seg.get('note', ""),
            })

        df_summary = pd.DataFrame(table_rows)
        st.dataframe(df_summary, use_container_width=True, hide_index=True)

        # 统计
        total_special_len = sum(s['length'] for s in sorted_segs)
        total_normal_len = total_length_input - total_special_len
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("巷道全长", f"{total_length_input:.0f} m")
        c2.metric("特殊段总长", f"{total_special_len:.0f} m")
        c3.metric("常规段总长", f"{total_normal_len:.0f} m")
        c4.metric("特殊段占比",
                  f"{total_special_len/max(total_length_input,1)*100:.1f}%")

        # ================= 优化后的纵剖面可视化 =================
        st.markdown("#### 📈 巷道纵剖面支护分段图")
        st.caption("💡 提示：鼠标悬停可查看每段的详细参数，"
                   "红色虚线为特殊段起止边界")

        fig_seg = go.Figure()

        # 1) 背景围岩带（浅灰）
        fig_seg.add_trace(go.Bar(
            x=[total_length_input],
            y=["围岩"],
            base=[0],
            orientation='h',
            marker=dict(color="rgba(220,220,220,0.30)"),
            hoverinfo="skip",
            showlegend=False,
        ))

        # 2) 分段色带
        for seg in all_segs:
            is_special = seg['reason'] != "常规段"
            if is_special:
                color = REASON_COLORS.get(seg['reason'], "#dc3545")
                icon = REASON_ICONS.get(seg['reason'], "⚠️")
                label = f"{icon} {seg['reason']}"
                line_color = "white"
                line_width = 2
            else:
                color = "#dfe6e9"
                icon = "✅"
                label = "常规段"
                line_color = "#b2bec3"
                line_width = 1

            hover_text = (
                f"<b>{label}</b><br>"
                f"📏 里程：{seg['start']:.0f} ~ {seg['end']:.0f} m<br>"
                f"📐 段长：{seg['length']:.0f} m<br>"
            )
            if is_special:
                hover_text += (
                    f"🎯 加强等级：{seg['level']}<br>"
                    f"📊 加强系数：+{seg['factor']*100:.0f}%<br>"
                )
            if seg.get('note'):
                hover_text += f"📝 备注：{seg['note']}"

            mid_x = (seg['start'] + seg['end']) / 2
            seg_len = seg['length']
            if seg_len < 80:
                text_str = f"<b>{seg['start']:.0f}~{seg['end']:.0f}</b>"
                text_size = 10
            else:
                text_str = (f"<b>{label}</b><br>"
                            f"{seg['start']:.0f}~{seg['end']:.0f}m")
                text_size = 12

            fig_seg.add_trace(go.Bar(
                x=[seg_len],
                y=["支护分段"],
                base=[seg['start']],
                orientation='h',
                marker=dict(color=color,
                            line=dict(color=line_color, width=line_width)),
                name=label,
                text=text_str,
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(color="white" if is_special else "#2d3436",
                              size=text_size,
                              family="Microsoft YaHei"),
                hovertemplate=hover_text + "<extra></extra>",
                showlegend=False,
            ))

        # 3) 特殊段上方标注
        for seg in sorted_segs:
            mid_x = (seg['start'] + seg['end']) / 2
            icon = REASON_ICONS.get(seg['reason'], "⚠️")
            seg_color = REASON_COLORS.get(seg['reason'], "#dc3545")
            fig_seg.add_annotation(
                x=mid_x, y=1.55,
                text=f"{icon} <b>{seg['reason']}</b><br>"
                     f"<span style='font-size:10px;'>"
                     f"{seg['level']}｜+{seg['factor']*100:.0f}%</span>",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=1.5,
                arrowcolor=seg_color,
                ax=0, ay=-25,
                bgcolor="white",
                bordercolor=seg_color,
                borderwidth=2,
                borderpad=6,
                font=dict(size=11, color="#2d3436"),
                align="center",
            )

        # 4) 里程参考线
        tick_step = 500 if total_length_input > 2000 else 200
        for tick in range(0, int(total_length_input) + 1, tick_step):
            fig_seg.add_vline(
                x=tick,
                line=dict(color="rgba(150,150,150,0.35)",
                          width=1, dash="dot"),
            )

        # 5) 特殊段起止醒目竖线
        for seg in sorted_segs:
            seg_color = REASON_COLORS.get(seg['reason'], "#dc3545")
            for x_pos in [seg['start'], seg['end']]:
                fig_seg.add_vline(
                    x=x_pos,
                    line=dict(color=seg_color, width=2, dash="dash"),
                )

        # 6) 开挖方向箭头
        fig_seg.add_annotation(
            x=total_length_input * 0.98, y=1.85,
            text="开挖方向 ➡",
            showarrow=False,
            font=dict(size=13, color="#e67e22",
                      family="Microsoft YaHei"),
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#e67e22",
            borderwidth=1,
            borderpad=4,
        )

        fig_seg.update_layout(
            title=dict(
                text=f"<b>巷道全长支护分段纵剖面图</b><br>"
                     f"<span style='font-size:13px; color:#666;'>"
                     f"L = {total_length_input:.0f} m ｜ "
                     f"特殊段 {len(sorted_segs)} 处 ｜ "
                     f"特殊段总长 "
                     f"{sum(s['length'] for s in sorted_segs):.0f} m "
                     f"({sum(s['length'] for s in sorted_segs)/max(total_length_input,1)*100:.1f}%)"
                     f"</span>",
                font=dict(size=16, color="#2c3e50"),
                x=0.5, xanchor="center",
            ),
            xaxis=dict(
                title=dict(text="<b>里程 (m)</b>",
                           font=dict(size=13, color="#2c3e50")),
                range=[0, total_length_input],
                tick0=0, dtick=tick_step,
                tickfont=dict(size=11, color="#555"),
                showgrid=True,
                gridcolor="rgba(200,200,200,0.25)",
                gridwidth=1,
                zeroline=False,
                showline=True,
                linecolor="#b2bec3",
                linewidth=1.5,
                mirror=True,
            ),
            yaxis=dict(
                range=[0, 2.2],
                showticklabels=False,
                showgrid=False,
                zeroline=False,
                showline=True,
                linecolor="#b2bec3",
                linewidth=1.5,
                mirror=True,
            ),
            height=420,
            margin=dict(l=40, r=40, t=110, b=60),
            bargap=0.0,
            plot_bgcolor="rgba(250,250,252,1)",
            paper_bgcolor="white",
            hoverlabel=dict(
                bgcolor="white",
                font_size=12,
                font_family="Microsoft YaHei",
                bordercolor="#e67e22",
            ),
        )
        st.plotly_chart(fig_seg, use_container_width=True)

        # 图例卡片
        if sorted_segs:
            st.markdown("##### 🎨 图例")
            legend_cols = st.columns(min(len(sorted_segs), 6))
            for i, seg in enumerate(sorted_segs):
                color = REASON_COLORS.get(seg['reason'], "#dc3545")
                icon = REASON_ICONS.get(seg['reason'], "⚠️")
                with legend_cols[i % len(legend_cols)]:
                    st.markdown(
                        f"""<div style='background:{color}; color:white;
                        padding:8px 12px; border-radius:8px; font-size:12px;
                        text-align:center; margin-bottom:6px;
                        box-shadow:0 2px 4px rgba(0,0,0,0.1);'>
                        {icon} <b>{seg['reason']}</b><br>
                        <span style='font-size:10px; opacity:0.95;'>
                        {seg['start']:.0f}~{seg['end']:.0f}m ｜
                        {seg['level']}</span>
                        </div>""",
                        unsafe_allow_html=True,
                    )

        # ================= 每个特殊段的详细参数 + 断面示意图 =================
        if sorted_segs:
            st.markdown("---")
            st.markdown("#### 🔧 特殊段加强支护参数")

            base_snap = st.session_state.get('snapshot', {
                'B': B, 'H': H, 'rock': rock_class,
                'gamma': gamma_rock, 'phi': phi, 'c_r': c_r,
                'shape': section_shape,
            })
            base_p = st.session_state.get('pressure', {
                '修正后设计竖直压力 qd(kPa)': 100.0,
            })
            base_qd = base_p.get('修正后设计竖直压力 qd(kPa)', 100.0)

            for idx, seg in enumerate(sorted_segs, 1):
                seg_color = REASON_COLORS.get(seg['reason'], "#dc3545")
                icon = REASON_ICONS.get(seg['reason'], "⚠️")
                with st.expander(
                    f"{icon} 特殊段 {idx}：里程 "
                    f"{seg['start']:.0f}~{seg['end']:.0f} m"
                    f"（{seg['reason']}，{seg['level']}）",
                    expanded=(idx == 1)
                ):
                    params = calc_segment_reinforced_params(
                        base_snap, base_qd, seg)
                    f_boost = seg['factor']

                    # 顶部信息卡
                    st.markdown(
                        f"""<div style='background:linear-gradient(
                        135deg, {seg_color}dd 0%, {seg_color}99 100%);
                        color:white; padding:12px 20px; border-radius:8px;
                        margin-bottom:16px;'>
                        <b style='font-size:16px;'>{icon} {seg['reason']}</b>
                        ｜ {seg['level']} ｜ 加强系数 +{f_boost*100:.0f}%
                        ｜ 段长 {seg['length']:.0f} m<br>
                        <span style='font-size:12px; opacity:0.95;'>
                        📏 {seg['start']:.0f} ~ {seg['end']:.0f} m ｜
                        💬 {seg.get('note', '') or '无补充说明'}</span>
                        </div>""",
                        unsafe_allow_html=True,
                    )

                    # ---- 断面加强对比示意图 ----
                    st.markdown("##### 📐 断面加强对比示意图")
                    st.caption(
                        "左侧为常规段断面，右侧为加强段断面。"
                        "🟥 锚杆 ｜ 🟪 锚索 ｜ 🟦 钢架 ｜ 🟧 喷层"
                    )

                    fig_cmp = go.Figure()
                    Bv = base_snap['B']
                    Hv = base_snap['H']
                    shape_v = base_snap.get('shape', section_shape)

                    # 计算两种断面间距
                    x_gap = Bv + 2.5
                    x_left = -x_gap / 2
                    x_right = x_gap / 2

                    # 常规段参数
                    sp_n = params['bolt_spacing_normal']
                    shot_n = params['shot_normal']
                    cable_n = None
                    cable_sp_n = None
                    steel_n = False
                    steel_sp_n = None
                    if st.session_state.get('cable'):
                        try:
                            cable_sp_n = float(
                                st.session_state['cable'][
                                    '锚索间排距(m)'].split("×")[0])
                            cable_n = True
                        except Exception:
                            pass
                    if st.session_state.get('steel'):
                        steel_n = True
                        try:
                            steel_sp_n = float(
                                st.session_state['steel']['支架间距(m)'])
                        except Exception:
                            steel_sp_n = 1.0

                    # 加强段参数
                    sp_b = params['bolt_spacing_boost']
                    shot_b = params['shot_boost']
                    cable_sp_b = params['cable_sp_boost']
                    steel_sp_b = params['steel_sp_boost']

                    # 绘制左侧（常规）
                    draw_section_on_figure(
                        fig_cmp, x_left, shape_v, Bv, Hv,
                        spacing=sp_n,
                        shot_t_mm=shot_n,
                        draw_cable=cable_n,
                        cable_sp=cable_sp_n,
                        draw_steel=steel_n,
                        steel_sp=steel_sp_n,
                        title=f"✅ 常规段",
                        is_boost=False,
                    )
                    # 绘制右侧（加强）
                    draw_section_on_figure(
                        fig_cmp, x_right, shape_v, Bv, Hv,
                        spacing=sp_b,
                        shot_t_mm=shot_b,
                        draw_cable=True,
                        cable_sp=cable_sp_b or 1.2,
                        draw_steel=True,
                        steel_sp=steel_sp_b,
                        title=f"{icon} 加强段",
                        is_boost=True,
                    )

                    # 中间箭头
                    fig_cmp.add_annotation(
                        x=0, y=Hv / 2,
                        text="➡",
                        showarrow=False,
                        font=dict(size=36, color="#e67e22"),
                    )
                    fig_cmp.add_annotation(
                        x=0, y=Hv / 2 - 0.8,
                        text=f"加强<br>+{f_boost*100:.0f}%",
                        showarrow=False,
                        font=dict(size=11, color="#e67e22"),
                        bgcolor="rgba(255,255,255,0.9)",
                        bordercolor="#e67e22",
                        borderwidth=1,
                        borderpad=3,
                    )

                    x_total = Bv + 2.5 + 1.5
                    y_max = Hv + 4.0
                    fig_cmp.update_layout(
                        xaxis=dict(
                            range=[-x_total, x_total],
                            showticklabels=False,
                            showgrid=False,
                            zeroline=False,
                            scaleanchor="y",
                            scaleratio=1,
                        ),
                        yaxis=dict(
                            range=[-1.5, y_max],
                            showticklabels=False,
                            showgrid=False,
                            zeroline=False,
                        ),
                        height=520,
                        margin=dict(l=20, r=20, t=30, b=20),
                        plot_bgcolor="rgba(250,250,252,1)",
                        paper_bgcolor="white",
                        showlegend=False,
                    )
                    st.plotly_chart(fig_cmp, use_container_width=True,
                                    key=f"fig_cmp_{idx}")

                    # ---- 参数详情 + 加强措施建议 ----
                    col_a, col_b = st.columns([2, 1])

                    with col_a:
                        st.markdown("##### 📊 参数加强对比")
                        compare_rows = [
                            {"参数": "锚杆间排距",
                             "常规": f"{params['bolt_spacing_normal']}×"
                                     f"{params['bolt_spacing_normal']} m",
                             "加强": f"{params['bolt_spacing_boost']}×"
                                     f"{params['bolt_spacing_boost']} m"},
                            {"参数": "喷层厚度",
                             "常规": f"{params['shot_normal']} mm",
                             "加强": f"{params['shot_boost']} mm"},
                            {"参数": "锚杆预紧力",
                             "常规": f"{params['pre_normal']:.0f} kN",
                             "加强": f"{params['pre_boost']:.0f} kN"},
                            {"参数": "钢架间距",
                             "常规": f"{params['steel_sp_normal']} m",
                             "加强": f"{params['steel_sp_boost']} m"},
                            {"参数": "设计压力 qd",
                             "常规": f"{base_qd:.1f} kPa",
                             "加强": f"{params['qd_boost']:.1f} kPa"},
                            {"参数": "预留变形量",
                             "常规": f"{params['deform_normal']} mm",
                             "加强": f"{params['deform_boost']} mm"},
                        ]
                        if params['cable_sp_boost'] is not None:
                            compare_rows.insert(2, {
                                "参数": "锚索间排距",
                                "常规": "1.6×3.2 m",
                                "加强": f"{params['cable_sp_boost']}×"
                                        f"{params['cable_rsp_boost']} m",
                            })
                        st.dataframe(
                            pd.DataFrame(compare_rows),
                            use_container_width=True,
                            hide_index=True,
                        )

                    with col_b:
                        st.markdown("##### 🛠️ 加强措施建议")
                        measures = []
                        if seg['reason'] == "断层破碎带":
                            measures = [
                                "锚杆间距缩小至 0.6~0.7m",
                                "锚索加密至间排距 1.2×2.4m",
                                "喷层厚度增加 30~50mm",
                                "增设 U 型钢可缩支架 @0.5~0.6m",
                                "超前小导管/管棚预支护",
                                "必要时进行超前注浆加固",
                            ]
                        elif seg['reason'] == "涌水段":
                            measures = [
                                "超前探放水，先探后掘",
                                "注浆堵水 + 排水沟",
                                "喷层加厚，采用防水混凝土",
                                "锚杆改用防腐型",
                                "锚索注浆改用水泥-水玻璃双液浆",
                            ]
                        elif seg['reason'] == "采动影响区":
                            measures = [
                                "锚杆预紧力提高至设计值 1.2 倍",
                                "采用可缩性 U 型钢支架",
                                "增设让压锚杆/让压锚索",
                                "加密监测测点（每 20~30m）",
                                "预留变形量 300~500mm",
                            ]
                        elif seg['reason'] == "交叉点/硐室":
                            measures = [
                                "交叉点处锚索加密，形成承载圈",
                                "增设抬棚或组合梁",
                                "加大喷层厚度至 200mm 以上",
                                "钢筋网改用 φ8@100×100",
                                "增加锁口锚索（4~6根/处）",
                            ]
                        elif seg['reason'] == "淋水段":
                            measures = [
                                "喷层中掺入防水剂",
                                "锚杆孔口加设止水环",
                                "增设导水管引排",
                                "必要时采用化学浆液封堵",
                            ]
                        elif seg['reason'] == "岩性突变带":
                            measures = [
                                "过渡段锚杆加密，长短锚杆交替",
                                "设置变形缝，适应不均匀变形",
                                "加强收敛监测",
                            ]
                        elif seg['reason'] == "高地应力岩爆段":
                            measures = [
                                "采用让压锚杆 + 高预应力锚索",
                                "喷钢纤维混凝土（厚度≥150mm）",
                                "增设柔性防护网",
                                "避免大面积暴露，短掘短支",
                                "必要时实施应力释放孔",
                            ]
                        elif seg['reason'] == "软岩大变形段":
                            measures = [
                                "采用可缩性 U 型钢支架 + 让压构件",
                                "锚杆加长至 2.8~3.2m",
                                "预留变形量 500~800mm",
                                "多次支护，先柔后刚",
                                "加强底板治理（底鼓控制）",
                            ]
                        else:
                            measures = [
                                "锚杆间距缩小 20%",
                                "喷层加厚 30mm",
                                "加强监测",
                            ]
                        for m in measures:
                            st.markdown(f"- {m}")

                    # 段详情表
                    st.markdown("##### 📋 段详情")
                    detail_rows = [
                        {"项目": "起点里程",
                         "数值": f"{seg['start']:.0f} m"},
                        {"项目": "终点里程",
                         "数值": f"{seg['end']:.0f} m"},
                        {"项目": "段长",
                         "数值": f"{seg['length']:.0f} m"},
                        {"项目": "加强原因", "数值": seg['reason']},
                        {"项目": "加强等级", "数值": seg['level']},
                        {"项目": "加强系数",
                         "数值": f"+{f_boost*100:.0f}%"},
                        {"项目": "常规设计压力 qd",
                         "数值": f"{base_qd:.1f} kPa"},
                        {"项目": "加强设计压力 qd′",
                         "数值": f"{params['qd_boost']:.1f} kPa"},
                        {"项目": "补充说明",
                         "数值": (seg.get('note', '') or '—')},
                    ]
                    st.dataframe(
                        pd.DataFrame(detail_rows),
                        use_container_width=True,
                        hide_index=True,
                    )

        # ---- 清除 / 导出按钮 ----
        st.markdown("---")
        btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 2])

        with btn_col1:
            if st.button("🗑️ 清空所有特殊段", use_container_width=True):
                st.session_state['special_segments'] = []
                st.rerun()

        with btn_col2:
            csv_data = df_summary.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "📥 下载分段清单 (CSV)",
                data=csv_data,
                file_name=f"特殊段清单_"
                          f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with btn_col3:
            st.info(
                "💡 **提示**：特殊段参数基于常规段自动放大，"
                "实际工程中应根据地质预报、监测数据动态调整。"
            )

    else:
        st.info("👈 请在上方添加特殊段，例如断层破碎带、涌水段等。")
        st.markdown(
            """
            **常见需要加强支护的区段：**
            - 🔴 **断层破碎带**：围岩破碎，自稳能力差，需超前支护 + 强支护
            - 💧 **涌水段**：水压软化围岩，锚固力下降，需注浆堵水
            - ⚡ **采动影响区**：动压显现，需可缩性支架 + 让压构件
            - 🏗️ **交叉点/硐室**：跨度大，应力集中，需锁口加强
            - 💦 **淋水段**：长期淋水腐蚀锚杆，需防腐 + 防水
            - 🪨 **岩性突变带**：软硬交界处易应力集中，需过渡支护
            - 💥 **高地应力岩爆段**：需让压支护 + 柔性防护
            - 🌀 **软岩大变形段**：需多次支护、预留变形量
            """
        )


st.markdown("---")
st.markdown(
    "<p style='text-align:center; color:#888;'>⛏️ 井下巷道智能支护方案设计系统 | "
    "依据 GB/T 35056-2018、GB 50419-2017 | 结果仅供参考</p>",
    unsafe_allow_html=True
)