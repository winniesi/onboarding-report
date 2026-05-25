"""Render analysis results as an HTML report with Plotly charts."""

from typing import List, Optional
import json
import plotly.graph_objects as go
from pathlib import Path

# Chart specs: collected during rendering, rendered at end as one script block
ChartSpec = object


def _make_chart(fig: go.Figure, div_id: str) -> dict:
    fig.update_layout(
        margin=dict(l=50, r=20, t=30, b=40),
        height=350,
        font=dict(size=12),
    )
    return {'id': div_id, 'data': fig.to_json()}


def _chart_div(div_id: str) -> str:
    return f'<div id="{div_id}" style="width:100%;height:380px;"></div>\n'


def _table_html(headers: List[str], rows: List[List[str]], widths: Optional[List[str]] = None) -> str:
    width_style = ''
    if widths:
        col_styles = ''.join(f'<col style="width:{w}">' for w in widths)
        width_style = f'<colgroup>{col_styles}</colgroup>'
    header_html = ''.join(f'<th>{h}</th>' for h in headers)
    body_html = ''
    for row in rows:
        body_html += '<tr>' + ''.join(f'<td>{cell}</td>' for cell in row) + '</tr>'
    return f'<table>{width_style}<thead><tr>{header_html}</tr></thead><tbody>{body_html}</tbody></table>'


def render_html(result: dict, output_path: str):
    m = result['meta']
    charts = []
    body_parts = []

    def add(heading, content, chart=None):
        body_parts.append(heading + content)
        if chart:
            charts.append(chart)

    # 1. Funnel overview
    funnel_rows = []
    for r in result['funnel']:
        funnel_rows.append([r['metric'], r['this_week'], r['prev_4weeks'], r['change']])
    add('<h2>1. 漏斗总览</h2>',
        _table_html(['指标', '本周', '前4周均值', '变化'], funnel_rows))

    fig = go.Figure()
    labels = ['注册', 'KYC1', 'KYC2', '充值', '交易']
    tw_vals = [r['tw_raw'] for r in result['funnel'] if r['metric'] in ('注册人数', 'KYC1 人数', 'KYC2 人数', '充值人数', '交易人数')]
    pw_vals = [r['pw_raw'] for r in result['funnel'] if r['metric'] in ('注册人数', 'KYC1 人数', 'KYC2 人数', '充值人数', '交易人数')]
    fig.add_trace(go.Bar(name='本周', x=labels, y=tw_vals))
    fig.add_trace(go.Bar(name='前4周均值', x=labels, y=pw_vals))
    fig.update_layout(barmode='group', title='漏斗人数对比', showlegend=True)
    add('', _chart_div('funnel_chart'), _make_chart(fig, 'funnel_chart'))

    # 2. Per capita
    pc_rows = []
    for r in result['per_capita']:
        pc_rows.append([r['metric'], r['this_week'], r['prev_4weeks'], r['change']])
    add('<h2>2. 人均金额</h2>',
        _table_html(['指标', '本周', '前4周均值', '变化'], pc_rows))

    # 3. Spot vs futures
    sf = result['spot_futures']
    sf_rows = [
        ['现货', str(sf['this_week']['spot_count']),
         f"{sf['this_week']['spot_amount']:.2f}", f"{sf['this_week']['spot_pct']:.1%}"],
        ['合约', str(sf['this_week']['futures_count']),
         f"{sf['this_week']['futures_amount']:.2f}", f"{sf['this_week']['futures_pct']:.1%}"],
    ]
    add('<h2>3. 现货 vs 合约（本周）</h2>',
        _table_html(['类型', '交易人数', '交易金额', '占比'], sf_rows))

    fig = go.Figure(data=[go.Pie(
        labels=['现货', '合约'],
        values=[sf['this_week']['spot_amount'], sf['this_week']['futures_amount']],
        textinfo='label+percent',
    )])
    fig.update_layout(title='交易金额占比')
    add('', _chart_div('spot_futures_chart'), _make_chart(fig, 'spot_futures_chart'))

    # 4. Channel ranking
    ch_rows = []
    for r in result['channels']['rows']:
        ch_rows.append([str(r['rank']), r['channel'], str(r['reg']), r['deposit_rate'],
                        r['trade_rate'], r['avg_trade'], r['trade_amount'], r['rank_change']])
    add('<h2>4. 渠道排名</h2>',
        _table_html(['排名', '渠道', '注册量', '充值率', '交易率', '人均交易', '交易金额', '排名变化'], ch_rows))

    # 5. Country top 10
    ct_rows = []
    for r in result['countries']:
        ct_rows.append([str(r['rank']), r['country'], str(r['reg']), str(r['deposit_count']), r['deposit_rate'],
                        r['trade_rate'], r['avg_deposit'], r['avg_trade'], r['dep_change'], r['trade_change']])
    add('<h2>5. 国家 Top 10</h2>',
        _table_html(['排名', '国家', '注册量', '充值人数', '充值率', '交易率', '人均充值', '人均交易', '充值率变化', '交易率变化'], ct_rows))

    # 6. Wool analysis
    wool = result['wool']
    wool_rows = [[r['channel'], str(r['total']), str(r['filtered']), str(r['wool']), r['wool_pct'], r['change']]
                 for r in wool['channels']]
    add('<h2>6. 羊毛分析</h2>',
        _table_html(['渠道', '全部注册', '去羊毛注册', '羊毛量', '羊毛比例', '变化'], wool_rows))
    ov = wool['overall']
    add('', f'<p class="summary">总计：本周羊毛 {ov["tw_wool"]} / {ov["tw_total"]} ({ov["tw_pct"]})，'
            f'前4周 {ov["pw_wool"]} / {ov["pw_total"]} ({ov["pw_pct"]})</p>')

    # 7. Monthly trend
    monthly = result['monthly']
    body_parts.append('<h2>7. 月度趋势</h2>')

    fig = go.Figure()
    fig.add_trace(go.Bar(x=monthly['months'], y=monthly['reg'], name='注册人数'))
    fig.update_layout(title='月度注册人数')
    add('', _chart_div('monthly_reg'), _make_chart(fig, 'monthly_reg'))

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monthly['months'], y=monthly['deposit_rate'], name='充值率', mode='lines+markers'))
    fig.add_trace(go.Scatter(x=monthly['months'], y=monthly['trade_rate'], name='交易率', mode='lines+markers'))
    fig.add_trace(go.Scatter(x=monthly['months'], y=monthly['kyc1_rate'], name='KYC1率', mode='lines+markers'))
    fig.update_layout(title='月度转化率', yaxis_tickformat='.1%')
    add('', _chart_div('monthly_rate'), _make_chart(fig, 'monthly_rate'))

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monthly['months'], y=monthly['deposit_amount'], name='充值金额', mode='lines+markers'))
    fig.add_trace(go.Scatter(x=monthly['months'], y=monthly['trade_amount'], name='交易金额', mode='lines+markers'))
    fig.update_layout(title='月度金额')
    add('', _chart_div('monthly_amount'), _make_chart(fig, 'monthly_amount'))

    # Build chart rendering script (single block at end)
    chart_script_parts = []
    for c in charts:
        chart_script_parts.append(
            f'var c_{c["id"]} = {c["data"]};\n'
            f'Plotly.newPlot("{c["id"]}", c_{c["id"]}.data, c_{c["id"]}.layout);'
        )
    chart_script = '\n'.join(chart_script_parts)

    body = '\n'.join(body_parts)

    html = HTML_TEMPLATE.format(
        title=f'Onboarding 周报 | {m["report_start"]} ~ {m["report_end"]}',
        meta=f'报告期：{m["report_start"]} ~ {m["report_end"]} | 对比期：{m["compare_start"]} ~ {m["compare_end"]}',
        body=body,
        chart_script=chart_script,
    )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/plotly.js@2.27.0/dist/plotly.min.js"></script>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 40px auto; max-width: 1100px; color: #333; }}
h1 {{ border-bottom: 2px solid #2563eb; padding-bottom: 8px; }}
h2 {{ margin-top: 40px; color: #1e40af; }}
.meta {{ color: #666; margin-bottom: 30px; }}
table {{ border-collapse: collapse; width: 100%; margin: 12px 0 24px; }}
th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: right; font-size: 13px; }}
th {{ background: #f1f5f9; text-align: center; font-weight: 600; }}
td:first-child, th:first-child {{ text-align: left; }}
tr:nth-child(even) {{ background: #fafafa; }}
.up {{ color: #16a34a; font-weight: 600; }}
.down {{ color: #dc2626; font-weight: 600; }}
.summary {{ background: #f8fafc; border-left: 3px solid #2563eb; padding: 10px 16px; margin: 12px 0; font-size: 14px; }}
</style>
</head>
<body>
<h1>Onboarding 周报</h1>
<p class="meta">{meta}</p>
{body}
<script>
window.addEventListener('DOMContentLoaded', function() {{
{chart_script}
}});
</script>
</body>
</html>"""
