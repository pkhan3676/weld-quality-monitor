# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import time
from datetime import datetime
import os
import plotly.graph_objects as go

st.set_page_config(
    page_title="Weld Monitor | Prince Khan",
    layout="wide",
    initial_sidebar_state="collapsed"
)

log_file   = "welding_log.csv"
alarm_file = "alarm_log.csv"

for k, v in [("voltage",5),("direction",1),
             ("last_update",0),("prev_voltage",None),
             ("prev_status",None)]:
    if k not in st.session_state:
        st.session_state[k] = v

t = time.time()
if t - st.session_state.last_update >= 0.8:
    st.session_state.voltage += 3 * st.session_state.direction
    if st.session_state.voltage >= 100: st.session_state.direction = -1
    elif st.session_state.voltage <= 5:  st.session_state.direction =  1
    st.session_state.last_update = t
voltage = st.session_state.voltage

def get_status(v):
    if v < 20:  return "BURN THROUGH", "CRITICAL", "#FF2D55"
    if v < 40:  return "POROSITY",     "FAULT",    "#FF6B00"
    if v < 60:  return "SPATTER",      "WARNING",  "#FFD60A"
    if v > 90:  return "UNSTABLE ARC", "ALARM",    "#BF5AF2"
    return "NORMAL WELD", "OK", "#30D158"

label, stype, scolor = get_status(voltage)

def save_data(v, s):
    row = pd.DataFrame({"Time":[datetime.now()],"Voltage":[v],"Status":[s]})
    row.to_csv(log_file, mode='a',
               header=not os.path.exists(log_file), index=False)

def save_alarm(v, s):
    row = pd.DataFrame({"Time":[datetime.now()],"Voltage":[v],"Status":[s]})
    row.to_csv(alarm_file, mode='a',
               header=not os.path.exists(alarm_file), index=False)

if (voltage != st.session_state.prev_voltage or
        label != st.session_state.prev_status):
    save_data(voltage, label)
    save_alarm(voltage, label)
    st.session_state.prev_voltage = voltage
    st.session_state.prev_status  = label

# ── CSS ───────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap');
html,body,[class*="css"]{{
    background-color:#080C10!important;
    color:#C8D8E8;
    font-family:'Rajdhani',sans-serif;
}}
.hdr{{display:flex;align-items:center;justify-content:space-between;
    padding:14px 28px;
    background:linear-gradient(90deg,#0D1520 0%,#0A1828 100%);
    border-bottom:1px solid #1A3050;margin-bottom:24px;}}
.hdr-title{{font-size:22px;font-weight:700;letter-spacing:3px;
    color:#E0F0FF;text-transform:uppercase;
    font-family:'Share Tech Mono',monospace;}}
.hdr-sub{{font-size:12px;color:#4A7090;letter-spacing:2px;
    font-family:'Share Tech Mono',monospace;}}
.hdr-time{{font-family:'Share Tech Mono',monospace;
    font-size:13px;color:#2A9D8F;letter-spacing:1px;}}
.kpi-row{{display:grid;grid-template-columns:repeat(4,1fr);
    gap:14px;margin-bottom:24px;padding:0 4px;}}
.kpi{{background:#0D1520;border:1px solid #1A3050;
    border-top:3px solid {scolor};border-radius:8px;
    padding:18px 20px;position:relative;}}
.kpi-label{{font-size:11px;color:#4A7090;letter-spacing:2px;
    text-transform:uppercase;
    font-family:'Share Tech Mono',monospace;margin-bottom:6px;}}
.kpi-value{{font-size:32px;font-weight:700;color:#E0F0FF;
    font-family:'Share Tech Mono',monospace;line-height:1;}}
.kpi-unit{{font-size:13px;color:#4A7090;margin-left:4px;}}
.kpi-badge{{position:absolute;top:14px;right:14px;
    font-size:10px;font-weight:700;padding:3px 8px;
    border-radius:4px;letter-spacing:1px;
    font-family:'Share Tech Mono',monospace;
    background:{scolor}33;color:{scolor};
    border:1px solid {scolor}88;}}
.status-bar{{background:{scolor}18;
    border:1px solid {scolor}44;
    border-left:4px solid {scolor};
    border-radius:6px;padding:14px 24px;
    margin-bottom:24px;
    display:flex;align-items:center;gap:16px;}}
.status-dot{{width:10px;height:10px;border-radius:50%;
    background:{scolor};
    animation:pulse 1.4s ease-in-out infinite;}}
@keyframes pulse{{
    0%,100%{{opacity:1;transform:scale(1)}}
    50%{{opacity:.5;transform:scale(1.3)}}}}
.status-type{{font-family:'Share Tech Mono',monospace;
    font-size:11px;color:{scolor};letter-spacing:2px;}}
.status-label{{font-size:18px;font-weight:700;
    color:#E0F0FF;letter-spacing:1px;}}
.sec-hdr{{font-family:'Share Tech Mono',monospace;
    font-size:11px;color:#2A9D8F;letter-spacing:3px;
    text-transform:uppercase;border-bottom:1px solid #1A3050;
    padding-bottom:8px;margin-bottom:16px;}}
#MainMenu,footer,header{{visibility:hidden}}
.block-container{{padding-top:0!important;padding-bottom:0!important}}
</style>
""", unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────
st.markdown(f"""
<div class="hdr">
  <div>
    <div class="hdr-title">⚡ Weld Quality Monitor</div>
    <div class="hdr-sub">STM32F407 · MATLAB Algorithm · Real-Time Detection</div>
  </div>
  <div class="hdr-time">{datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}</div>
</div>
""", unsafe_allow_html=True)

# ── KPI CARDS ─────────────────────────────────
total_alarms = 0
weld_quality = 100.0
if os.path.exists(alarm_file):
    adf = pd.read_csv(alarm_file)
    total_alarms = len(adf[adf['Status'] != 'NORMAL WELD'])
    total_rows   = len(adf)
    ok_rows      = len(adf[adf['Status'] == 'NORMAL WELD'])
    weld_quality = round(
        (ok_rows/total_rows*100) if total_rows else 100, 1)

st.markdown(f"""
<div class="kpi-row">
  <div class="kpi">
    <div class="kpi-badge">{stype}</div>
    <div class="kpi-label">Arc Voltage</div>
    <div class="kpi-value">{voltage:.0f}
      <span class="kpi-unit">V</span></div>
  </div>
  <div class="kpi">
    <div class="kpi-label">Weld Quality</div>
    <div class="kpi-value">{weld_quality}
      <span class="kpi-unit">%</span></div>
  </div>
  <div class="kpi">
    <div class="kpi-label">Total Alarms</div>
    <div class="kpi-value">{total_alarms}
      <span class="kpi-unit">events</span></div>
  </div>
  <div class="kpi">
    <div class="kpi-label">Sample Rate</div>
    <div class="kpi-value">10
      <span class="kpi-unit">kHz</span></div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── STATUS BANNER ─────────────────────────────
st.markdown(f"""
<div class="status-bar">
  <div class="status-dot"></div>
  <div>
    <div class="status-type">{stype}</div>
    <div class="status-label">{label}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── GAUGE + TREND ─────────────────────────────
col1, col2 = st.columns([1, 2])

with col1:
    st.markdown(
        '<div class="sec-hdr">── Voltage Gauge</div>',
        unsafe_allow_html=True)

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=voltage,
        number={'font': {'size': 56,
                         'family': 'Share Tech Mono',
                         'color': '#E0F0FF'},
                'suffix': ' V'},
        gauge={
            'axis': {
                'range': [0, 100],
                'tickfont': {'color': '#4A7090', 'size': 10},
                'tickcolor': '#1A3050'
            },
            'bar':  {'color': scolor, 'thickness': 0.25},
            'bgcolor': '#0A1828',
            'borderwidth': 0,
            'steps': [
                {'range': [0,  20], 'color': '#1a0808'},
                {'range': [20, 40], 'color': '#1a1008'},
                {'range': [40, 60], 'color': '#1a1800'},
                {'range': [60, 90], 'color': '#081a0d'},
                {'range': [90,100], 'color': '#120818'},
            ],
            'threshold': {
                'line': {'color': scolor, 'width': 3},
                'thickness': 0.8,
                'value': voltage
            }
        }
    ))
    fig.update_layout(
        height=280,
        margin=dict(l=20, r=20, t=20, b=10),
        paper_bgcolor='#0D1520',
        font={'color': '#C8D8E8'}
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown(
        '<div class="sec-hdr">── Voltage Trend</div>',
        unsafe_allow_html=True)

    if os.path.exists(log_file):
        df = pd.read_csv(log_file)
        df["Time"] = pd.to_datetime(df["Time"])
        df = df.tail(200)

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=df["Time"], y=df["Voltage"],
            mode='lines',
            line=dict(color=scolor, width=2),
            fill='tozeroy',
            fillcolor='rgba(42,157,143,0.08)',
            name='Voltage'
        ))
        for y, c, n in [
            (20, '#FF2D55', 'Burn'),
            (40, '#FF6B00', 'Porosity'),
            (60, '#FFD60A', 'Spatter'),
            (90, '#BF5AF2', 'Unstable')
        ]:
            fig2.add_hline(
                y=y, line_dash='dot',
                line_color=c, opacity=0.5,
                annotation_text=n,
                annotation_font_color=c,
                annotation_font_size=10)

        fig2.update_layout(
            height=260,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor='#0D1520',
            plot_bgcolor='#0A1828',
            xaxis=dict(showgrid=False,
                       color='#4A7090',
                       tickfont={'size': 9}),
            yaxis=dict(gridcolor='#151F2C',
                       color='#4A7090',
                       range=[0, 105]),
            showlegend=False
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Waiting for data...")

# ── DEFECT INDICATORS ─────────────────────────
st.markdown(
    '<div class="sec-hdr" style="margin-top:8px">── Defect Indicators</div>',
    unsafe_allow_html=True)

d1, d2, d3, d4 = st.columns(4)
defects = [
    ("BURN THROUGH",  voltage < 20,       "#FF2D55", d1),
    ("POROSITY",      20<=voltage<40,      "#FF6B00", d2),
    ("SPATTER",       40<=voltage<60,      "#FFD60A", d3),
    ("UNSTABLE ARC",  voltage > 90,        "#BF5AF2", d4),
]
for name, active, color, col in defects:
    bg   = f"rgba({int(color[1:3],16)},"  \
           f"{int(color[3:5],16)},"        \
           f"{int(color[5:7],16)},0.15)"  \
           if active else "#0D1520"
    bord = color if active else "#1A3050"
    icon = "●"   if active else "○"
    with col:
        st.markdown(f"""
        <div style="background:{bg};border:1px solid {bord};
             border-radius:6px;padding:12px 16px;text-align:center">
          <div style="font-family:'Share Tech Mono',monospace;
               font-size:10px;color:{color};letter-spacing:2px">
            {icon} {name}</div>
          <div style="font-size:18px;font-weight:700;
               color:{'#E0F0FF' if active else '#2A4060'};
               margin-top:4px">
            {'ACTIVE' if active else 'CLEAR'}</div>
        </div>
        """, unsafe_allow_html=True)

# ── ALARM LOG ─────────────────────────────────
st.markdown(
    '<div class="sec-hdr" style="margin-top:20px">── Event Log</div>',
    unsafe_allow_html=True)

if os.path.exists(alarm_file):
    adf = pd.read_csv(alarm_file).tail(8)
    adf["Time"] = pd.to_datetime(
        adf["Time"]).dt.strftime('%H:%M:%S')
    st.dataframe(adf, use_container_width=True,
                 hide_index=True)
else:
    st.info("No events logged yet")

# ── DOWNLOAD ──────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
if os.path.exists(log_file):
    with open(log_file, "rb") as f:
        st.download_button(
            "⬇️ Export Weld Log (CSV)", f,
            "weld_log.csv", "text/csv")

# ── AUTO REFRESH ──────────────────────────────
time.sleep(0.8)
st.rerun()

