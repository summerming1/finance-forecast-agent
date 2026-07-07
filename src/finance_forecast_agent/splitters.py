from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class SplitWindow:
    train_indices: list[int]
    test_indices: list[int]
    purge: int = 0
    embargo: int = 0


def reject_random_split_for_finance(split_method: str) -> None:
    if split_method.lower() in {'random','random_kfold','kfold','shuffle_split'}:
        raise ValueError('random split is not allowed for formal finance evaluation')


def rolling_origin_splits(n: int, *, min_train: int = 60, test_size: int = 16, step: int = 100) -> list[SplitWindow]:
    windows = []
    train_end = min_train
    while train_end + test_size <= n:
        windows.append(SplitWindow(list(range(0, train_end)), list(range(train_end, train_end + test_size))))
        train_end += step
    if not windows:
        raise ValueError('not enough rows for rolling origin split')
    return windows


def purged_walk_forward_splits(n: int, *, train_size: int = 60, test_size: int = 16, step: int = 100, purge: int = 1, embargo: int = 1) -> list[SplitWindow]:
    windows = []
    test_start = train_size + purge
    while test_start + test_size <= n:
        train_start = max(0, test_start - purge - train_size)
        train_end = max(train_start, test_start - purge)
        test_end = test_start + test_size
        # embargo is represented in the window and prevents the next test start from overlapping label horizons.
        windows.append(SplitWindow(list(range(train_start, train_end)), list(range(test_start, test_end)), purge=purge, embargo=embargo))
        test_start += step + embargo
    if not windows:
        raise ValueError('not enough rows for purged walk-forward split')
    return windows


def make_splits(method: str, n: int) -> list[SplitWindow]:
    reject_random_split_for_finance(method)
    if method == 'purged_walk_forward':
        return purged_walk_forward_splits(n)
    if method == 'rolling_origin':
        return rolling_origin_splits(n)
    raise ValueError(f'unsupported split method: {method}')
