from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .config import load_env_file

load_env_file()

class MLflowTracker:
    def __init__(self, tracking_dir: str | Path, *, experiment_name: str = 'finance-forecast-agent'):
        self.tracking_dir = Path(tracking_dir)
        self.tracking_dir.mkdir(parents=True, exist_ok=True)
        configured_uri = os.getenv('MLFLOW_TRACKING_URI', '').strip()
        database_path = (self.tracking_dir.parent / 'mlflow.db').resolve()
        tracking_uri = configured_uri or f"sqlite:///{database_path.as_posix()}"
        self.tracking_uri = tracking_uri
        self.experiment_name = experiment_name
        try:
            import mlflow  # type: ignore
            self.mlflow = mlflow
            self.backend = 'mlflow'
            self.mlflow.set_tracking_uri(tracking_uri)
            self.mlflow.set_experiment(experiment_name)
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
                    return {
                        'backend': 'mlflow',
                        'run_id': run.info.run_id,
                        'tracking_uri': self.tracking_uri,
                        'experiment_name': self.experiment_name,
                    }
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

    def _command(self, *args: str) -> list[str]:
        if self.dvc_bin:
            return [self.dvc_bin, *args]
        return [sys.executable, '-m', 'dvc', *args]

    def _run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            self._command(*args),
            cwd=self.repo_dir,
            check=check,
            capture_output=True,
            text=True,
        )

    def status(self) -> dict[str, Any]:
        try:
            remote_name = self._run('remote', 'default').stdout.strip()
            remote_url = self._run('config', f'remote.{remote_name}.url').stdout.strip()
            return {
                'backend': 'dvc',
                'configured': bool(remote_name and remote_url),
                'remote': {'name': remote_name, 'url': remote_url},
            }
        except Exception as exc:
            return {'backend': 'dvc', 'configured': False, 'error': str(exc)}

    def configure_remote(self, remote_url: str | Path, *, name: str = 'finance_agent_remote') -> dict[str, Any]:
        url = str(remote_url).strip()
        if not url:
            raise ValueError('DVC remote URL cannot be empty')
        if not (url.startswith(('s3://', 'gs://', 'azure://', 'ssh://', 'http://', 'https://')) or '://' in url):
            url = str(Path(url).resolve())
        self._run('init', '--no-scm', check=False)
        self._run('remote', 'add', '-f', '-d', name, url)
        return self.status()

    def track(self, data_path: Path) -> dict[str, Any]:
        try:
            import dvc  # type: ignore  # noqa: F401
            dvc_available = True
        except Exception:
            dvc_available = bool(self.dvc_bin)
        if dvc_available:
            try:
                data_path = Path(data_path).resolve()
                repo_root = self.repo_dir.resolve()
                try:
                    relative_path = data_path.relative_to(repo_root)
                except ValueError as exc:
                    raise ValueError(f'DVC data must be inside {repo_root}: {data_path}') from exc
                self._run('init', '--no-scm', check=False)
                if self.remote_url:
                    remote_url = self.remote_url
                    if not (remote_url.startswith(('s3://', 'gs://', 'azure://', 'ssh://', 'http://', 'https://')) or '://' in remote_url):
                        remote_url = str(Path(remote_url).resolve())
                    self._run('remote', 'add', '-f', '-d', 'finance_agent_remote', remote_url)
                remote_status = self.status()
                if not remote_status.get('configured'):
                    raise RuntimeError('DVC default remote is not configured')
                self._run('add', relative_path.as_posix())
                self._run('push', relative_path.as_posix() + '.dvc')
                pointer = Path(str(data_path) + '.dvc')
                return {
                    'backend': 'dvc',
                    'tracked': True,
                    'pushed': True,
                    'path': str(data_path),
                    'pointer_path': str(pointer),
                    'remote': remote_status['remote'],
                }
            except Exception as exc:
                return {'backend': 'dvc', 'tracked': False, 'error': str(exc), 'path': str(data_path)}
        meta = self.repo_dir / 'dvc_local_fallback.json'
        meta.write_text(json.dumps({'backend': 'local_fallback', 'tracked_path': str(data_path)}, indent=2), encoding='utf-8')
        return {'backend': 'local_fallback', 'tracked': True, 'path': str(data_path), 'metadata': str(meta)}
