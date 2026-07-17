from __future__ import annotations

import pytest

from finance_forecast_agent.native_plugins import (
    DEFAULT_NATIVE_PLUGIN_REGISTRY,
    NativePluginDefinition,
    NativePluginRegistry,
    infer_native_plugin_bindings,
)


def test_default_bindings_choose_artifact_conda_and_patch_plugins() -> None:
    bindings = infer_native_plugin_bindings(
        metric_artifact_glob="results/*/metrics.npy",
        compatibility_patches=[{"path": "run.py"}],
        command=["{conda}", "run", "-n", "paper", "python", "run.py"],
    )
    assert bindings["metric_extractor"] == "numpy_vector_v1"
    assert bindings["execution_backend"] == "conda_subprocess_v1"
    assert bindings["compatibility_recipe"] == "semantic_noop_text_patch_v1"
    assert not DEFAULT_NATIVE_PLUGIN_REGISTRY.validate_bindings(
        bindings,
        experiment_type="forecast_only",
        artifact_type="npy",
    )


def test_registry_supports_task_protocols_and_rejects_missing_bindings() -> None:
    bindings = infer_native_plugin_bindings(
        metric_artifact_glob="",
        compatibility_patches=[],
        command=["python", "run.py"],
    )
    assert not DEFAULT_NATIVE_PLUGIN_REGISTRY.validate_bindings(
        bindings,
        experiment_type="portfolio_rl",
        artifact_type="stdout",
    )

    bindings.pop("acceptance_policy")
    blockers = DEFAULT_NATIVE_PLUGIN_REGISTRY.validate_bindings(
        bindings,
        experiment_type="forecast_only",
        artifact_type="stdout",
    )
    assert "native plugin binding is missing: acceptance_policy" in blockers


def test_registry_rejects_duplicate_and_unknown_plugin_kinds() -> None:
    definition = NativePluginDefinition("example", "source_resolver", "module:name", ("*",))
    registry = NativePluginRegistry([definition])
    with pytest.raises(ValueError, match="Duplicate native plugin id"):
        registry.register(definition)
    with pytest.raises(ValueError, match="Unknown native plugin kind"):
        registry.register(NativePluginDefinition("bad", "unknown", "module:name", ("*",)))
