# app.py
# 超长工作面地压监测系统
# 功能：顶板活动监测、支架受力分析、围岩应力分析、超前支护参数优化

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# ============================================================
# 页面配置（必须放在最前）
# ============================================================
st.set_page_config(
    page_title="超长工作面地压监测系统",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 全局CSS样式
# ============================================================
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1F4E79;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid #1F4E79;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #e4ecf7 100%);
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    .stMetric label { font-size: 0.9rem !important; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 数据层：模拟矿压数据
# ============================================================
@st.cache_data
def generate_mock_data():
    """生成400m超长工作面倾向矿压数据"""
    np.random.seed(42)

    # 工作面倾向位置：0-400m，每5m一个支架
    positions = np.arange(0, 405, 5)
    n = len(positions)

    # 支架工作阻力：双峰状分布（两端高、中间相对低）
    base_resistance = (
            28
            + 6 * np.exp(-((positions - 80) / 60) ** 2)  # 左侧峰值
            + 5 * np.exp(-((positions - 320) / 70) ** 2)  # 右侧峰值
            + np.random.normal(0, 1.5, n)
    )
    base_resistance = np.clip(base_resistance, 0, 40)

    # 超前段应力：距工作面距离 0-60m
    advance_dist = np.arange(0, 65, 1)
    advance_stress = (
            12
            + 18 * np.exp(-((advance_dist - 10) / 12) ** 2)
            + np.random.normal(0, 1, len(advance_dist))
    )
    advance_stress = np.clip(advance_stress, 0, None)

    # 微震事件（顶板活动）
    n_events = 80
    microseismic = pd.DataFrame({
        'x': np.random.uniform(0, 400, n_events),
        'y': np.random.uniform(-20, 80, n_events),
        'energy': np.random.exponential(500, n_events),
        'time': [datetime.now() - timedelta(hours=int(np.random.randint(0, 72)))
                 for _ in range(n_events)]
    })

    # 支架阻力时序
    time_range = pd.date_range(end=datetime.now(), periods=200, freq='10min')
    resistance_series = (
            22
            + 8 * np.sin(np.linspace(0, 8 * np.pi, 200))
            + np.random.normal(0, 1.2, 200)
    )
    resistance_series = np.clip(resistance_series, 0, None)

    return positions, base_resistance, advance_dist, advance_stress, microseismic, time_range, resistance_series


# ============================================================
# 页面一：总览仪表盘
# ============================================================
def page_dashboard():
    st.markdown('<div class="main-header">📊 矿压监测总览</div>', unsafe_allow_html=True)

    positions, resistance, adv_dist, adv_stress, micro, _, _ = generate_mock_data()

    # 关键指标卡片
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "最大支架阻力",
            f"{resistance.max():.1f} MPa",
            delta=f"额定 32 MPa"
        )
    with col2:
        peak_stress = adv_stress.max()
        peak_pos = adv_dist[np.argmax(adv_stress)]
        st.metric(
            "超前应力峰值",
            f"{peak_stress:.1f} MPa",
            delta=f"距煤壁 {peak_pos:.0f} m"
        )
    with col3:
        st.metric(
            "微震事件数",
            f"{len(micro)}",
            delta=f"最大能量 {micro['energy'].max():.0f} J"
        )
    with col4:
        risk_pct = (resistance > 30).sum() / len(resistance) * 100
        st.metric(
            "高阻力支架占比",
            f"{risk_pct:.1f}%",
            delta="预警阈值 30 MPa" if risk_pct > 0 else None
        )

    st.divider()

    # 支架阻力倾向分布
    st.subheader("支架工作阻力沿工作面倾向分布")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=positions, y=resistance,
        mode='lines+markers',
        name='支架阻力',
        marker=dict(size=5, color='#2E86AB'),
        line=dict(color='#2E86AB', width=2)
    ))
    fig.add_hline(
        y=32, line_dash="dash", line_color="red",
        annotation_text="额定工作阻力 32 MPa",
        annotation_position="top right"
    )
    fig.update_layout(
        xaxis_title="工作面倾向位置 (m)",
        yaxis_title="工作阻力 (MPa)",
        height=380,
        hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=True)

    # 微震事件平面分布
    st.subheader("顶板微震事件分布")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=micro['x'], y=micro['y'],
        mode='markers',
        marker=dict(
            size=np.log1p(micro['energy']) * 3,
            color=micro['energy'],
            colorscale='YlOrRd',
            showscale=True,
            colorbar=dict(title="能量(J)"),
            line=dict(width=0.5, color='white')
        ),
        text=micro['energy'].apply(lambda e: f"能量: {e:.0f} J"),
        hovertemplate="位置: %{x:.0f} m<br>距工作面: %{y:.0f} m<br>%{text}<extra></extra>",
        name='微震事件'
    ))
    fig2.add_hline(y=0, line_dash="solid", line_color="gray",
                   annotation_text="工作面煤壁")
    fig2.update_layout(
        xaxis_title="工作面倾向位置 (m)",
        yaxis_title="距工作面距离 (m)",
        height=380
    )
    st.plotly_chart(fig2, use_container_width=True)


# ============================================================
# 页面二：支架受力分析
# ============================================================
def page_support_analysis():
    st.markdown('<div class="main-header">🔧 支架受力特征分析</div>', unsafe_allow_html=True)

    positions, resistance, _, _, _, time_range, res_series = generate_mock_data()

    # 分区统计
    st.subheader("工作面倾向分区支架阻力对比")
    zone_labels = ['上部 (0-130m)', '中部 (130-270m)', '下部 (270-400m)']
    zone_means = [
        resistance[positions < 130].mean(),
        resistance[(positions >= 130) & (positions < 270)].mean(),
        resistance[positions >= 270].mean()
    ]
    zone_max = [
        resistance[positions < 130].max(),
        resistance[(positions >= 130) & (positions < 270)].max(),
        resistance[positions >= 270].max()
    ]

    fig = go.Figure(data=[
        go.Bar(name='平均阻力', x=zone_labels, y=zone_means, marker_color='#4A90D9'),
        go.Bar(name='峰值阻力', x=zone_labels, y=zone_max, marker_color='#E74C3C')
    ])
    fig.update_layout(
        barmode='group',
        yaxis_title="工作阻力 (MPa)",
        height=350,
        legend=dict(orientation='h', y=1.1)
    )
    st.plotly_chart(fig, use_container_width=True)

    # 时序曲线
    st.subheader("典型支架阻力时序曲线（近24h）")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=time_range, y=res_series,
        mode='lines', name='工作阻力',
        line=dict(color='#2E86AB', width=1.8)
    ))
    fig2.add_hline(
        y=30, line_dash="dash", line_color="orange",
        annotation_text="预警阈值 30 MPa"
    )
    fig2.add_hline(
        y=32, line_dash="dash", line_color="red",
        annotation_text="额定阻力 32 MPa"
    )
    fig2.update_layout(
        xaxis_title="时间",
        yaxis_title="工作阻力 (MPa)",
        height=330,
        hovermode='x unified'
    )
    st.plotly_chart(fig2, use_container_width=True)

    # 增阻特性
    st.subheader("支架增阻特性分析")
    col1, col2 = st.columns(2)
    with col1:
        st.info("""
        **增阻规律**  
        来压期间支架增阻呈 **"对数-指数"复合函数型**，  
        呈现 **先快、中缓、最后短时急速增阻** 的特点。
        """)
    with col2:
        st.warning("""
        **关键指标**  
        - 初撑力：应达额定阻力的 **60%** 左右  
        - 增阻速率：快速阶段 > **2 MPa/h**  
        - 安全阀开启率：评估支架适应性的核心指标
        """)

    # 增阻阶段模拟曲线
    t = np.linspace(0, 10, 100)
    quick = 12 * (1 - np.exp(-3 * t))  # 快速增阻
    slow = 4 * np.log1p(t)  # 缓慢增阻
    final = 6 * np.exp(0.8 * (t - 9))  # 急速增阻
    total = quick + slow * 0.5 + np.where(t > 8, final * 0.1, 0)
    total = np.clip(total, 0, 34)

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=t, y=total, mode='lines',
                              line=dict(color='#E74C3C', width=2.5),
                              name='实际增阻曲线'))
    fig3.add_vrect(x0=0, x1=2, fillcolor="green", opacity=0.1,
                   annotation_text="快速增阻", annotation_position="top left")
    fig3.add_vrect(x0=2, x1=8, fillcolor="blue", opacity=0.1,
                   annotation_text="缓慢增阻", annotation_position="top left")
    fig3.add_vrect(x0=8, x1=10, fillcolor="red", opacity=0.1,
                   annotation_text="急速增阻", annotation_position="top left")
    fig3.update_layout(
        xaxis_title="来压持续时间 (h)",
        yaxis_title="工作阻力 (MPa)",
        height=330
    )
    st.plotly_chart(fig3, use_container_width=True)


# ============================================================
# 页面三：围岩应力与超前支护
# ============================================================
def page_advanced_support():
    st.markdown('<div class="main-header">🛡️ 围岩应力与超前支护分析</div>', unsafe_allow_html=True)

    _, _, adv_dist, adv_stress, _, _, _ = generate_mock_data()

    # 超前应力分布
    st.subheader("超前支承压力分布曲线")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=adv_dist, y=adv_stress,
        mode='lines', fill='tozeroy',
        name='超前应力',
        line=dict(color='#E74C3C', width=2.5),
        fillcolor='rgba(231, 76, 60, 0.2)'
    ))
    peak_idx = int(np.argmax(adv_stress))
    fig.add_annotation(
        x=adv_dist[peak_idx], y=adv_stress[peak_idx],
        text=f"峰值 {adv_stress[peak_idx]:.1f} MPa<br>距煤壁 {adv_dist[peak_idx]:.0f} m",
        showarrow=True, arrowhead=2, arrowcolor="#333",
        bgcolor="white", bordercolor="#333"
    )
    fig.add_vline(x=40, line_dash="dash", line_color="orange",
                  annotation_text="典型影响范围边界 ~40m")
    fig.update_layout(
        xaxis_title="距工作面煤壁距离 (m)",
        yaxis_title="垂直应力 (MPa)",
        xaxis=dict(autorange="reversed"),
        height=380
    )
    st.plotly_chart(fig, use_container_width=True)

    # 支护参数推荐
    st.subheader("超前支护合理参数推荐")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**支护长度确定依据**")
        st.info("""
        实测与理论分析表明：
        - 一般采动影响范围：**37 ~ 40 m**
        - 深部高应力巷道：**45 ~ 68 m**

        **建议**：支护长度不低于 **40 m**，  
        深部条件取 **60 m** 以上。
        """)
    with col2:
        st.markdown("**支护强度确定依据**")
        st.info("""
        基于 **"低初撑、高工阻"** 原则：
        - 从端头至超前远端 **梯度递减**
        - 初撑力设为额定阻力的 **60%** 左右
        - 实测超前支护强度建议 ≥ **267.38 kPa**
        """)

    # 支护强度计算器
    with st.expander("📐 支护强度计算器（基于传递岩梁理论）", expanded=True):
        st.latex(r"p = A + \frac{M_E \cdot \rho_E \cdot c}{K_T \cdot L_k}")
        st.markdown("""
        - $A$：直接顶载荷 (kPa)  
        - $M_E$：基本顶厚度 (m)  
        - $\\rho_E$：基本顶密度 (kN/m³)  
        - $c$：周期垮落步距 (m)  
        - $K_T$：岩重分配系数  
        - $L_k$：控顶距 (m)
        """)
        col_a, col_b = st.columns(2)
        with col_a:
            M_E = st.number_input("基本顶厚度 M_E (m)", value=8.0, step=0.5, min_value=0.0)
            rho_E = st.number_input("基本顶密度 ρ_E (kN/m³)", value=25.0, step=0.5, min_value=0.0)
            c = st.number_input("周期垮落步距 c (m)", value=20.0, step=1.0, min_value=0.0)
        with col_b:
            K_T = st.number_input("岩重分配系数 K_T", value=2.0, step=0.1, min_value=0.1)
            L_k = st.number_input("控顶距 L_k (m)", value=5.0, step=0.5, min_value=0.1)
            A = st.number_input("直接顶载荷 A (kPa)", value=150.0, step=10.0, min_value=0.0)

        p = A + (M_E * rho_E * c) / (K_T * L_k)
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.metric("计算支护强度 p", f"{p:.1f} kPa")
        with col_r2:
            if p < 267.38:
                st.error("⚠️ 低于建议值 267.38 kPa，需加强支护")
            else:
                st.success("✅ 满足支护强度要求")


# ============================================================
# 页面四：支护优化评估
# ============================================================
def page_optimization():
    st.markdown('<div class="main-header">🔍 支护方案优化评估</div>', unsafe_allow_html=True)

    st.markdown("""
    基于监测数据，从 **支护强度适应性**、**来压动载响应**、**围岩控制效果**、
    **设备协同性**、**安全裕度** 五个维度评价并优化现有支护方案。
    """)

    # 雷达图
    categories = ['支护强度适应性', '来压动载响应', '围岩变形控制',
                  '设备协同性', '安全裕度']
    current_scores = [72, 58, 65, 70, 60]
    optimized_scores = [85, 78, 82, 80, 82]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=current_scores + [current_scores[0]],
        theta=categories + [categories[0]],
        fill='toself', name='当前方案',
        line_color='#E74C3C', fillcolor='rgba(231,76,60,0.25)'
    ))
    fig.add_trace(go.Scatterpolar(
        r=optimized_scores + [optimized_scores[0]],
        theta=categories + [categories[0]],
        fill='toself', name='优化建议',
        line_color='#2E86AB', fillcolor='rgba(46,134,171,0.25)'
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        height=450,
        legend=dict(orientation='h', y=1.1)
    )
    st.plotly_chart(fig, use_container_width=True)

    # 优化建议列表
    st.subheader("优化建议")
    suggestions = [
        {
            "问题": "中部支架阻力偏低，两端偏高（谷形/双峰分布）",
            "依据": "千米深井超长工作面支架阻力呈'中间小、两端大'特征",
            "建议": "中部峰值影响区采用成组协同移架，其他区域独立移架"
        },
        {
            "问题": "来压期间支架快速增阻，安全阀频繁开启",
            "依据": "超长工作面来压增阻呈'对数-指数'复合型，大截深是主要诱因",
            "建议": "顶板不稳定时适当减小采煤机截深，提高支护质量"
        },
        {
            "问题": "超前支护长度可能不足，远端围岩控制效果差",
            "依据": "深部沿空巷道超前支护距离应为 45~68 m",
            "建议": "将超前支护从 40 m 延长至 60 m，采用'预先主动、一次承载'理念"
        },
        {
            "问题": "支架初撑力偏低，无法有效控制早期离层",
            "依据": "初撑力应为工作阻力的 60% 左右",
            "建议": "将初撑力设定值提升至额定工作阻力的 60%，加强供液系统压力保障"
        }
    ]

    for i, s in enumerate(suggestions, 1):
        with st.expander(f"⚠️ 问题 {i}：{s['问题']}"):
            st.markdown(f"**理论依据**：{s['依据']}")
            st.success(f"**优化建议**：{s['建议']}")


# ============================================================
# 页面五：数据接入配置
# ============================================================
def page_data_source():
    st.markdown('<div class="main-header">🔌 数据接入配置</div>', unsafe_allow_html=True)

    st.markdown("""
    本系统支持多种数据接入方式，实际部署时替换模拟数据源即可。
    """)

    data_option = st.radio(
        "选择数据源类型",
        ["模拟数据（演示）", "CSV文件上传", "MQTT实时流", "数据库连接"],
        horizontal=True
    )

    if data_option == "模拟数据（演示）":
        st.info("当前使用内置模拟数据。切换到其他选项可查看实际接入示例。")
        df_preview = pd.DataFrame({
            'sensor_id': [f'S{i:03d}' for i in range(1, 11)],
            'sensor_type': ['support_resistance'] * 10,
            'position': np.arange(0, 100, 10),
            'value': np.round(np.random.uniform(20, 32, 10), 2),
            'timestamp': [datetime.now()] * 10
        })
        st.dataframe(df_preview, use_container_width=True)

    elif data_option == "CSV文件上传":
        uploaded = st.file_uploader("上传矿压监测数据 (CSV)", type=['csv'])
        if uploaded is not None:
            try:
                df = pd.read_csv(uploaded)
                st.dataframe(df.head(20), use_container_width=True)
                st.success(f"✅ 已加载 {len(df)} 条记录，字段：{list(df.columns)}")
            except Exception as e:
                st.error(f"读取失败：{e}")

    elif data_option == "MQTT实时流":
        st.code("""
# 实际部署时的MQTT接入示例
import paho.mqtt.client as mqtt
import json

def on_message(client, userdata, msg):
    data = json.loads(msg.payload)
    # data: {"sensor_id": "S001", "value": 28.5,
    #        "type": "support_resistance", "position": 120.0}
    update_realtime_data(data)

client = mqtt.Client()
client.on_message = on_message
client.connect("mqtt.broker.address", 1883)
client.subscribe("mine/support/#")
client.loop_start()
        """, language="python")

    elif data_option == "数据库连接":
        st.code("""
# 时序数据库 InfluxDB 接入示例
from influxdb_client import InfluxDBClient

client = InfluxDBClient(
    url="http://localhost:8086",
    token="YOUR_TOKEN",
    org="mine_org"
)
query = '''
from(bucket: "mine_pressure")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "support_resistance")
'''
result = client.query_api().query(query)
        """, language="python")

    st.divider()
    st.subheader("建议的数据字段结构")
    schema = pd.DataFrame({
        '字段': ['sensor_id', 'sensor_type', 'position', 'value', 'timestamp'],
        '类型': ['str', 'str', 'float', 'float', 'datetime'],
        '说明': [
            '传感器编号',
            'support_resistance / stress / microseismic',
            '位置坐标 (m)',
            '测量值',
            '采集时间'
        ]
    })
    st.dataframe(schema, use_container_width=True, hide_index=True)


# ============================================================
# 主入口
# ============================================================
def main():
    # 侧边栏（保留项目信息，去掉导航）
    st.sidebar.title("⛏️ 地压监测系统")
    st.sidebar.markdown("**工作面**：3101 综采面")
    st.sidebar.markdown(f"**更新时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.sidebar.divider()
    st.sidebar.caption("""
    **系统说明**  
    本系统用于超长工作面地压监测分析，  
    支撑顶板活动、支架受力、围岩应力协同评价，  
    为超前支护参数确定与方案优化提供依据。
    """)

    # 主页面顶部 Tab 导航
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 总览仪表盘",
        "🔧 支架受力分析",
        "🛡️ 围岩应力与超前支护",
        "🔍 支护优化评估",
        "🔌 数据接入配置"
    ])

    with tab1:
        page_dashboard()
    with tab2:
        page_support_analysis()
    with tab3:
        page_advanced_support()
    with tab4:
        page_optimization()
    with tab5:
        page_data_source()


if __name__ == "__main__":
    main()