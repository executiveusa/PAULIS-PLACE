"""Tests for the six revenue channels (04)."""
import sys
from pathlib import Path
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))


def test_channels_registry_has_six():
    from channels import _CHANNEL_CONFIG, CHANNEL_DISPATCHERS
    assert set(_CHANNEL_CONFIG.keys()) == {"CH1","CH2","CH3","CH4","CH5","CH6"}
    assert set(CHANNEL_DISPATCHERS.keys()) == {"CH1","CH2","CH3","CH4","CH5","CH6"}


def test_channels_respect_L2_services_cap():
    from channels import _CHANNEL_CONFIG
    for chid, cfg in _CHANNEL_CONFIG.items():
        assert len(cfg["services"]) <= 3, (
            f"L2 violated — {chid} touches {len(cfg['services'])} services"
        )


def test_channels_respect_L3_per_channel_cap():
    from channels import _CHANNEL_CONFIG
    import os
    cap_env = float(os.environ.get("YAPPY_PER_CHANNEL_CAP_USD","0.50"))
    for chid, cfg in _CHANNEL_CONFIG.items():
        assert cfg["cap"] <= cap_env + 0.01, (
            f"L3 — {chid} cap {cfg['cap']} exceeds env cap {cap_env}"
        )


def test_channels_dispatchers_are_callable():
    from channels import CHANNEL_DISPATCHERS, ch1_tick, ch2_tick, ch3_tick, ch4_tick, ch5_tick, ch6_tick
    assert callable(ch1_tick) and callable(ch2_tick) and callable(ch3_tick)
    assert callable(ch4_tick) and callable(ch5_tick) and callable(ch6_tick)


def test_channel_tick_id_format():
    from channels import _tick_id
    tid = _tick_id("CH1")
    assert tid.startswith("tik_CH1_")