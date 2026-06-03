"""Exact symbolic checks for distinct distances and no-three-collinear constraints."""

from __future__ import annotations

import json
from datetime import datetime
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import sympy as sp
from mpmath import mp


class ExactVerifier:
    def __init__(self, dps: int = 100) -> None:
        mp.dps = dps

    @staticmethod
    def _to_rational_points(points: np.ndarray) -> List[Tuple[sp.Rational, sp.Rational]]:
        return [(sp.Rational(str(float(x))), sp.Rational(str(float(y)))) for x, y in points]

    def certify(
        self,
        points: np.ndarray,
        name: Optional[str] = None,
        save: bool = True,
        output_dir: str = "certified_configs",
    ) -> Dict[str, object]:
        if points.ndim != 2 or points.shape[1] != 2:
            raise ValueError("ExactVerifier currently supports 2D points only")
        if name is None:
            name = f"config_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        n = points.shape[0]
        points_exact = self._to_rational_points(points)

        multiplicities: Dict[str, int] = {}
        for i, j in combinations(range(n), 2):
            dx = points_exact[i][0] - points_exact[j][0]
            dy = points_exact[i][1] - points_exact[j][1]
            sq = sp.simplify(dx * dx + dy * dy)
            key = str(sq)
            multiplicities[key] = multiplicities.get(key, 0) + 1

        per_point_counts: List[int] = []
        for i in range(n):
            per_point = set()
            for j in range(n):
                if i == j:
                    continue
                dx = points_exact[i][0] - points_exact[j][0]
                dy = points_exact[i][1] - points_exact[j][1]
                sq = sp.simplify(dx * dx + dy * dy)
                per_point.add(str(sq))
            per_point_counts.append(len(per_point))

        collinear_triples: List[Tuple[int, int, int]] = []
        for i, j, k in combinations(range(n), 3):
            area2 = sp.simplify(
                (points_exact[j][0] - points_exact[i][0]) * (points_exact[k][1] - points_exact[i][1])
                - (points_exact[j][1] - points_exact[i][1]) * (points_exact[k][0] - points_exact[i][0])
            )
            if area2 == 0:
                collinear_triples.append((i, j, k))

        result: Dict[str, object] = {
            "name": name,
            "n": n,
            "num_distinct_squared_distances": len(multiplicities),
            "min_distinct_from_point": min(per_point_counts) if per_point_counts else 0,
            "max_distinct_from_point": max(per_point_counts) if per_point_counts else 0,
            "per_point_distinct_counts": per_point_counts,
            "distance_multiplicities": dict(sorted(multiplicities.items(), key=lambda item: -item[1])),
            "collinear_triples": len(collinear_triples),
            "is_valid": len(collinear_triples) == 0,
            "dps": mp.dps,
            "timestamp": datetime.now().isoformat(),
        }

        if save:
            out_dir = Path(output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            path = out_dir / f"{name}.json"
            with path.open("w", encoding="utf-8") as handle:
                json.dump(result, handle, indent=2)

        return result
