import pandas as pd

from src.evaluation.roi import G, scenario_savings, scenario_summary


def _inp():
    return pd.DataFrame({"category": ["A", "B"], "sigma_sum_baseline": [100.0, 50.0],
                         "sigma_sum_model": [90.0, 50.0], "avg_price": [4.0, 10.0],
                         "annual_units": [1e5, 2e4]})


def test_loss_function_known_value():
    assert abs(G(0.0) - 0.39894) < 1e-4


def test_no_improvement_means_no_savings():
    s = scenario_savings(_inp(), 1.0, improvement=0.0)
    assert abs(s.total.sum()) < 1e-9


def test_savings_monotonic_in_improvement():
    lo = scenario_savings(_inp(), 1.0, improvement=0.05).total.sum()
    hi = scenario_savings(_inp(), 1.0, improvement=0.20).total.sum()
    assert hi > lo > 0


def test_scenarios_ordered():
    s = scenario_summary(_inp()).set_index("scenario").annual_savings
    assert s["Conservative"] < s["Expected"] < s["Optimistic"]
