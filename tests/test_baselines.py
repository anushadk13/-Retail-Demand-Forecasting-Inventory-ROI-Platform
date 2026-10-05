import numpy as np

from src.models import baselines


def test_seasonal_naive_repeats_last_week():
    h = np.arange(1, 15, dtype=float)[None, :]  # 1..14
    f = baselines.seasonal_naive(h, 14)
    assert f.shape == (1, 14)
    assert (f[0, :7] == np.arange(8, 15)).all() and (f[0, 7:] == f[0, :7]).all()


def test_moving_average_constant():
    h = np.tile(np.arange(28, dtype=float), (2, 2))
    f = baselines.moving_average(h, 5)
    assert np.allclose(f, 13.5)


def test_ets_nonnegative_and_shaped():
    rng = np.random.default_rng(0)
    h = rng.poisson(3, (3, 120)).astype(float)
    f = baselines.ets_holt_winters(h, 28)
    assert f.shape == (3, 28) and (f >= 0).all()
