from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .config import load_env_file

load_env_file()

class MLflowTracker:
    def __init__(self, tracking_dir: str | Path):
        self.tracking_dir = Path(tracking_dir)
        self.tracking_dir.mkdir(parents=True, exist_ok=True)
        tracking_uri = os.getenv('MLFLOW_TRACKING_URI')
        try:
            import mlflow  # type: ignore
            self.mlflow = mlflow
            self.backend = 'mlflow'
            self.mlflow.set_tracking_uri(tracking_uri or self.tracking_dir.as_uri())
        except Exception:
            self.mlflow = None
            self.backend = 'local_json_fallback'

    def log_run(self, run_name: str, *, params: dict[str, Any], metrics: dict[str, float], artifacts: dict[str, Any]) -> dict[str, Any]:
        if self.mlflow is not None:
            try:
                with self.mlflow.start_run(run_name=run_name) as run:
                    self.mlflow.log_params({k: str(v) for k, v in params.items()})
                    self.mlflow.log_metrics({k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))})
                    artifact_path = self.tracking_dir / f'{run.info.run_id}_artifacts.json'
                    artifact_path.write_text(json.dumps(artifacts, indent=2, ensure_ascii=False), encoding='utf-8')
                    self.mlflow.log_artifact(str(artifact_path))
                    return {'backend': 'mlflow', 'run_id': run.info.run_id}
            except Exception as exc:
                self.backend = 'local_json_fallback'
                fallback_error = str(exc)
        path = self.tracking_dir / f'{run_name}.json'
        payload = {'params': params, 'metrics': metrics, 'artifacts': artifacts}
        if 'fallback_error' in locals():
            payload['fallback_error'] = fallback_error
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
        return {'backend': self.backend, 'path': str(path)}

class DVCDataTracker:
    def __init__(self, repo_dir: str | Path):
        self.repo_dir = Path(repo_dir)
        self.repo_dir.mkdir(parents=True, exist_ok=True)
        self.dvc_bin = shutil.which('dvc')
        self.remote_url = os.getenv('DVC_REMOTE_URL', '').strip()

    def track(self, data_path: Path) -> dict[str, Any]:
        if self.dvc_bin:
            try:
                data_path = Path(data_path).resolve()
                subprocess.run([self.dvc_bin, 'init', '--no-scm'], cwd=self.repo_dir, check=False, capture_output=True, text=True)
                remote = None
                if self.remote_url:
                    remote_url = self.remote_url
                    if not (remote_url.startswith(('s3://', 'gs://', 'azure://', 'ssh://', 'http://', 'https://')) or '://' in remote_url):
                        remote_url = str(Path(remote_url).resolve())
                    subprocess.run([self.dvc_bin, 'remote', 'add', '-f', '-d', 'finance_agent_remote', remote_url], cwd=self.repo_dir, check=True, capture_output=True, text=True)
                    remote = {'name': 'finance_agent_remote', 'url': remote_url}
                subprocess.run([self.dvc_bin, 'add', str(data_path)], cwd=self.repo_dir, check=True, capture_output=True, text=True)
                return {'backend': 'dvc', 'tracked': True, 'path': str(data_path), 'remote': remote}
            except Exception as exc:
                return {'backend': 'dvc', 'tracked': False, 'error': str(exc), 'path': str(data_path)}
        meta = self.repo_dir / 'dvc_local_fallback.json'
        meta.write_text(json.dumps({'backend': 'local_fallback', 'tracked_path': str(data_path)}, indent=2), encoding='utf-8')
        return {'backend': 'local_fallback', 'tracked': True, 'path': str(data_path), 'metadata': str(meta)}
