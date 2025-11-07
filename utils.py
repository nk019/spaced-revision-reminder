from datetime import datetime, timedelta
from typing import List, Tuple
def parse_offsets_csv(csv_str: str) -> List[int]:
    if not csv_str.strip():
        return []
    parts = [p.strip() for p in csv_str.split(",")]
    vals = []
    for p in parts:
        if not p:
            continue
        try:
            n = int(p)
            if n >= 0:
                vals.append(n)
        except ValueError:
            continue
    return sorted(set(vals))
def build_series_datetimes(base_dt: datetime, day_offsets: List[int]) -> List[datetime]:
    return [base_dt + timedelta(days=d) for d in day_offsets]
def human_readable_status(rem) -> str:
    emoji = {"pending":"🕒", "done":"✅", "skipped":"⏭️"}.get(rem.status, "🕒")
    return f"{emoji} {rem.status}"
def split_series_change(original: List[int], new: List[int]) -> Tuple[List[int], List[int], List[int]]:
    oset = set(original); nset = set(new)
    return (sorted(nset - oset), sorted(oset - nset), sorted(oset & nset))
