#!/usr/bin/env python3
"""Graph and rigidity utilities for Erdős distance exploration."""

from __future__ import annotations

import itertools
import math
from typing import Dict, Iterable, List, Tuple

import numpy as np
import networkx as nx

Graph = nx.Graph


def lamans_count(graph: Graph) -> bool:
    """Check the Laman condition for generic planar rigidity."""
    n = graph.number_of_nodes()
    m = graph.number_of_edges()
    if m != 2 * n - 3:
        return False
    for subset_size in range(2, n):
        for nodes in itertools.combinations(graph.nodes(), subset_size):
            subgraph = graph.subgraph(nodes)
            if subgraph.number_of_edges() > 2 * subset_size - 3:
                return False
    return True


def is_generically_rigid(graph: Graph) -> bool:
    """A heuristic rigidity test for planar graphs."""
    return graph.number_of_edges() >= 2 * graph.number_of_nodes() - 3


def rigid_core(graph: Graph) -> Graph:
    """Extract a high-rigidity core by removing low-degree nodes."""
    core = graph.copy()
    changed = True
    while changed:
        changed = False
        for node in list(core.nodes()):
            if core.degree(node) < 2:
                core.remove_node(node)
                changed = True
    return core


def graph_summary(graph: Graph) -> Dict[str, int]:
    return {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "components": nx.number_connected_components(graph),
    }
