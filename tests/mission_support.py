"""Explicitly synthetic fixtures: no downloaded market data or user acceptance."""
import numpy as np
import pandas as pd

from finance_forecast_agent.focused_data import FocusedDatasetSnapshot


def simulated_frame(n=1050, seed=72):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range('2017-01-03', periods=n + 1).strftime('%Y-%m-%d')
    values = rng.normal(0, 0.01, n + 25)
    price = 100 * np.exp(np.cumsum(values))
    frame = pd.DataFrame({'timestamp': dates[:-1], 'decision_time': dates[:-1],
                          'label_start_time': dates[:-1], 'label_end_time': dates[1:],
                          'label': price[25:] / price[24:-1] - 1,
                          'spy_adj_close': price[24:-1]})
    for lag in range(1, 21):
        frame[f'return_lag_{lag}'] = values[24-lag:24-lag+n]
    for window in [5, 20]:
        frame[f'momentum_{window}'] = (price[24:-1] / price[24-window:-1-window] - 1)
        frame[f'volatility_{window}'] = pd.Series(values).rolling(window).std().iloc[24:-1].values
    frame['volume_change_1'] = rng.normal(0, .1, n)
    snapshot = FocusedDatasetSnapshot(f'simulation-{seed}', f'fixture-{seed}', f'fixture-{seed}',
                                     len(frame), dates[0], dates[-2], 'explicit synthetic fixture',
                                     '', 'generated_for_testing', 'simulation_only',
                                     session_validation='simulation_business_days_not_market_calendar')
    return frame, snapshot
