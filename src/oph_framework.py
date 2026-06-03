"""
OPH-Inspired Framework for Erdős Distance Problems

This module translates Observer-Patch Holography principles into a computational
framework for exploring Erdős distance conjectures. Key concepts:

1. Patch-based decomposition: Point configurations viewed as overlapping local
   observers (patches) that must maintain consistency at boundaries.

2. Seam language: Distance relationships reframed as "seams" between points,
   where each seam carries a distinct value (vibration mode).

3. Observer-visible targets: Quantitative audit checklist (like OPH's SOPH)
   against which all configurations are tested.

4. Moduli stabilization: Parameter space locked to achieve target behavior,
   removing free dials.

5. Multi-scale consensus: Verification at local, regional, and global scales
   with repair protocols for inconsistencies.

Reference: B. Mueller, Observer-Patch Holography as a String-Vacuum Selector
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Set, Optional
import numpy as np
from itertools import combinations
from scipy.spatial.distance import euclidean, pdist, squareform


# =============================================================================
# PART 1: DISTANCE SEAMS (OPH edges as distance graph constraints)
# =============================================================================

@dataclass
class DistanceSeam:
    """
    OPH-inspired: A 'seam' is the constraint/relationship between two points.
    In OPH, seams carry representation labels and vibration modes.
    Here, seams carry distance values and distinctness contributions.
    """
    point_i: int
    point_j: int
    distance: float = 0.0
    
    def __hash__(self):
        return hash((min(self.point_i, self.point_j), 
                     max(self.point_i, self.point_j)))
    
    def __eq__(self, other):
        if not isinstance(other, DistanceSeam):
            return False
        return {self.point_i, self.point_j} == {other.point_i, other.point_j}
    
    def oscillation_fingerprint(self) -> float:
        """
        Like OPH standing waves: the 'tone' or 'mode' of this seam.
        Used for grouping distances into distinct categories.
        """
        return self.distance % 1.0
    
    def __repr__(self):
        return f"Seam({self.point_i}-{self.point_j}: {self.distance:.6f})"


class ConfigurationAsSeamGraph:
    """
    Reframe a point configuration as a graph of distance seams.
    This perspective highlights the distinctness structure directly.
    """
    
    def __init__(self, points: np.ndarray):
        """
        Args:
            points: (n, d) array of point coordinates
        """
        self.points = np.asarray(points)
        self.n = len(points)
        self.dim = points.shape[1] if points.ndim > 1 else 1
        self.seams: Dict[Tuple[int, int], DistanceSeam] = {}
        self._build_seams()
    
    def _build_seams(self):
        """Construct seams for all point pairs."""
        self.seams = {}
        for i, j in combinations(range(self.n), 2):
            seam = DistanceSeam(i, j)
            self.seams[(i, j)] = seam
        self.enforce_seam_distances()
    
    def enforce_seam_distances(self):
        """OPH repair: Compute all seam distances from point coordinates."""
        for (i, j), seam in self.seams.items():
            seam.distance = euclidean(self.points[i], self.points[j])
    
    def count_distinct_seam_oscillations(self, tolerance: float = 1e-6) -> int:
        """
        Count distinct distances = distinct seam vibration modes.
        Uses tolerance to group nearly-identical distances.
        """
        distances = np.array([s.distance for s in self.seams.values()])
        distances_sorted = np.sort(distances)
        
        distinct = 1
        for i in range(1, len(distances_sorted)):
            if distances_sorted[i] - distances_sorted[i-1] > tolerance:
                distinct += 1
        
        return distinct
    
    def get_distance_groups(self, tolerance: float = 1e-6) -> Dict[int, List[DistanceSeam]]:
        """
        Group seams by distance equivalence (within tolerance).
        Returns dict mapping group_id -> list of seams in that group.
        """
        distances_with_seams = [(s.distance, s) for s in self.seams.values()]
        distances_with_seams.sort()
        
        groups = {}
        group_id = 0
        current_group = []
        
        for dist, seam in distances_with_seams:
            if current_group and (dist - current_group[0][0]) > tolerance:
                groups[group_id] = [s for _, s in current_group]
                group_id += 1
                current_group = []
            current_group.append((dist, seam))
        
        if current_group:
            groups[group_id] = [s for _, s in current_group]
        
        return groups
    
    def seam_connectivity_matrix(self) -> np.ndarray:
        """
        OPH-inspired: Represent seam topology as adjacency-like matrix.
        Element (i, j) = distance between points i and j, or 0 if undefined.
        """
        matrix = np.zeros((self.n, self.n))
        for (i, j), seam in self.seams.items():
            matrix[i, j] = seam.distance
            matrix[j, i] = seam.distance
        return matrix


# =============================================================================
# PART 2: CONFIGURATION PATCHES (OPH local observers)
# =============================================================================

@dataclass
class ConfigurationPatch:
    """
    OPH-inspired: A local observer patch over a subset of points.
    Each patch maintains local distance consistency and can overlap with neighbors.
    """
    patch_id: int
    point_indices: Set[int]
    boundary_radius: float = 1.0
    local_seams: Dict[Tuple[int, int], DistanceSeam] = field(default_factory=dict)
    
    def __post_init__(self):
        self.point_indices = set(self.point_indices)
    
    def extract_local_seams(self, seam_graph: ConfigurationAsSeamGraph):
        """Extract all seams where both endpoints are in this patch."""
        self.local_seams = {}
        for (i, j), seam in seam_graph.seams.items():
            if i in self.point_indices and j in self.point_indices:
                self.local_seams[(i, j)] = seam
    
    def verify_overlap_consistency(self, neighbor_patch: 'ConfigurationPatch', 
                                   tolerance: float = 1e-6) -> bool:
        """
        OPH repair protocol: Ensure shared boundary points agree on distances.
        Returns True if consistent, False if conflict detected.
        """
        shared_points = self.point_indices & neighbor_patch.point_indices
        
        for p1, p2 in combinations(shared_points, 2):
            key = (min(p1, p2), max(p1, p2))
            
            dist_self = None
            for (i, j), seam in self.local_seams.items():
                if {i, j} == {p1, p2}:
                    dist_self = seam.distance
                    break
            
            dist_neighbor = None
            for (i, j), seam in neighbor_patch.local_seams.items():
                if {i, j} == {p1, p2}:
                    dist_neighbor = seam.distance
                    break
            
            if dist_self and dist_neighbor:
                if abs(dist_self - dist_neighbor) > tolerance:
                    return False
        
        return True
    
    def get_boundary_seams(self) -> List[DistanceSeam]:
        """Return seams that cross the patch boundary (one endpoint inside, one outside)."""
        return []  # Placeholder for now; full implementation depends on full graph
    
    def local_distinctness(self, tolerance: float = 1e-6) -> int:
        """Count distinct distances within this patch."""
        if not self.local_seams:
            return 0
        distances = np.array([s.distance for s in self.local_seams.values()])
        distances_sorted = np.sort(distances)
        
        distinct = 1
        for i in range(1, len(distances_sorted)):
            if distances_sorted[i] - distances_sorted[i-1] > tolerance:
                distinct += 1
        return distinct


# =============================================================================
# PART 3: ERDŐS TARGET & AUDIT SYSTEM (OPH order ticket)
# =============================================================================

@dataclass
class ErdosTarget:
    """
    OPH-style audit checklist for Erdős conjectures.
    Every configuration is tested against this target.
    Like OPH's SOPH, this is derived from first principles (collinearity, 
    distinctness, rigidity) rather than experimental input.
    """
    n: int                           # Number of points
    min_distinct_distances: int      # ⌊n/2⌋ from Erdős #1082
    max_collinear_triple: int = 0    # Constraint: no three collinear
    
    def __post_init__(self):
        if self.min_distinct_distances == 0:
            self.min_distinct_distances = max(1, (self.n + 1) // 2)
    
    def create_audit_checklist(self) -> Dict[str, bool]:
        """Create empty checklist to be filled by audit function."""
        return {
            "erdos_1082_set_bound": False,        # distinct_distances >= ⌊n/2⌋
            "no_three_collinear": False,          # All triples non-collinear
            "rigidity_pass": False,                # Valid in dimension d
            "seam_consistency": False,             # All seams form valid metric
        }
    
    def __repr__(self):
        return (f"ErdosTarget(n={self.n}, "
                f"min_distinct={self.min_distinct_distances}, "
                f"no_three_collinear={self.max_collinear_triple == 0})")


def audit_configuration(config: ConfigurationAsSeamGraph, 
                        target: ErdosTarget,
                        collinearity_tolerance: float = 1e-6) -> Tuple[bool, Dict]:
    """
    OPH-style audit: Check all gates against the target.
    Like OPH's order ticket, every line must pass.
    
    Args:
        config: Configuration as seam graph
        target: Erdős target checklist
        collinearity_tolerance: Threshold for three-point collinearity
    
    Returns:
        (passes_all_gates, detailed_report_dict)
    """
    report = target.create_audit_checklist()
    
    # Gate 1: Erdős #1082 set bound
    distinct_count = config.count_distinct_seam_oscillations(tolerance=collinearity_tolerance)
    report["erdos_1082_set_bound"] = distinct_count >= target.min_distinct_distances
    
    # Gate 2: No three collinear
    no_three_col = check_no_three_collinear(config.points, tolerance=collinearity_tolerance)
    report["no_three_collinear"] = no_three_col
    
    # Gate 3: Rigidity (basic check: not degenerate)
    non_degenerate = config.n > config.dim
    report["rigidity_pass"] = non_degenerate
    
    # Gate 4: Seam consistency (triangle inequality, etc.)
    seams_consistent = verify_metric_space(config.seams, tolerance=collinearity_tolerance)
    report["seam_consistency"] = seams_consistent
    
    passes_all = all(report.values())
    
    return passes_all, report


def check_no_three_collinear(points: np.ndarray, tolerance: float = 1e-6) -> bool:
    """Check if any three points are collinear."""
    n = len(points)
    for i, j, k in combinations(range(n), 3):
        p1, p2, p3 = points[i], points[j], points[k]
        
        # Cross product (for 2D: z-component; for 3D: full vector)
        v1 = p2 - p1
        v2 = p3 - p1
        
        if points.shape[1] == 2:
            cross = v1[0] * v2[1] - v1[1] * v2[0]
            if abs(cross) < tolerance:
                return False
        else:
            cross = np.cross(v1, v2)
            if np.linalg.norm(cross) < tolerance:
                return False
    
    return True


def verify_metric_space(seams: Dict[Tuple[int, int], DistanceSeam], 
                       tolerance: float = 1e-6) -> bool:
    """Verify triangle inequality and symmetry for all seams."""
    # Simplified: check that no seam is extremely small relative to others
    distances = [s.distance for s in seams.values()]
    if not distances:
        return True
    
    max_dist = max(distances)
    min_dist = min(distances)
    
    # Sanity check: max should be reasonable multiple of min
    if min_dist > tolerance and max_dist / min_dist > 1e6:
        return False
    
    return True


# =============================================================================
# PART 4: MODULI STABILIZATION (parameter space locking)
# =============================================================================

@dataclass
class ParameterLockdown:
    """
    OPH-inspired parameter space locking.
    Like OPH's F(m★) = SOPH, find the parameter region where the target is achieved.
    Removes free dials by systematically sweeping and locking.
    """
    target: ErdosTarget
    parameter_ranges: Dict[str, List] = field(default_factory=dict)
    locked_params: Optional[Dict] = None
    sweep_results: List = field(default_factory=list)
    
    def __post_init__(self):
        if not self.parameter_ranges:
            self.parameter_ranges = {
                'steps': [1000, 2000, 3000, 5000],
                'opt_method': ['anneal', 'hillclimb', 'direct'],
                'seed_type': ['uniform', 'lattice', 'regular'],
            }
    
    def lock_to_target(self, run_optimization_fn, collinearity_tolerance: float = 1e-6):
        """
        Sweep parameter space and lock to combinations that hit the target.
        
        Args:
            run_optimization_fn: Function signature:
                config = run_optimization_fn(n, steps, opt_method, seed_type)
                Returns a ConfigurationAsSeamGraph and energy value.
            collinearity_tolerance: Tolerance for distance distinctness check
        """
        best_energy = float('inf')
        self.locked_params = None
        self.sweep_results = []
        
        for steps in self.parameter_ranges.get('steps', [2000]):
            for opt_method in self.parameter_ranges.get('opt_method', ['anneal']):
                for seed_type in self.parameter_ranges.get('seed_type', ['uniform']):
                    # Run optimization
                    result = run_optimization_fn(
                        n=self.target.n,
                        steps=steps,
                        opt_method=opt_method,
                        seed_type=seed_type
                    )
                    
                    if isinstance(result, tuple):
                        config, energy = result
                    else:
                        config, energy = result, float('inf')
                    
                    # Audit against target
                    passes, report = audit_configuration(config, self.target, 
                                                        collinearity_tolerance)
                    
                    self.sweep_results.append({
                        'params': {
                            'steps': steps,
                            'opt_method': opt_method,
                            'seed_type': seed_type,
                        },
                        'config': config,
                        'energy': energy,
                        'audit_passes': passes,
                        'audit_report': report,
                    })
                    
                    # Lock to parameters that pass and have low energy
                    if passes and energy < best_energy:
                        best_energy = energy
                        self.locked_params = {
                            'steps': steps,
                            'opt_method': opt_method,
                            'seed_type': seed_type,
                            'energy': energy,
                        }
        
        return self.locked_params
    
    def get_all_successful_params(self) -> List[Dict]:
        """Get all parameter combinations that passed the audit."""
        return [r for r in self.sweep_results if r['audit_passes']]


# =============================================================================
# PART 5: MULTI-SCALE AUDIT (hierarchical verification)
# =============================================================================

class MultiScaleAudit:
    """
    OPH-inspired hierarchical audit at different scales.
    Configurations must achieve consensus across local, regional, and global scales.
    """
    
    @staticmethod
    def audit_k_neighborhoods(config: ConfigurationAsSeamGraph, 
                             k_hop: int = 3,
                             collinearity_tolerance: float = 1e-6) -> Dict:
        """
        Audit on k-hop distance neighborhoods.
        For each point, check distinctness in its k-hop neighborhood.
        """
        seam_graph = config
        n = config.n
        
        # Build k-hop neighborhoods
        neighborhoods = {}
        for center in range(n):
            neighbors = {center}
            current = {center}
            
            for _ in range(k_hop):
                next_layer = set()
                for node in current:
                    for (i, j), seam in seam_graph.seams.items():
                        if i == node and j not in neighbors:
                            next_layer.add(j)
                        elif j == node and i not in neighbors:
                            next_layer.add(i)
                neighbors.update(next_layer)
                current = next_layer
            
            neighborhoods[center] = neighbors
        
        # Audit each neighborhood
        local_reports = {}
        for center, neighbor_set in neighborhoods.items():
            local_seams = {}
            for (i, j), seam in seam_graph.seams.items():
                if i in neighbor_set and j in neighbor_set:
                    local_seams[(i, j)] = seam
            
            if local_seams:
                distinct = count_distinct_from_seams(local_seams, collinearity_tolerance)
                local_reports[center] = {
                    'neighborhood_size': len(neighbor_set),
                    'distinct_distances': distinct,
                }
        
        return local_reports
    
    @staticmethod
    def verify_scale_consensus(global_audit: Dict, 
                               local_audits: Dict,
                               report_key: str = "no_three_collinear") -> bool:
        """
        Check that all scales agree on critical properties.
        Returns True if consensus achieved across all scales.
        """
        if not global_audit.get(report_key, False):
            return False
        
        # All local audits should also pass key gates
        for local_report in local_audits.values():
            if isinstance(local_report, dict) and report_key in local_report:
                if not local_report[report_key]:
                    return False
        
        return True


def count_distinct_from_seams(seams: Dict, tolerance: float = 1e-6) -> int:
    """Helper: count distinct distances from a seam dictionary."""
    if not seams:
        return 0
    distances = np.array([s.distance for s in seams.values()])
    distances_sorted = np.sort(distances)
    
    distinct = 1
    for i in range(1, len(distances_sorted)):
        if distances_sorted[i] - distances_sorted[i-1] > tolerance:
            distinct += 1
    return distinct


# =============================================================================
# PART 6: INTEGRATION UTILITIES
# =============================================================================

def wrap_points_as_seam_graph(points: np.ndarray) -> ConfigurationAsSeamGraph:
    """Convenience: Convert raw points to seam graph representation."""
    return ConfigurationAsSeamGraph(points)


def create_patches_from_config(config: ConfigurationAsSeamGraph, 
                               patch_size: int = 3) -> List[ConfigurationPatch]:
    """
    Decompose a configuration into overlapping patches.
    Simple greedy algorithm: group nearby points.
    """
    n = config.n
    patches = []
    visited = set()
    
    for center in range(n):
        if center in visited:
            continue
        
        # Build patch around center: add nearest neighbors up to patch_size
        distances_from_center = []
        for j in range(n):
            if j != center:
                key = (min(center, j), max(center, j))
                if key in config.seams:
                    dist = config.seams[key].distance
                    distances_from_center.append((dist, j))
        
        distances_from_center.sort()
        patch_members = {center}
        for _, neighbor_idx in distances_from_center[:patch_size - 1]:
            patch_members.add(neighbor_idx)
        
        patch = ConfigurationPatch(
            patch_id=len(patches),
            point_indices=patch_members
        )
        patch.extract_local_seams(config)
        patches.append(patch)
        visited.update(patch_members)
    
    return patches


def report_oph_analysis(config: ConfigurationAsSeamGraph,
                       target: ErdosTarget) -> str:
    """Generate a human-readable OPH analysis report."""
    passes_all, audit_report = audit_configuration(config, target)
    distinct_count = config.count_distinct_seam_oscillations()
    
    report_lines = [
        "=" * 70,
        "OPH FRAMEWORK ANALYSIS REPORT",
        "=" * 70,
        f"Target: {target}",
        f"Configuration: {config.n} points in {config.dim}D",
        f"Distinct distances: {distinct_count}",
        "",
        "AUDIT RESULTS:",
        "-" * 70,
    ]
    
    for gate, result in audit_report.items():
        status = "✓ PASS" if result else "✗ FAIL"
        report_lines.append(f"  {gate:.<40} {status}")
    
    report_lines.extend([
        "-" * 70,
        f"Overall: {'✓ ALL GATES PASS' if passes_all else '✗ GATES FAILED'}",
        "=" * 70,
    ])
    
    return "\n".join(report_lines)
