"""SQLite persistence for experiment tracking."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np


class ExperimentDB:
    def __init__(self, db_path: str = "results/erdos_experiments.db") -> None:
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS experiments (
                    id INTEGER PRIMARY KEY,
                    n INTEGER NOT NULL,
                    dim INTEGER NOT NULL,
                    trial_id INTEGER NOT NULL,
                    seed INTEGER,
                    seed_family TEXT,
                    method TEXT,
                    num_distinct INTEGER,
                    max_distinct_from_point INTEGER,
                    no_three_collinear INTEGER,
                    energy REAL,
                    points_json TEXT,
                    run_tag TEXT,
                    exact_distinct_sq INTEGER,
                    exact_min_distinct_from_point INTEGER,
                    exact_max_distinct_from_point INTEGER,
                    exact_is_valid INTEGER,
                    cert_name TEXT,
                    timestamp TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS benchmark_summaries (
                    id INTEGER PRIMARY KEY,
                    run_tag TEXT,
                    n INTEGER NOT NULL,
                    trials INTEGER NOT NULL,
                    benchmark_runs INTEGER NOT NULL,
                    mean_best_exact REAL,
                    std_best_exact REAL,
                    min_best_exact REAL,
                    max_best_exact REAL,
                    ci95_low REAL,
                    ci95_high REAL,
                    timestamp TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS family_evidence (
                    id INTEGER PRIMARY KEY,
                    run_tag TEXT,
                    n INTEGER NOT NULL,
                    exact_distinct_sq INTEGER,
                    family_tol REAL,
                    num_candidates INTEGER,
                    num_families INTEGER,
                    num_signature_families INTEGER,
                    signatures_json TEXT,
                    pairwise_json TEXT,
                    timestamp TEXT
                )
                """
            )
            self._ensure_experiment_columns(conn)
            self._ensure_family_columns(conn)

    @staticmethod
    def _ensure_experiment_columns(conn: sqlite3.Connection) -> None:
        expected = {
            "run_tag": "TEXT",
            "exact_distinct_sq": "INTEGER",
            "exact_min_distinct_from_point": "INTEGER",
            "exact_max_distinct_from_point": "INTEGER",
            "exact_is_valid": "INTEGER",
            "cert_name": "TEXT",
        }
        existing = {
            row[1]
            for row in conn.execute("PRAGMA table_info(experiments)").fetchall()
        }
        for col, col_type in expected.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE experiments ADD COLUMN {col} {col_type}")

    @staticmethod
    def _ensure_family_columns(conn: sqlite3.Connection) -> None:
        expected = {
            "num_signature_families": "INTEGER",
        }
        existing = {
            row[1]
            for row in conn.execute("PRAGMA table_info(family_evidence)").fetchall()
        }
        for col, col_type in expected.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE family_evidence ADD COLUMN {col} {col_type}")

    def save(
        self,
        *,
        n: int,
        dim: int,
        trial_id: int,
        seed: int,
        seed_family: str,
        method: str,
        num_distinct: int,
        max_distinct_from_point: int,
        no_three_collinear: bool,
        energy: float,
        points: np.ndarray,
        run_tag: str,
    ) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO experiments
                (n, dim, trial_id, seed, seed_family, method, num_distinct,
                 max_distinct_from_point, no_three_collinear, energy, points_json, run_tag, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    n,
                    dim,
                    trial_id,
                    seed,
                    seed_family,
                    method,
                    num_distinct,
                    max_distinct_from_point,
                    int(no_three_collinear),
                    energy,
                    json.dumps(points.tolist()),
                    run_tag,
                    datetime.now().isoformat(),
                ),
            )
            return int(cursor.lastrowid)

    def update_exact_result(
        self,
        *,
        row_id: int,
        exact_distinct_sq: int,
        exact_min_distinct_from_point: int,
        exact_max_distinct_from_point: int,
        exact_is_valid: bool,
        cert_name: str,
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE experiments
                SET exact_distinct_sq = ?,
                    exact_min_distinct_from_point = ?,
                    exact_max_distinct_from_point = ?,
                    exact_is_valid = ?,
                    cert_name = ?
                WHERE id = ?
                """,
                (
                    exact_distinct_sq,
                    exact_min_distinct_from_point,
                    exact_max_distinct_from_point,
                    int(exact_is_valid),
                    cert_name,
                    row_id,
                ),
            )

    def save_benchmark_summary(
        self,
        *,
        run_tag: str,
        n: int,
        trials: int,
        benchmark_runs: int,
        mean_best_exact: float,
        std_best_exact: float,
        min_best_exact: float,
        max_best_exact: float,
        ci95_low: float,
        ci95_high: float,
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO benchmark_summaries
                (run_tag, n, trials, benchmark_runs, mean_best_exact, std_best_exact,
                 min_best_exact, max_best_exact, ci95_low, ci95_high, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_tag,
                    n,
                    trials,
                    benchmark_runs,
                    mean_best_exact,
                    std_best_exact,
                    min_best_exact,
                    max_best_exact,
                    ci95_low,
                    ci95_high,
                    datetime.now().isoformat(),
                ),
            )

    def save_family_evidence(
        self,
        *,
        run_tag: str,
        n: int,
        exact_distinct_sq: int,
        family_tol: float,
        num_candidates: int,
        num_families: int,
        num_signature_families: int,
        signatures: List[str],
        pairwise: List[Dict[str, Any]],
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO family_evidence
                (run_tag, n, exact_distinct_sq, family_tol, num_candidates, num_families, num_signature_families,
                 signatures_json, pairwise_json, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_tag,
                    n,
                    exact_distinct_sq,
                    family_tol,
                    num_candidates,
                    num_families,
                    num_signature_families,
                    json.dumps(signatures),
                    json.dumps(pairwise),
                    datetime.now().isoformat(),
                ),
            )

    def get_best(self, n: Optional[int] = None, limit: int = 10) -> List[Dict[str, Any]]:
        query = (
            "SELECT id, n, dim, trial_id, seed_family, method, num_distinct, "
            "max_distinct_from_point, no_three_collinear, energy, exact_distinct_sq, "
            "exact_min_distinct_from_point, exact_max_distinct_from_point, exact_is_valid, run_tag, timestamp "
            "FROM experiments"
        )
        params: List[Any] = []
        if n is not None:
            query += " WHERE n = ?"
            params.append(n)
        query += " ORDER BY num_distinct ASC, energy ASC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_best_points(self, n: Optional[int] = None, limit: int = 10) -> List[np.ndarray]:
        query = (
            "SELECT points_json FROM experiments "
            "WHERE exact_distinct_sq IS NOT NULL AND exact_is_valid = 1"
        )
        params: List[Any] = []
        if n is not None:
            query += " AND n = ?"
            params.append(n)
        query += " ORDER BY exact_distinct_sq ASC, exact_min_distinct_from_point DESC, energy ASC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
            return [np.array(json.loads(row[0]), dtype=float) for row in rows if row[0]]

    def get_benchmark_summaries(self, n: Optional[int] = None, limit: int = 30) -> List[Dict[str, Any]]:
        query = (
            "SELECT id, run_tag, n, trials, benchmark_runs, mean_best_exact, std_best_exact, "
            "min_best_exact, max_best_exact, ci95_low, ci95_high, timestamp "
            "FROM benchmark_summaries"
        )
        params: List[Any] = []
        if n is not None:
            query += " WHERE n = ?"
            params.append(n)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_latest_family_evidence(self, n: Optional[int] = None, limit: int = 20) -> List[Dict[str, Any]]:
        query = (
            "SELECT id, run_tag, n, exact_distinct_sq, family_tol, num_candidates, num_families, num_signature_families, "
            "signatures_json, pairwise_json, timestamp FROM family_evidence"
        )
        params: List[Any] = []
        if n is not None:
            query += " WHERE n = ?"
            params.append(n)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
