# -*- coding: utf-8 -*-
"""
Created on Mon Mar 30 16:11:20 2026

@author: pkhan
"""

import streamlit as st
import serial
import serial.tools.list_ports
import pandas as pd
import re
import time
from collections import deque
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Weld Monitor | STM32 Live",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── CUSTOM CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Rajdhani', sans-serif;
    background-color: #0a0e1a;
    color: #e0e6f0;
}

.main { background-color: #0a0e1a; }

/* Title */
.title-bar {
    background: linear-gradient(90deg, #0d1b2a, #1a2f4a);
    border-left: 4px solid #00d4ff;
    padding: 16px 24px;
    margin-bottom: 20px;
    border-radius: 4px;
}
.title-bar h1 {
    font-family: 'Rajdhani', sans-serif;
    font-weight: 700;
    font-size: 2rem;
    color: #00d4ff;
    margin: 0;
    letter-spacing: 3px;
    text-transform: uppercase;
}
.title-bar p {
    color: #7090b0;
    margin: 4px 0 0 0;
    font-size: 0.9rem;
    letter-spacing: 1px;
}

/* Metric Cards */
.metric-card {
    background: linear-gradient(135deg, #0d1b2a 0%, #132030 100%);
    border: 1px solid #1e3a5a;
    border-radius: 8px;
    padding: 20px;
    text-align: center;
    margin-bottom: 12px;
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, #00d4ff, transparent);
}
.metric-label {
    font-size: 0.75rem;
    color: #7090b0;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.metric-value {
    font-family: 'Share Tech Mono', monospace;
    font-size: 2.2rem;
    font-weight: bold;
    color: #00d4ff;
}
.metric-value.warn { color: #ffa500; }
.metric-value.danger { color: #ff4444; }
.metric-value.ok { color: #00ff88; }

/* Status Badge */
.status-badge {
    display: inline-block;
    padding: 6px 18px;
    border-radius: 20px;
    font-weight: 700;
    font-size: 0.9rem;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin: 8px 4px;
}
.badge-ok    { background: rgba(0,255,136,0.15); border: 1px solid #00ff88; color: #00ff88; }
.badge-warn  { background: rgba(255,165,0,0.15);  border: 1px solid #ffa500; color: #ffa500; }
.badge-fault { background: rgba(255,68,68,0.15);  border: 1px solid #ff4444; color: #ff4444; }

/* Fault indicators */
.fault-grid { display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; }
.fault-chip {
    padding: 8px 16px;
    border-radius: 6px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 1rem;
    font-weight: bold;
    letter-spacing: 1px;
}
.fault-off { background: #0d1b2a; border: 1px solid #1e3a5a; color: #3a5a7a; }
.fault-on  { background: rgba(255,68,68,0.2); border: 1px solid #ff4444; color: #ff4444;
             box-shadow: 0 0 12px rgba(255,68,68,0.3); animation: pulse 1s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.7} }

/* Log box */
.log-box {
    background: #060c14;
    border: 1px solid #1e3a5a;
    border-radius: 6px;
    padding: 12px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.78rem;
    color: #00d4ff;
    height: 200px;
    overflow-y: auto;
    white-space: pre;
}
</style>
""", unsafe_allow_html=True)

# ─── SIDEBAR CONFIG ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Connection Settings")

    # Auto-detect available ports
    ports = [p.device for p in serial.tools.list_ports.comports()]
    default_port = "COM10" if "COM10" in ports else (ports[0] if ports else "COM10")

    port = st.selectbox("Serial Port", options=ports if ports else ["COM10"], index=0)
    baud = st.selectbox("Baud Rate", [115200, 9600, 57600], index=0)

    st.markdown("---")
    st.markdown("### 🎯 Fault Thresholds")
    th_spatter  = st.number_input("Spatter STD >",   value=2.1943, format="%.4f")
    th_burn     = st.number_input("Burn RMS >",      value=2.1607, format="%.4f")
    th_instab   = st.number_input("Instability Range >", value=0.2410, format="%.4f")
    th_porosity = st.number_input("Porosity MIN <",  value=0.8000, format="%.4f")

    st.markdown("---")
    max_points = st.slider("Graph history (samples)", 50, 500, 100)

    st.markdown("---")
    start_btn = st.button("▶ START MONITORING", use_container_width=True, type="primary")
    stop_btn  = st.button("⏹ STOP",             use_container_width=True)

# ─── TITLE ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="title-bar">
  <h1>⚡ Weld Monitor — STM32 Live Dashboard</h1>
  <p>Real-time signal analysis via UART | STM32F446RE Nucleo</p>
</div>
""", unsafe_allow_html=True)

# ─── SESSION STATE ────────────────────────────────────────────────────────────
if 'running'   not in st.session_state: st.session_state.running   = False
if 'rms_hist'  not in st.session_state: st.session_state.rms_hist  = deque(maxlen=max_points)
if 'std_hist'  not in st.session_state: st.session_state.std_hist  = deque(maxlen=max_points)
if 'min_hist'  not in st.session_state: st.session_state.min_hist  = deque(maxlen=max_points)
if 'max_hist'  not in st.session_state: st.session_state.max_hist  = deque(maxlen=max_points)
if 'time_hist' not in st.session_state: st.session_state.time_hist = deque(maxlen=max_points)
if 'log_lines' not in st.session_state: st.session_state.log_lines = deque(maxlen=30)
if 'fault_counts' not in st.session_state:
    st.session_state.fault_counts = {'SP': 0, 'BU': 0, 'IN': 0, 'PO': 0}

if start_btn: st.session_state.running = True
if stop_btn:  st.session_state.running = False

# ─── PARSE STM32 LINE ─────────────────────────────────────────────────────────
def parse_line(line):
    """Parse: RMS:1.652 STD:0.071 MIN:1.549 MAX:1.754 | SP:0 BU:0 IN:0 PO:0"""
    pattern = r'RMS:([\d.]+)\s+STD:([\d.]+)\s+MIN:([\d.]+)\s+MAX:([\d.]+).*SP:(\d)\s+BU:(\d)\s+IN:(\d)\s+PO:(\d)'
    m = re.search(pattern, line)
    if m:
        return {
            'rms': float(m.group(1)), 'std': float(m.group(2)),
            'min': float(m.group(3)), 'max': float(m.group(4)),
            'SP': int(m.group(5)),    'BU': int(m.group(6)),
            'IN': int(m.group(7)),    'PO': int(m.group(8))
        }
    return None

# ─── LAYOUT ───────────────────────────────────────────────────────────────────
col_metrics, col_chart = st.columns([1, 2.5])

with col_metrics:
    rms_ph  = st.empty()
    std_ph  = st.empty()
    min_ph  = st.empty()
    max_ph  = st.empty()
    fault_ph = st.empty()
    status_ph = st.empty()

with col_chart:
    chart_ph = st.empty()

log_ph = st.empty()
stats_ph = st.empty()

# ─── HELPER: RENDER METRICS ───────────────────────────────────────────────────
def render_metrics(d):
    rms_cls = 'danger' if d['BU'] else ('warn' if d['rms'] > 1.8 else 'ok')
    std_cls = 'danger' if d['SP'] else 'ok'
    min_cls = 'danger' if d['PO'] else 'ok'
    rng = d['max'] - d['min']
    rng_cls = 'danger' if d['IN'] else 'ok'

    rms_ph.markdown(f"""
    <div class="metric-card">
      <div class="metric-label">RMS Voltage</div>
      <div class="metric-value {rms_cls}">{d['rms']:.3f} V</div>
    </div>""", unsafe_allow_html=True)

    std_ph.markdown(f"""
    <div class="metric-card">
      <div class="metric-label">Std Deviation</div>
      <div class="metric-value {std_cls}">{d['std']:.3f} V</div>
    </div>""", unsafe_allow_html=True)

    min_ph.markdown(f"""
    <div class="metric-card">
      <div class="metric-label">MIN / MAX</div>
      <div class="metric-value {min_cls}">{d['min']:.3f} / {d['max']:.3f} V</div>
    </div>""", unsafe_allow_html=True)

    max_ph.markdown(f"""
    <div class="metric-card">
      <div class="metric-label">Signal Range</div>
      <div class="metric-value {rng_cls}">{rng:.3f} V</div>
    </div>""", unsafe_allow_html=True)

    # Fault chips
    def chip(label, active):
        cls = 'fault-on' if active else 'fault-off'
        return f'<div class="fault-chip {cls}">{label}</div>'

    fault_ph.markdown(f"""
    <div class="metric-card">
      <div class="metric-label">Fault Indicators</div>
      <div class="fault-grid">
        {chip('SP SPATTER', d['SP'])}
        {chip('BU BURN', d['BU'])}
        {chip('IN INSTAB', d['IN'])}
        {chip('PO POROSITY', d['PO'])}
      </div>
    </div>""", unsafe_allow_html=True)

    # Overall status
    any_fault = d['SP'] or d['BU'] or d['IN'] or d['PO']
    if any_fault:
        faults = ' + '.join([k for k in ['SP','BU','IN','PO'] if d[k]])
        status_ph.markdown(f'<div style="text-align:center"><span class="status-badge badge-fault">🔴 FAULT: {faults}</span></div>', unsafe_allow_html=True)
    else:
        status_ph.markdown('<div style="text-align:center"><span class="status-badge badge-ok">🟢 NORMAL</span></div>', unsafe_allow_html=True)

# ─── HELPER: RENDER CHART ─────────────────────────────────────────────────────
def render_chart():
    if len(st.session_state.time_hist) < 2:
        return
    t   = list(st.session_state.time_hist)
    rms = list(st.session_state.rms_hist)
    std = list(st.session_state.std_hist)
    mn  = list(st.session_state.min_hist)
    mx  = list(st.session_state.max_hist)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        subplot_titles=('RMS & Signal Range', 'Std Deviation'),
                        row_heights=[0.65, 0.35],
                        vertical_spacing=0.1)

    # Shaded min-max band
    fig.add_trace(go.Scatter(x=t+t[::-1], y=mx+mn[::-1],
        fill='toself', fillcolor='rgba(0,212,255,0.08)',
        line=dict(color='rgba(0,212,255,0)'), name='Range', showlegend=True), row=1, col=1)

    fig.add_trace(go.Scatter(x=t, y=rms, name='RMS',
        line=dict(color='#00d4ff', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=t, y=mx, name='MAX',
        line=dict(color='#ffa500', width=1, dash='dot')), row=1, col=1)
    fig.add_trace(go.Scatter(x=t, y=mn, name='MIN',
        line=dict(color='#ff6b6b', width=1, dash='dot')), row=1, col=1)

    fig.add_trace(go.Scatter(x=t, y=std, name='STD',
        line=dict(color='#b87fff', width=2)), row=2, col=1)

    # Threshold lines
    fig.add_hline(y=th_burn,     line_dash='dash', line_color='#ff4444', opacity=0.5,
                  annotation_text='BU threshold', row=1, col=1)
    fig.add_hline(y=th_porosity, line_dash='dash', line_color='#ffa500', opacity=0.5,
                  annotation_text='PO threshold', row=1, col=1)
    fig.add_hline(y=th_spatter,  line_dash='dash', line_color='#ff4444', opacity=0.5,
                  annotation_text='SP threshold', row=2, col=1)

    fig.update_layout(
        height=400,
        paper_bgcolor='#0a0e1a',
        plot_bgcolor='#060c14',
        font=dict(color='#7090b0', family='Share Tech Mono'),
        legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(size=11)),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis2=dict(showticklabels=False)
    )
    fig.update_xaxes(gridcolor='#1a2a3a', zeroline=False)
    fig.update_yaxes(gridcolor='#1a2a3a', zeroline=False)

    chart_ph.plotly_chart(fig, use_container_width=True)

# ─── MAIN MONITORING LOOP ─────────────────────────────────────────────────────
if st.session_state.running:
    try:
        ser = serial.Serial(port, baud, timeout=2)
        st.success(f"✅ Connected to {port} @ {baud} baud")
        time.sleep(0.5)

        sample_count = 0
        start_time = time.time()

        while st.session_state.running:
            try:
                raw = ser.readline().decode('utf-8', errors='ignore').strip()
                if not raw:
                    continue

                d = parse_line(raw)
                if d is None:
                    continue

                # Store history
                now = datetime.now().strftime('%H:%M:%S')
                st.session_state.rms_hist.append(d['rms'])
                st.session_state.std_hist.append(d['std'])
                st.session_state.min_hist.append(d['min'])
                st.session_state.max_hist.append(d['max'])
                st.session_state.time_hist.append(now)
                st.session_state.log_lines.append(raw)

                # Fault counts
                for k in ['SP','BU','IN','PO']:
                    if d[k]: st.session_state.fault_counts[k] += 1

                sample_count += 1

                # Render
                render_metrics(d)
                render_chart()

                # Log
                log_text = '\n'.join(list(st.session_state.log_lines)[-15:])
                log_ph.markdown(f'<div class="log-box">{log_text}</div>', unsafe_allow_html=True)

                # Stats
                elapsed = time.time() - start_time
                fc = st.session_state.fault_counts
                stats_ph.markdown(f"""
                <div style="display:flex;gap:20px;padding:12px;background:#0d1b2a;border-radius:6px;
                            border:1px solid #1e3a5a;font-family:'Share Tech Mono';font-size:0.8rem;color:#7090b0;">
                  <span>📊 Samples: <b style="color:#00d4ff">{sample_count}</b></span>
                  <span>⏱ Elapsed: <b style="color:#00d4ff">{int(elapsed)}s</b></span>
                  <span>🔥 SP faults: <b style="color:#ff4444">{fc['SP']}</b></span>
                  <span>🔥 BU faults: <b style="color:#ff4444">{fc['BU']}</b></span>
                  <span>⚡ IN faults: <b style="color:#ffa500">{fc['IN']}</b></span>
                  <span>💧 PO faults: <b style="color:#ffa500">{fc['PO']}</b></span>
                </div>""", unsafe_allow_html=True)

            except Exception as e:
                time.sleep(0.1)

        ser.close()

    except serial.SerialException as e:
        st.error(f"❌ Cannot open {port}: {e}")
        st.info("Check: 1) PuTTY band karo pehle  2) COM port sahi hai?  3) STM32 connected hai?")
else:
    # Static placeholder when not running
    st.markdown("""
    <div style="text-align:center;padding:60px;background:#0d1b2a;border-radius:8px;border:1px dashed #1e3a5a;">
      <h2 style="color:#3a5a7a;font-family:'Rajdhani';letter-spacing:3px;">MONITORING PAUSED</h2>
      <p style="color:#3a5a7a;">Sidebar se port select karo, phir <b style="color:#00d4ff">▶ START MONITORING</b> dabao</p>
    </div>
    """, unsafe_allow_html=True)