"""Onboarding Weekly Report — Streamlit Web App"""

import re
import sys
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

from load_data import load_from_upload, CSVParseError
from analysis import run_analysis
from render_excel import render_excel_bytes
from render_html import render_html


def render_html_string(result: dict) -> str:
    """Render HTML report to a string for download."""
    import tempfile, os
    fd, path = tempfile.mkstemp(suffix='.html')
    try:
        os.close(fd)
        render_html(result, path)
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    finally:
        os.unlink(path)


def strip_html(text):
    if not isinstance(text, str):
        return text
    return re.sub(r'<[^>]+>', '', text)


def clean_row(d: dict) -> dict:
    return {k: strip_html(v) for k, v in d.items()}


# --- Chart Helpers ---

def funnel_chart(result):
    labels = ['注册', 'KYC1', 'KYC2', '充值', '交易']
    tw_vals = [r['tw_raw'] for r in result['funnel']
               if r['metric'] in ('注册人数', 'KYC1 人数', 'KYC2 人数', '充值人数', '交易人数')]
    pw_vals = [r['pw_raw'] for r in result['funnel']
               if r['metric'] in ('注册人数', 'KYC1 人数', 'KYC2 人数', '充值人数', '交易人数')]
    fig = go.Figure()
    fig.add_trace(go.Bar(name='本周', x=labels, y=tw_vals))
    fig.add_trace(go.Bar(name='前4周均值', x=labels, y=[v / 4 for v in pw_vals]))
    fig.update_layout(barmode='group', title='漏斗人数对比', showlegend=True)
    return fig


def spot_futures_chart(result):
    sf = result['spot_futures']
    fig = go.Figure(data=[go.Pie(
        labels=['现货', '合约'],
        values=[sf['this_week']['spot_amount'], sf['this_week']['futures_amount']],
        textinfo='label+percent',
    )])
    fig.update_layout(title='交易金额占比（本周）')
    return fig


def monthly_reg_chart(result):
    m = result['monthly']
    fig = go.Figure()
    fig.add_trace(go.Bar(x=m['months'], y=m['reg'], name='注册人数'))
    fig.update_layout(title='月度注册人数')
    return fig


def monthly_rate_chart(result):
    m = result['monthly']
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=m['months'], y=m['deposit_rate'], name='充值率', mode='lines+markers'))
    fig.add_trace(go.Scatter(x=m['months'], y=m['trade_rate'], name='交易率', mode='lines+markers'))
    fig.add_trace(go.Scatter(x=m['months'], y=m['kyc1_rate'], name='KYC1率', mode='lines+markers'))
    fig.update_layout(title='月度转化率', yaxis_tickformat='.1%')
    return fig


def monthly_amount_chart(result):
    m = result['monthly']
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=m['months'], y=m['deposit_amount'], name='充值金额', mode='lines+markers'))
    fig.add_trace(go.Scatter(x=m['months'], y=m['trade_amount'], name='交易金额', mode='lines+markers'))
    fig.update_layout(title='月度金额')
    return fig


# --- Page Config ---

st.set_page_config(page_title="Onboarding 周报", page_icon="📊", layout="wide")
st.title("Onboarding 周报")

# --- Sidebar: File Upload ---

with st.sidebar:
    st.header("数据上传")
    st.caption("从后台导出两个 CSV 文件并上传")

    file_all = st.file_uploader(
        "全部数据（含羊毛）",
        type="csv",
        key="file_all",
    )
    file_filtered = st.file_uploader(
        "去羊毛数据",
        type="csv",
        key="file_filtered",
    )

    generate = st.button("生成报告", type="primary", use_container_width=True)

# --- Generate Report ---

if generate:
    if not file_all or not file_filtered:
        st.error("请上传两个 CSV 文件后再生成报告。")
        st.stop()

    with st.spinner("正在分析数据..."):
        try:
            df_all = load_from_upload(file_all)
        except CSVParseError as e:
            st.error(f"全部数据文件解析失败：{e}")
            st.stop()
        try:
            df_filtered = load_from_upload(file_filtered)
        except CSVParseError as e:
            st.error(f"去羊毛数据文件解析失败：{e}")
            st.stop()

        result = run_analysis(df_all, df_filtered)

    st.session_state["result"] = result
    st.session_state["excel_buf"] = render_excel_bytes(result)
    st.session_state["html_str"] = render_html_string(result)

if "result" not in st.session_state:
    st.info("上传两个 CSV 文件，然后点击「生成报告」。")
    st.stop()

result = st.session_state["result"]
meta = result["meta"]

# --- Report Header ---

st.subheader(f"报告期：{meta['report_start']} ~ {meta['report_end']}")
st.caption(f"对比期：{meta['compare_start']} ~ {meta['compare_end']}")

# Download buttons in sidebar
with st.sidebar:
    st.divider()
    st.header("下载报告")
    if "excel_buf" in st.session_state:
        st.download_button(
            "Excel 报告",
            data=st.session_state["excel_buf"],
            file_name=f"weekly-report-{meta['report_end']}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    if "html_str" in st.session_state:
        st.download_button(
            "HTML 报告",
            data=st.session_state["html_str"].encode('utf-8'),
            file_name=f"weekly-report-{meta['report_end']}.html",
            mime="text/html",
            use_container_width=True,
        )

# --- 1. Funnel Overview ---

st.header("1. 漏斗总览")

funnel_data = []
for r in result['funnel']:
    funnel_data.append(clean_row({
        '指标': r['metric'],
        '本周': r['this_week'],
        '前4周均值': r['prev_4weeks'],
        '变化': r['change'],
    }))
st.dataframe(pd.DataFrame(funnel_data), hide_index=True, use_container_width=True)
st.plotly_chart(funnel_chart(result), use_container_width=True)

# --- 2. Per Capita ---

st.header("2. 人均金额")

pc_data = []
for r in result['per_capita']:
    pc_data.append(clean_row({
        '指标': r['metric'],
        '本周': r['this_week'],
        '前4周均值': r['prev_4weeks'],
        '变化': r['change'],
    }))
st.dataframe(pd.DataFrame(pc_data), hide_index=True, use_container_width=True)

# --- 3. Spot vs Futures ---

st.header("3. 现货 vs 合约（本周）")

sf = result['spot_futures']
sf_data = [
    {'类型': '现货', '交易人数': sf['this_week']['spot_count'],
     '交易金额': f"{sf['this_week']['spot_amount']:.2f}",
     '占比': f"{sf['this_week']['spot_pct']:.1%}"},
    {'类型': '合约', '交易人数': sf['this_week']['futures_count'],
     '交易金额': f"{sf['this_week']['futures_amount']:.2f}",
     '占比': f"{sf['this_week']['futures_pct']:.1%}"},
]
st.dataframe(pd.DataFrame(sf_data), hide_index=True, use_container_width=True)
st.plotly_chart(spot_futures_chart(result), use_container_width=True)

# --- 4. Channel Ranking ---

st.header("4. 渠道排名")

ch_data = []
for r in result['channels']['rows']:
    ch_data.append(clean_row({
        '排名': r['rank'], '渠道': r['channel'], '注册量': r['reg'],
        '充值率': r['deposit_rate'], '交易率': r['trade_rate'],
        '人均交易': r['avg_trade'], '交易金额': r['trade_amount'],
        '排名变化': r['rank_change'],
    }))
st.dataframe(pd.DataFrame(ch_data), hide_index=True, use_container_width=True)

# --- 5. Country Top 10 ---

st.header("5. 国家 Top 10")

ct_data = []
for r in result['countries']:
    ct_data.append(clean_row({
        '排名': r['rank'], '国家': r['country'], '注册量': r['reg'],
        '充值率': r['deposit_rate'], '交易率': r['trade_rate'],
        '人均充值': r['avg_deposit'], '人均交易': r['avg_trade'],
        '充值率变化': r['dep_change'], '交易率变化': r['trade_change'],
    }))
st.dataframe(pd.DataFrame(ct_data), hide_index=True, use_container_width=True)

# --- 6. Wool Analysis ---

st.header("6. 羊毛分析")

wool = result['wool']
wool_data = []
for r in wool['channels']:
    wool_data.append(clean_row({
        '渠道': r['channel'], '全部注册': r['total'],
        '去羊毛注册': r['filtered'], '羊毛量': r['wool'],
        '羊毛比例': r['wool_pct'], '变化': r['change'],
    }))
st.dataframe(pd.DataFrame(wool_data), hide_index=True, use_container_width=True)

ov = wool['overall']
st.info(
    f"总计：本周羊毛 {ov['tw_wool']:,} / {ov['tw_total']:,}（{ov['tw_pct']}），"
    f"前4周均值 {ov['pw_wool']:,} / {ov['pw_total']:,}（{ov['pw_pct']}）"
)

# --- 7. Monthly Trend ---

st.header("7. 月度趋势")

st.subheader("月度注册人数")
st.plotly_chart(monthly_reg_chart(result), use_container_width=True)

st.subheader("月度转化率")
st.plotly_chart(monthly_rate_chart(result), use_container_width=True)

st.subheader("月度金额")
st.plotly_chart(monthly_amount_chart(result), use_container_width=True)
