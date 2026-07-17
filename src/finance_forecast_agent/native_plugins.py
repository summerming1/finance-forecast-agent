from __future__ import annotations

from dataclasses import dataclass
from typing import Any


PLUGIN_KINDS = {
    "source_resolver",
    "dataset_materializer",
    "execution_backend",
    "metric_extractor",
    "compatibility_recipe",
    "acceptance_policy",
}


@dataclass(frozen=True)
class NativePluginDefinition:
    plugin_id: str
    kind: str
    implementation: str
    supported_experiment_types: tuple[str, ...]
    supported_artifact_types: tuple[str, ...] = ()
    notes: str = ""

    def supports(self, *, experiment_type: str, artifact_type: str | None = None) -> bool:
        experiment_ok = "*" in self.supported_experiment_types or (
            experiment_type in self.supported_experiment_types
        )
        artifact_ok = (
            artifact_type is None
            or not self.supported_artifact_types
            or artifact_type in self.supported_artifact_types
        )
        return experiment_ok and artifact_ok


class NativePluginRegistry:
    def __init__(self, definitions: list[NativePluginDefinition] | None = None):
        self._definitions: dict[str, NativePluginDefinition] = {}
        for definition in definitions or []:
            self.register(definition)

    def register(self, definition: NativePluginDefinition) -> None:
        if definition.kind not in PLUGIN_KINDS:
            raise ValueError(f"Unknown native plugin kind: {definition.kind}")
        if definition.plugin_id in self._definitions:
            raise ValueError(f"Duplicate native plugin id: {definition.plugin_id}")
        self._definitions[definition.plugin_id] = definition

    def get(self, plugin_id: str) -> NativePluginDefinition:
        try:
            return self._definitions[plugin_id]
        except KeyError as exc:
            raise ValueError(f"Native plugin is not registered: {plugin_id}") from exc

    def validate_bindings(
        self,
        bindings: dict[str, str],
        *,
        experiment_type: str,
        artifact_type: str | None = None,
    ) -> list[str]:
        blockers = []
        for kind in sorted(PLUGIN_KINDS):
            plugin_id = bindings.get(kind)
            if not plugin_id:
                blockers.append(f"native plugin binding is missing: {kind}")
                continue
            try:
                definition = self.get(plugin_id)
            except ValueError as exc:
                blockers.append(str(exc))
                continue
            if definition.kind != kind:
                blockers.append(
                    f"native plugin {plugin_id} has kind {definition.kind}, expected {kind}"
                )
            elif not definition.supports(
                experiment_type=experiment_type,
                artifact_type=artifact_type if kind == "metric_extractor" else None,
            ):
                blockers.append(
                    f"native plugin {plugin_id} does not support {experiment_type}"
                )
        return blockers

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "native_plugin_registry_v1",
            "plugins": [
                definition.__dict__ for _, definition in sorted(self._definitions.items())
            ],
        }


DEFAULT_NATIVE_PLUGIN_REGISTRY = NativePluginRegistry(
    [
        NativePluginDefinition(
            "pinned_archive_v1",
            "source_resolver",
            "finance_forecast_agent.native_execution:audit_native_claim",
            ("*",),
        ),
        NativePluginDefinition(
            "frozen_file_v1",
            "dataset_materializer",
            "finance_forecast_agent.native_execution:audit_native_claim",
            ("*",),
        ),
        NativePluginDefinition(
            "local_subprocess_v1",
            "execution_backend",
            "finance_forecast_agent.native_execution:OfficialRepoCommandAdapter",
            ("*",),
        ),
        NativePluginDefinition(
            "conda_subprocess_v1",
            "execution_backend",
            "finance_forecast_agent.native_execution:OfficialRepoCommandAdapter",
            ("*",),
        ),
        NativePluginDefinition(
            "regex_log_v1",
            "metric_extractor",
            "finance_forecast_agent.native_execution:_parse_metric_values",
            ("*",),
            ("stdout", "stderr"),
        ),
        NativePluginDefinition(
            "numpy_vector_v1",
            "metric_extractor",
            "finance_forecast_agent.native_execution:_artifact_metric_values",
            ("*",),
            ("npy",),
        ),
        NativePluginDefinition(
            "semantic_noop_text_patch_v1",
            "compatibility_recipe",
            "finance_forecast_agent.native_execution:_prepare_runtime_source",
            ("*",),
        ),
        NativePluginDefinition(
            "no_compatibility_patch_v1",
            "compatibility_recipe",
            "finance_forecast_agent.native_execution:_prepare_runtime_source",
            ("*",),
        ),
        NativePluginDefinition(
            "paper_metric_tolerance_v1",
            "acceptance_policy",
            "finance_forecast_agent.native_execution:_metric_gate",
            ("*",),
        ),
    ]
)


def infer_native_plugin_bindings(
    *,
    metric_artifact_glob: str,
    compatibility_patches: list[dict[str, str]],
    command: list[str],
) -> dict[str, str]:
    return {
        "source_resolver": "pinned_archive_v1",
        "dataset_materializer": "frozen_file_v1",
        "execution_backend": (
            "conda_subprocess_v1" if any("{conda}" in part for part in command) else "local_subprocess_v1"
        ),
        "metric_extractor": "numpy_vector_v1" if metric_artifact_glob else "regex_log_v1",
        "compatibility_recipe": (
            "semantic_noop_text_patch_v1"
            if compatibility_patches
            else "no_compatibility_patch_v1"
        ),
        "acceptance_policy": "paper_metric_tolerance_v1",
    }
