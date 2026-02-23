from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class DatasetExample(BaseModel):
    answer: str
    sources: list[str]
    label: Literal["supported", "hallucinated"]


def load_examples(path: Path) -> list[DatasetExample]:
    examples: list[DatasetExample] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            examples.append(DatasetExample.model_validate_json(line))
    return examples
