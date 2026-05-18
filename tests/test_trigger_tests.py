from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

trigger_tests = import_module("20_test_entry_triggers")


def test_entry_vs_control_detects_directional_separation() -> None:
    entries = [
        {"wallet_buy_count_30s": "5", "label_win": "true", "sample_class": "winner"},
        {"wallet_buy_count_30s": "6", "label_win": "true", "sample_class": "winner"},
        {"wallet_buy_count_30s": "7", "label_win": "false", "sample_class": "loser"},
        {"wallet_buy_count_30s": "8", "label_win": "false", "sample_class": "loser"},
    ]
    controls = [
        {"wallet_buy_count_30s": "0"},
        {"wallet_buy_count_30s": "1"},
        {"wallet_buy_count_30s": "1"},
        {"wallet_buy_count_30s": "2"},
    ]
    features = [{"feature_id": "wallet_buy_count_30s", "family": "wallet_flow", "source": "wallet_swaps", "direction": "higher"}]

    rows = trigger_tests.build_trigger_tests(entries, controls, features, bootstrap_iters=50, top_k=2)

    entry_vs_control = next(row for row in rows if row["test_scope"] == "entry_vs_control")
    assert entry_vs_control["verdict"] in {"PASS", "PARTIAL"}
    assert float(entry_vs_control["auc"]) > 0.8
    assert float(entry_vs_control["cliffs_delta"]) > 0


def test_lower_direction_is_normalized_for_sell_pressure() -> None:
    entries = [{"wallet_sell_count_30s": "0"}, {"wallet_sell_count_30s": "1"}]
    controls = [{"wallet_sell_count_30s": "5"}, {"wallet_sell_count_30s": "6"}]
    feature = {"feature_id": "wallet_sell_count_30s", "family": "wallet_flow", "source": "wallet_swaps", "direction": "lower"}

    row = trigger_tests.build_test_row(1, "entry_vs_control", feature, entries, controls, "entry", "control", 50, 2)

    assert float(row["cliffs_delta"]) > 0
    assert float(row["auc"]) > 0.8


def test_missing_feature_coverage_yields_unknown() -> None:
    entries = [{"price_return_30s": ""}, {"price_return_30s": "UNKNOWN"}]
    controls = [{"price_return_30s": ""}, {"price_return_30s": "UNKNOWN"}]
    feature = {"feature_id": "price_return_30s", "family": "price_action", "source": "price_series", "direction": "higher"}

    row = trigger_tests.build_test_row(1, "entry_vs_control", feature, entries, controls, "entry", "control", 20, 2)

    assert row["coverage_pct"] == "0.00"
    assert row["verdict"] == "UNKNOWN"


def test_manifest_loader_reads_minimal_yaml(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
features:
  - feature_id: wallet_buy_count_30s
    family: wallet_flow
    source: wallet_swaps
    direction: higher
""",
        encoding="utf-8",
    )

    features = trigger_tests.load_manifest(manifest)

    assert features == [
        {
            "feature_id": "wallet_buy_count_30s",
            "family": "wallet_flow",
            "source": "wallet_swaps",
            "direction": "higher",
        }
    ]
