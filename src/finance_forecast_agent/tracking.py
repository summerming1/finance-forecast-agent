from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

class MLflowTracker:
    def __init__(self, tracking_dir: str | Path):
        self.tracking_dir = Path(tracking_dir)
        self.tracking_dir.mkdir(parents=True, exist_ok=True)
        try:
            import mlflow  # type: ignore
            self.mlflow = mlflow
            self.backend = 'mlflow'
            self.mlflow.set_tracking_uri(self.tracking_dir.as_uri())
        except Exception:
            self.mlflow = None
            self.backend = 'local_json_fallback'

    def log_run(self, run_name: str, *, params: dict[str, Any], metrics: dict[str, float], artifacts: dict[str, Any]) -> dict[str, Any]:
        if self.mlflow is not None:
            with self.mlflow.start_run(run_name=run_name) as run:
                self.mlflow.log_params({k: str(v) for k, v in params.items()})
                self.mlflow.log_metrics({k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))})
                artifact_path = self.tracking_dir / f'{run.info.run_id}_artifacts.json'
                artifact_path.write_text(json.dumps(artifacts, indent=2, ensure_ascii=False), encoding='utf-8')
                self.mlflow.log_artifact(str(artifact_path))
                return {'backend': 'mlflow', 'run_id': run.info.run_id}
        path = self.tracking_dir / f'{run_name}.json'
        path.write_text(json.dumps({'params': params, 'metrics': metrics, 'artifacts': artifacts}, indent=2, ensure_ascii=False), encoding='utf-8')
        return {'backend': self.backend, 'path': str(path)}

class DVCDataTracker:
    def __init__(self, repo_dir: str | Path):
        self.repo_dir = Path(repo_dir)
        self.repo_dir.mkdir(parents=True, exist_ok=True)
        self.dvc_bin = shutil.which('dvc')

    def track(self, data_path: Path) -> dict[str, Any]:
        if self.dvc_bin:
            try:
                subprocess.run([self.dvc_bin, 'init', '--no-scm'], cwd=self.repo_dir, check=False, capture_output=True, text=True)
                subprocess.run([self.dvc_bin, 'add', str(data_path)], cwd=self.repo_dir, check=True, capture_output=True, text=True)
                return {'backend': 'dvc', 'tracked': True, 'path': str(data_path)}
            except Exception as exc:
                return {'backend': 'dvc', 'tracked': False, 'error': str(exc), 'path': str(data_path)}
        meta = self.repo_dir / 'dvc_local_fallback.json'
        meta.write_text(json.dumps({'backend': 'local_fallback', 'tracked_path': str(data_path)}, indent=2), encoding='utf-8')
        return {'backend': 'local_fallback', 'tracked': True, 'path': str(data_path), 'metadata': str(meta)}
