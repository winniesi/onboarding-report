"""Load and clean onboarding CSV data."""

import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent

COLS = {
    'date': '用户注册日期',
    'country': '国家',
    'channel': '渠道',
    'reg': '注册人数',
    'kyc1': 'KYC1人数',
    'kyc2': 'KYC2人数',
    'deposit_count': '转化至充值人数',
    'deposit_amount': '充值总金额',
    'spot_count': '转化至现货交易人',
    'spot_amount': '现货交易总金额',
    'futures_count': '转化至合约交易人',
    'futures_amount': '合约交易总金额',
    'trade_count': '转化至交易人数',
    'trade_amount': '交易总金额',
}

NUMERIC_COLS = [k for k in COLS if k not in ('date', 'country', 'channel')]


def _load_file(filename: str) -> pd.DataFrame:
    path = DATA_DIR / filename
    df = pd.read_csv(path, dtype=str)
    df = df.rename(columns={
        COLS['date']: 'date',
        COLS['country']: 'country',
        COLS['channel']: 'channel',
        COLS['reg']: 'reg',
        COLS['kyc1']: 'kyc1',
        COLS['kyc2']: 'kyc2',
        COLS['deposit_count']: 'deposit_count',
        COLS['deposit_amount']: 'deposit_amount',
        COLS['spot_count']: 'spot_count',
        COLS['spot_amount']: 'spot_amount',
        COLS['futures_count']: 'futures_count',
        COLS['futures_amount']: 'futures_amount',
        COLS['trade_count']: 'trade_count',
        COLS['trade_amount']: 'trade_amount',
    })
    df['date'] = pd.to_datetime(df['date'])
    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col].replace('', '0'), errors='coerce').fillna(0)
    return df


def load_all() -> pd.DataFrame:
    return _load_file('注册漏斗-国家渠道-全部-1年.csv')


def load_filtered() -> pd.DataFrame:
    return _load_file('注册漏斗-国家渠道-去羊毛-1年.csv')
