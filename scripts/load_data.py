"""Load and clean onboarding CSV data."""

import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent

# Ordered list of (english_name, chinese_name) — order matches CSV column positions
COLS_ORDERED = [
    ('date', '用户注册日期'),
    ('country', '国家'),
    ('channel', '渠道'),
    ('reg', '注册人数'),
    ('kyc1', 'KYC1人数'),
    ('kyc2', 'KYC2人数'),
    ('deposit_count', '转化至充值人数'),
    ('deposit_amount', '充值总金额'),
    ('spot_count', '转化至现货交易人'),
    ('spot_amount', '现货交易总金额'),
    ('futures_count', '转化至合约交易人'),
    ('futures_amount', '合约交易总金额'),
    ('trade_count', '转化至交易人数'),
    ('trade_amount', '交易总金额'),
]

NUM_COLS = len(COLS_ORDERED)
COLS = dict(COLS_ORDERED)
NUMERIC_COLS = [k for k in COLS if k not in ('date', 'country', 'channel')]
RENAME_MAP = {v: k for k, v in COLS.items()}


class CSVParseError(Exception):
    pass


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns and convert types. Supports both name-based and positional mapping."""
    col_count = len(df.columns)

    # Try name-based mapping first
    matched = set(RENAME_MAP.keys()) & set(df.columns)
    if len(matched) >= NUM_COLS - 2:  # allow a couple missing if most match
        df = df.rename(columns=RENAME_MAP)
        df = df[list(COLS.keys())]
    elif col_count >= NUM_COLS:
        # Fall back to positional mapping (take first NUM_COLS columns)
        df.columns = [c if i >= NUM_COLS else COLS_ORDERED[i][0]
                      for i, c in enumerate(df.columns)]
        df = df[list(COLS.keys())]
    else:
        raise CSVParseError(
            f"列数不足：需要 {NUM_COLS} 列，实际只有 {col_count} 列。"
            f"请确认导出的 CSV 格式正确。"
        )

    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col].replace('', '0'), errors='coerce').fillna(0)
    return df


def _load_file(filename: str) -> pd.DataFrame:
    path = DATA_DIR / filename
    df = pd.read_csv(path, dtype=str)
    return _clean(df)


def load_from_upload(file_obj) -> pd.DataFrame:
    """Load DataFrame from a Streamlit uploaded file object."""
    df = pd.read_csv(file_obj, dtype=str)
    return _clean(df)


def load_all() -> pd.DataFrame:
    return _load_file('注册漏斗-国家渠道-全部-1年.csv')


def load_filtered() -> pd.DataFrame:
    return _load_file('注册漏斗-国家渠道-去羊毛-1年.csv')
