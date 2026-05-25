"""Core analysis logic for onboarding funnel data."""

from typing import List, Optional
import pandas as pd
import numpy as np
from datetime import timedelta


def _aggregate(df: pd.DataFrame, group_cols: Optional[List[str]] = None) -> pd.DataFrame:
    """Aggregate raw data to specified granularity, computing sums and rates."""
    sum_cols = ['reg', 'kyc1', 'kyc2', 'deposit_count', 'deposit_amount',
                'spot_count', 'spot_amount', 'futures_count', 'futures_amount',
                'trade_count', 'trade_amount']
    if group_cols:
        agg = df.groupby(group_cols)[sum_cols].sum().reset_index()
    else:
        agg = pd.DataFrame([df[sum_cols].sum()])
    # Calculate rates from sums (never average pre-computed rates)
    agg['kyc1_rate'] = np.where(agg['reg'] > 0, agg['kyc1'] / agg['reg'], 0)
    agg['kyc2_rate'] = np.where(agg['reg'] > 0, agg['kyc2'] / agg['reg'], 0)
    agg['deposit_rate'] = np.where(agg['reg'] > 0, agg['deposit_count'] / agg['reg'], 0)
    agg['trade_rate'] = np.where(agg['deposit_count'] > 0, agg['trade_count'] / agg['deposit_count'], 0)
    agg['spot_rate'] = np.where(agg['deposit_count'] > 0, agg['spot_count'] / agg['deposit_count'], 0)
    agg['futures_rate'] = np.where(agg['deposit_count'] > 0, agg['futures_count'] / agg['deposit_count'], 0)
    agg['avg_deposit'] = np.where(agg['deposit_count'] > 0, agg['deposit_amount'] / agg['deposit_count'], 0)
    agg['avg_trade'] = np.where(agg['trade_count'] > 0, agg['trade_amount'] / agg['trade_count'], 0)
    agg['avg_spot'] = np.where(agg['spot_count'] > 0, agg['spot_amount'] / agg['spot_count'], 0)
    agg['avg_futures'] = np.where(agg['futures_count'] > 0, agg['futures_amount'] / agg['futures_count'], 0)
    return agg


def _filter_period(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    return df[(df['date'] >= start) & (df['date'] <= end)].copy()


def _change_pct(current: float, previous: float) -> Optional[float]:
    if previous == 0:
        return None
    return (current - previous) / previous * 100


def _pct(val: float) -> str:
    return f'{val:.2%}'


def _num(val: float) -> str:
    if val >= 1_000_000:
        return f'{val/1_000_000:.2f}M'
    if val >= 1_000:
        return f'{val/1_000:.2f}K'
    return f'{val:.0f}'


def _change_str(val: Optional[float]) -> str:
    if val is None:
        return '-'
    sign = '+' if val > 0 else ''
    color = 'green' if val > 0 else ('red' if val < 0 else '')
    return f'<span class="{"up" if val > 0 else ("down" if val < 0 else "")}">{sign}{val:.1f}%</span>'


def run_analysis(df_all: pd.DataFrame, df_filtered: pd.DataFrame) -> dict:
    latest = df_all['date'].max()
    week_start = latest - timedelta(days=6)
    prev_start = latest - timedelta(days=34)
    prev_end = latest - timedelta(days=7)

    meta = {
        'report_start': week_start.strftime('%Y-%m-%d'),
        'report_end': latest.strftime('%Y-%m-%d'),
        'compare_start': prev_start.strftime('%Y-%m-%d'),
        'compare_end': prev_end.strftime('%Y-%m-%d'),
        'latest': latest.strftime('%Y-%m-%d'),
    }

    # Period slices (use filtered data for main analysis)
    tw_filtered = _filter_period(df_filtered, week_start, latest)
    pw_filtered = _filter_period(df_filtered, prev_start, prev_end)
    tw_all = _filter_period(df_all, week_start, latest)
    pw_all = _filter_period(df_all, prev_start, prev_end)

    tw_agg = _aggregate(tw_filtered)
    pw_agg = _aggregate(pw_filtered)

    # 1. Funnel overview
    funnel = _build_funnel(tw_agg, pw_agg)

    # 2. Per capita
    per_capita = _build_per_capita(tw_agg, pw_agg)

    # 3. Spot vs futures
    spot_futures = _build_spot_futures(tw_agg, pw_agg)

    # 4. Channel ranking
    channels = _build_channel_ranking(tw_filtered, pw_filtered)

    # 5. Country top 10
    countries = _build_country_top10(tw_filtered, pw_filtered)

    # 6. Wool analysis
    wool = _build_wool(tw_all, pw_all, tw_filtered, pw_filtered)

    # 7. Monthly trend (use full data)
    monthly = _build_monthly(df_filtered)

    return {
        'meta': meta,
        'funnel': funnel,
        'per_capita': per_capita,
        'spot_futures': spot_futures,
        'channels': channels,
        'countries': countries,
        'wool': wool,
        'monthly': monthly,
    }


def _build_funnel(tw: pd.DataFrame, pw: pd.DataFrame) -> List[dict]:
    rows = []
    metrics = [
        ('注册人数', 'reg', False),
        ('KYC1 人数', 'kyc1', False),
        ('KYC1 率', 'kyc1_rate', True),
        ('KYC2 人数', 'kyc2', False),
        ('KYC2 率', 'kyc2_rate', True),
        ('充值人数', 'deposit_count', False),
        ('充值率', 'deposit_rate', True),
        ('充值金额', 'deposit_amount', False),
        ('交易人数', 'trade_count', False),
        ('交易率(充值→交易)', 'trade_rate', True),
        ('交易金额', 'trade_amount', False),
    ]
    for label, col, is_rate in metrics:
        tw_val = tw[col].iloc[0]
        pw_val = pw[col].iloc[0]
        # pw is 28-day sum; divide non-rate values by 4 for weekly average
        pw_avg = pw_val if is_rate else pw_val / 4
        change = _change_pct(tw_val, pw_avg)
        rows.append({
            'metric': label,
            'this_week': _pct(tw_val) if is_rate else _num(tw_val),
            'prev_4weeks': _pct(pw_avg) if is_rate else _num(pw_avg),
            'change': _change_str(change),
            'tw_raw': tw_val,
            'pw_raw': pw_avg,
        })
    return rows


def _build_per_capita(tw: pd.DataFrame, pw: pd.DataFrame) -> List[dict]:
    rows = []
    metrics = [
        ('人均充值', 'avg_deposit'),
        ('人均交易', 'avg_trade'),
        ('人均现货交易', 'avg_spot'),
        ('人均合约交易', 'avg_futures'),
    ]
    for label, col in metrics:
        tw_val = tw[col].iloc[0]
        pw_val = pw[col].iloc[0]
        change = _change_pct(tw_val, pw_val)
        rows.append({
            'metric': label,
            'this_week': f'{tw_val:.2f}',
            'prev_4weeks': f'{pw_val:.2f}',
            'change': _change_str(change),
        })
    return rows


def _build_spot_futures(tw: pd.DataFrame, pw: pd.DataFrame) -> dict:
    def _sf_row(agg, is_4weeks=False):
        div = 4 if is_4weeks else 1
        total = agg['spot_amount'].iloc[0] + agg['futures_amount'].iloc[0]
        spot_pct = agg['spot_amount'].iloc[0] / total if total > 0 else 0
        futures_pct = agg['futures_amount'].iloc[0] / total if total > 0 else 0
        return {
            'spot_count': int(agg['spot_count'].iloc[0] / div),
            'spot_amount': agg['spot_amount'].iloc[0] / div,
            'spot_pct': spot_pct,
            'futures_count': int(agg['futures_count'].iloc[0] / div),
            'futures_amount': agg['futures_amount'].iloc[0] / div,
            'futures_pct': futures_pct,
            'total_amount': total / div,
        }
    return {'this_week': _sf_row(tw), 'prev_4weeks': _sf_row(pw, is_4weeks=True)}


def _build_channel_ranking(tw: pd.DataFrame, pw: pd.DataFrame) -> dict:
    tw_ch = _aggregate(tw, ['channel']).sort_values('trade_amount', ascending=False)
    pw_ch = _aggregate(pw, ['channel']).sort_values('trade_amount', ascending=False)
    pw_rank = {row['channel']: i + 1 for i, row in pw_ch.iterrows()}

    rows = []
    for i, row in tw_ch.iterrows():
        ch = row['channel']
        tw_rank = len(rows) + 1
        prev_rank = pw_rank.get(ch)
        rank_change = (prev_rank - tw_rank) if prev_rank else None
        rows.append({
            'rank': tw_rank,
            'channel': ch,
            'reg': int(row['reg']),
            'deposit_rate': _pct(row['deposit_rate']),
            'trade_rate': _pct(row['trade_rate']),
            'avg_trade': f'{row["avg_trade"]:.2f}',
            'trade_amount': _num(row['trade_amount']),
            'rank_change': _change_str(rank_change) if rank_change is not None and rank_change != 0 else '-',
        })
    return {'rows': rows}


def _build_country_top10(tw: pd.DataFrame, pw: pd.DataFrame) -> List[dict]:
    tw_ct = _aggregate(tw, ['country']).sort_values('deposit_count', ascending=False).head(10)
    pw_ct = _aggregate(pw, ['country'])
    pw_dict = pw_ct.set_index('country').to_dict('index')

    rows = []
    for i, row in tw_ct.iterrows():
        country = row['country']
        pw_row = pw_dict.get(country, {})
        dep_change = _change_pct(row['deposit_rate'], pw_row.get('deposit_rate', 0))
        trade_change = _change_pct(row['trade_rate'], pw_row.get('trade_rate', 0))
        rows.append({
            'rank': len(rows) + 1,
            'country': country,
            'reg': int(row['reg']),
            'deposit_rate': _pct(row['deposit_rate']),
            'trade_rate': _pct(row['trade_rate']),
            'avg_deposit': f'{row["avg_deposit"]:.2f}',
            'avg_trade': f'{row["avg_trade"]:.2f}',
            'dep_change': _change_str(dep_change),
            'trade_change': _change_str(trade_change),
        })
    return rows


def _build_wool(tw_all: pd.DataFrame, pw_all: pd.DataFrame,
                tw_filtered: pd.DataFrame, pw_filtered: pd.DataFrame) -> dict:
    def _wool_by_channel(all_df, filt_df):
        a = _aggregate(all_df, ['channel']).set_index('channel')['reg']
        f = _aggregate(filt_df, ['channel']).set_index('channel')['reg']
        channels = a.index.union(f.index)
        rows = []
        for ch in channels:
            total = a.get(ch, 0)
            filtered = f.get(ch, 0)
            wool = total - filtered
            ratio = wool / total if total > 0 else 0
            rows.append({
                'channel': ch,
                'total': int(total),
                'filtered': int(filtered),
                'wool': int(wool),
                'wool_pct': _pct(ratio),
                'wool_raw': ratio,
            })
        return rows

    # This week
    tw_rows = _wool_by_channel(tw_all, tw_filtered)
    # Previous 4 weeks
    pw_rows = _wool_by_channel(pw_all, pw_filtered)
    pw_dict = {r['channel']: r['wool_raw'] for r in pw_rows}

    for r in tw_rows:
        prev = pw_dict.get(r['channel'], 0)
        change = _change_pct(r['wool_raw'], prev)
        r['change'] = _change_str(change)

    # Overall
    tw_total_all = _aggregate(tw_all)['reg'].iloc[0]
    tw_total_filt = _aggregate(tw_filtered)['reg'].iloc[0]
    pw_total_all = _aggregate(pw_all)['reg'].iloc[0]
    pw_total_filt = _aggregate(pw_filtered)['reg'].iloc[0]

    pw_wool_avg = (pw_total_all - pw_total_filt) / 4
    pw_total_avg = pw_total_all / 4
    return {
        'channels': tw_rows,
        'overall': {
            'tw_wool': int(tw_total_all - tw_total_filt),
            'tw_total': int(tw_total_all),
            'tw_pct': _pct((tw_total_all - tw_total_filt) / tw_total_all) if tw_total_all > 0 else '-',
            'pw_wool': int(pw_wool_avg),
            'pw_total': int(pw_total_avg),
            'pw_pct': _pct((pw_total_all - pw_total_filt) / pw_total_all) if pw_total_all > 0 else '-',
        },
    }


def _build_monthly(df: pd.DataFrame) -> dict:
    df = df.copy()
    df['month'] = df['date'].dt.to_period('M')
    monthly = _aggregate(df, ['month']).sort_values('month')

    months = [str(m) for m in monthly['month']]
    return {
        'months': months,
        'reg': monthly['reg'].tolist(),
        'deposit_rate': monthly['deposit_rate'].tolist(),
        'trade_rate': monthly['trade_rate'].tolist(),
        'deposit_amount': monthly['deposit_amount'].tolist(),
        'trade_amount': monthly['trade_amount'].tolist(),
        'kyc1_rate': monthly['kyc1_rate'].tolist(),
        'kyc2_rate': monthly['kyc2_rate'].tolist(),
    }
