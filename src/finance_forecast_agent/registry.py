from __future__ import annotations

import json
from pathlib import Path
from typing import Any

class PaperDatasetRegistry:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text('{}', encoding='utf-8')

    def register(self, paper_id: str, info: dict[str, Any]) -> None:
        data = self.load_all()
        data[paper_id] = info
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

    def load_all(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding='utf-8'))

    def get(self, paper_id: str) -> dict[str, Any] | None:
        return self.load_all().get(paper_id)
