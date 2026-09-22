"""Canonical identities shared by evidence, cache, model and data contracts.

These hashes detect changes, not authenticity. Trust comes from the independently
controlled registry/ledger. Target keys deliberately exclude observed label values:
a later revision cannot turn an already-exposed target into an unseen one.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def canonical_json(value: Any) -> str:
    def encode(obj):
        if isinstance(obj, np.generic):
            return obj.item()
        if isinstance(obj, (datetime, date, pd.Timestamp)):
            return obj.isoformat()
        if isinstance(obj, Path):
            return str(obj)
        raise TypeError(f'Unsupported identity value: {type(obj).__name__}')
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False, default=encode)


def identity(value: Any, *, domain: str) -> str:
    return hashlib.sha256((domain + '\n' + canonical_json(value)).encode('utf-8')).hexdigest()


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _cell(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float, np.number)):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError('Non-finite value cannot have a research identity')
        # Exact float64 representation, not rounding for approximate equality.
        return ['float64', (0.0 if number == 0 else number).hex()]
    if isinstance(value, (date, datetime, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, str):
        return value
    raise TypeError(f'Unsupported frame cell: {type(value).__name__}')


def frame_fingerprint(frame: pd.DataFrame, columns: list[str] | None = None) -> str:
    if frame.columns.duplicated().any():
        raise ValueError('Duplicate column names in research data')
    cols = sorted(columns if columns is not None else list(frame.columns))
    if not all(isinstance(column, str) for column in cols):
        raise ValueError('Research column names must be strings')
    return identity({'columns': cols, 'rows': [[_cell(v) for v in row] for row in frame[cols].itertuples(index=False, name=None)]},
                    domain='focused-frame-v1')


def target_row_ids(frame: pd.DataFrame, task: dict[str, Any]) -> list[str]:
    definition = {key: task.get(key) for key in ('entity_id', 'frequency', 'horizon', 'label_definition')}
    if not {'timestamp', 'label_end_time'} <= set(frame.columns):
        raise ValueError('Target identity requires session and label end time')
    def session_key(value):
        if task.get('frequency') != 'daily':
            return str(value)
        # These fields identify sessions, not instants. Actual provider receipt
        # / decision instants belong in separate timezone-aware columns.
        stamp = pd.Timestamp(value)
        if pd.isna(stamp) or stamp.tzinfo is not None or stamp != stamp.normalize():
            raise ValueError('Daily target identity requires unambiguous session dates')
        return stamp.date().isoformat()

    return [identity({'target': definition, 'session': session_key(row.timestamp), 'end': session_key(row.label_end_time)},
                     domain='focused-target-key-v1')
            for row in frame[['timestamp', 'label_end_time']].itertuples(index=False)]



def data_identity(frame: pd.DataFrame, task: dict[str, Any]) -> dict[str, str]:
    keys = target_row_ids(frame, task)
    if len(set(keys)) != len(keys):
        raise ValueError('Duplicate target identities')
    target_cols = [c for c in ('timestamp', 'label_end_time', 'label') if c in frame]
    obs_cols = [c for c in ('timestamp', 'spy_adj_close', 'spy_volume') if c in frame]
    return {
        'identity_version': 'focused_data_identity_v1',
        'frame_fingerprint': frame_fingerprint(frame),
        'target_fingerprint': identity(sorted(keys), domain='focused-target-set-v1'),
        'target_content_fingerprint': frame_fingerprint(frame, target_cols),
        'observation_fingerprint': frame_fingerprint(frame, obs_cols),
    }
