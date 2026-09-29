from __future__ import annotations

import csv
from pathlib import Path


def write_csv(rows, path: Path) -> int:
    count = 0
    with Path(path).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        for row in rows:
            writer.writerow(row)
            count += 1
    return max(0, count - 1)  # Header is not a posting.
