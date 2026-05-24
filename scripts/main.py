"""Entry point: load data, run analysis, generate reports."""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))

from load_data import load_all, load_filtered
from analysis import run_analysis
from render_html import render_html
from render_excel import render_excel

OUTPUT_DIR = Path(__file__).resolve().parent.parent / 'output'


def main():
    print('Loading data...')
    df_all = load_all()
    df_filtered = load_filtered()
    print(f'  All: {len(df_all)} rows, Filtered: {len(df_filtered)} rows')
    print(f'  Date range: {df_all["date"].min().date()} ~ {df_all["date"].max().date()}')

    print('Running analysis...')
    result = run_analysis(df_all, df_filtered)

    date_tag = result['meta']['report_end']
    html_path = OUTPUT_DIR / f'weekly-report-{date_tag}.html'
    excel_path = OUTPUT_DIR / f'weekly-report-{date_tag}.xlsx'

    print(f'Rendering HTML: {html_path}')
    render_html(result, str(html_path))

    print(f'Rendering Excel: {excel_path}')
    render_excel(result, str(excel_path))

    print(f'Done. Output:')
    print(f'  HTML:  {html_path}')
    print(f'  Excel: {excel_path}')


if __name__ == '__main__':
    main()
