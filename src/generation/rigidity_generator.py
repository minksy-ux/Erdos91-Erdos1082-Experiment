"""Rigidity-inspired graph generation and geometric realization."""

from __future__ import annotations

import random
from typing import Optional

import networkx as nx
import numpy as np


class RigidityGenerator:
    """Generate minimally rigid-like graphs and realize them in 2D."""

    def __init__(self, seed: int = 42) -> None:
        self._rand = random.Random(seed)

    def generate_laman_like(self, n: int) -> Optional[nx.Graph]:
        """Construct a sparse graph with target 2n-3 edges via Henneberg-I style growth."""
        if n < 3:
            return None

        g = nx.complete_graph(3)
        for v in range(3, n):
            nodes = list(g.nodes())
            u, w = self._rand.sample(nodes, 2)
            g.add_node(v)
            g.add_edge(v, u)
            g.add_edge(v, w)

            if self._rand.random() < 0.2:
                z = self._rand.choice(nodes)
                if not g.has_edge(v, z):
                    g.add_edge(v, z)

        while g.number_of_edges() > 2 * n - 3:
            edge = self._rand.choice(list(g.edges()))
            g.remove_edge(*edge)

        if g.number_of_edges() != 2 * n - 3:
            return None
        return g

    def realize(self, graph: nx.Graph, seed: int = 42, iterations: int = 300) -> np.ndarray:
        """Realize graph coordinates with spring layout as optimization seed."""
        pos = nx.spring_layout(graph, seed=seed, iterations=iterations, dim=2)
        points = np.array([pos[i] for i in sorted(graph.nodes())], dtype=float)
        points -= points.mean(axis=0)
        return points
