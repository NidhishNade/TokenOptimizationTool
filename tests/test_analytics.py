"""Tests for the in-app usage analytics accumulator."""

from optimizer.analytics import UsageStats


def test_starts_empty():
    stats = UsageStats()
    assert stats.runs == 0
    assert stats.total_tokens_saved == 0
    assert stats.average_percent_saved == 0.0
    assert stats.best_percent_saved == 0.0
    assert stats.history == []


def test_records_a_single_run():
    stats = UsageStats()
    percent = stats.record(original_tokens=100, final_tokens=60, cost_saved_usd=0.01)

    assert stats.runs == 1
    assert stats.total_original_tokens == 100
    assert stats.total_final_tokens == 60
    assert stats.total_tokens_saved == 40
    assert percent == 40.0
    assert stats.best_percent_saved == 40.0
    assert stats.total_cost_saved_usd == 0.01
    assert stats.history == [40.0]


def test_average_is_volume_weighted():
    stats = UsageStats()
    stats.record(100, 50)   # 50% on 100 tokens
    stats.record(10, 9)     # 10% on 10 tokens
    # Weighted: 51 saved / 110 original ≈ 46.4%, NOT the (50+10)/2 = 30% mean.
    assert round(stats.average_percent_saved, 1) == 46.4


def test_best_percent_tracks_the_max():
    stats = UsageStats()
    stats.record(100, 90)   # 10%
    stats.record(100, 20)   # 80%
    stats.record(100, 70)   # 30%
    assert stats.best_percent_saved == 80.0


def test_negative_savings_are_clamped():
    # An optimizer should never report growth as savings.
    stats = UsageStats()
    percent = stats.record(original_tokens=50, final_tokens=80)
    assert percent == 0.0
    assert stats.total_tokens_saved == 0
    assert stats.total_final_tokens == 50  # clamped down to original


def test_zero_original_tokens_is_safe():
    stats = UsageStats()
    percent = stats.record(original_tokens=0, final_tokens=0)
    assert percent == 0.0
    assert stats.runs == 1
    assert stats.average_percent_saved == 0.0


def test_reset_clears_everything():
    stats = UsageStats()
    stats.record(100, 40, cost_saved_usd=0.5)
    stats.reset()
    assert stats.runs == 0
    assert stats.total_tokens_saved == 0
    assert stats.total_cost_saved_usd == 0.0
    assert stats.history == []
