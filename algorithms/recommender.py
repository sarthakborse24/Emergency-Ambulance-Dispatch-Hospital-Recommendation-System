"""
Hospital Recommendation and Multi-Criteria Weighted Scoring Engine.
Filters candidates by medical eligibility, calculates optimal routes,
computes normalized suitability scores, and ranks hospitals with full explainability.
"""

from typing import List, Dict, Any, Optional, Tuple
from config import Config
from algorithms.dijkstra import RoadNetworkGraph


def map_emergency_to_specialization(emergency_type: str) -> str:
    """Map natural language emergency query string to canonical specialization."""
    if not emergency_type:
        return "General"
    t = emergency_type.strip().lower()
    if any(k in t for k in ["cardiac", "heart", "cardio", "chest pain", "infarction", "angina"]):
        return "Cardiology"
    elif any(k in t for k in ["ortho", "fracture", "bone", "joint", "spine", "dislocation"]):
        return "Orthopaedics"
    elif any(k in t for k in ["trauma", "accident", "hemorrhage", "crash", "bleeding"]):
        return "Trauma"
    elif any(k in t for k in ["neuro", "stroke", "brain", "seizure", "paralysis"]):
        return "Neurology"
    elif any(k in t for k in ["pediatric", "child", "infant"]):
        return "Pediatrics"
    return "General"


class HospitalRecommendationEngine:
    """
    Evaluates hospital candidates for emergency dispatch using Dijkstra route optimization
    and multi-criteria normalized weighted scoring.
    """

    def __init__(
        self,
        weight_dist: float = Config.WEIGHT_DISTANCE,
        weight_traffic: float = Config.WEIGHT_TRAFFIC,
        weight_beds: float = Config.WEIGHT_BEDS,
        weight_spec: float = Config.WEIGHT_SPECIALIZATION
    ):
        self.w_dist = weight_dist
        self.w_traffic = weight_traffic
        self.w_beds = weight_beds
        self.w_spec = weight_spec

        # Normalize weights so they sum to exactly 1.0
        total_w = self.w_dist + self.w_traffic + self.w_beds + self.w_spec
        if total_w > 0:
            self.w_dist /= total_w
            self.w_traffic /= total_w
            self.w_beds /= total_w
            self.w_spec /= total_w

    def evaluate_candidates(
        self,
        hospitals: List[Any],
        road_graph: RoadNetworkGraph,
        patient_node: str,
        emergency_type: str,
        severity: str = "Medium"
    ) -> Dict[str, Any]:
        """
        Execute full recommendation pipeline:
        1. Eligibility filtering (beds > 0, specialization match, active status, graph reachability).
        2. Route calculation via Dijkstra algorithm.
        3. Feature normalization (distance, traffic congestion, bed availability, specialty match).
        4. Weighted scoring and deterministic ranking.
        5. Detailed explanation generation.
        """
        required_spec = map_emergency_to_specialization(emergency_type)
        patient_node = str(patient_node).upper()

        if patient_node not in road_graph.nodes:
            return {
                "success": False,
                "error": f"Patient location node '{patient_node}' does not exist in the road network.",
                "recommended": None,
                "all_candidates": []
            }

        eligible_candidates = []
        ineligible_reasons = []

        # Step A: Filter hospitals for eligibility
        for h in hospitals:
            # Active check
            if not getattr(h, "is_active", True):
                ineligible_reasons.append(f"{h.name}: Hospital is marked inactive/closed.")
                continue

            # Bed availability check
            if h.beds_available <= 0:
                ineligible_reasons.append(f"{h.name}: Zero available beds ({h.beds_available}/{h.total_beds}).")
                continue

            # Specialization match check
            h_specs = [s.name if hasattr(s, "name") else str(s) for s in getattr(h, "specializations", [])]
            if not h_specs and hasattr(h, "specialization"):
                h_specs = [h.specialization]

            has_spec = any(s.lower() == required_spec.lower() for s in h_specs)
            # General facilities can serve as lower-tier emergency match if needed, but primary check prioritizes required spec
            if not has_spec:
                ineligible_reasons.append(f"{h.name}: Does not offer required '{required_spec}' (Offers: {', '.join(h_specs)}).")
                continue

            # Reachability check using Dijkstra algorithm
            route_result = road_graph.dijkstra(patient_node, h.node_id, optimize_by="travel_time")
            if not route_result:
                ineligible_reasons.append(f"{h.name} (Node {h.node_id}): Unreachable from Patient Node {patient_node} due to road network disconnection.")
                continue

            candidate = {
                "hospital_id": h.hospital_id,
                "name": h.name,
                "address": h.address,
                "node": h.node_id,
                "node_id": h.node_id,
                "beds_available": h.beds_available,
                "total_beds": h.total_beds,
                "contact_number": h.contact_number,
                "specializations": h_specs,
                "specialization": required_spec if has_spec else (h_specs[0] if h_specs else "General"),
                "distance_km": route_result["total_distance_km"],
                "travel_time_minutes": route_result["total_travel_time_minutes"],
                "route": route_result["route"],
                "average_traffic": route_result["average_traffic"],
                "steps": route_result["steps"]
            }
            eligible_candidates.append(candidate)

        if not eligible_candidates:
            return {
                "success": False,
                "message": f"No eligible hospital found matching specialization '{required_spec}' with available beds.",
                "required_specialization": required_spec,
                "patient_node": patient_node,
                "reasons": ineligible_reasons,
                "recommended": None,
                "all_candidates": []
            }

        # Step B: Normalize metrics for multi-criteria weighted scoring
        distances = [c["distance_km"] for c in eligible_candidates]
        travel_times = [c["travel_time_minutes"] for c in eligible_candidates]
        beds = [c["beds_available"] for c in eligible_candidates]

        min_dist, max_dist = min(distances), max(distances)
        min_time, max_time = min(travel_times), max(travel_times)
        min_beds, max_beds = min(beds), max(beds)

        for c in eligible_candidates:
            # 1. Distance score (shorter is better, normalized 0.0 to 1.0)
            if max_dist == min_dist:
                score_dist = 1.0
            else:
                score_dist = 1.0 - ((c["distance_km"] - min_dist) / (max_dist - min_dist))

            # 2. Traffic / Travel time score (faster travel time is better, normalized 0.0 to 1.0)
            if max_time == min_time:
                score_traffic = 1.0
            else:
                score_traffic = 1.0 - ((c["travel_time_minutes"] - min_time) / (max_time - min_time))

            # 3. Bed score (more beds is better, normalized 0.0 to 1.0)
            if max_beds == min_beds:
                score_beds = 1.0
            else:
                score_beds = (c["beds_available"] - min_beds) / (max_beds - min_beds)

            # 4. Specialization match score
            score_spec = 1.0

            # Composite weighted suitability score (scaled to 0 - 100)
            composite = (
                (self.w_dist * score_dist) +
                (self.w_traffic * score_traffic) +
                (self.w_beds * score_beds) +
                (self.w_spec * score_spec)
            ) * 100.0

            c["score_breakdown"] = {
                "distance_score": round(score_dist * 100, 1),
                "traffic_score": round(score_traffic * 100, 1),
                "bed_score": round(score_beds * 100, 1),
                "specialization_score": round(score_spec * 100, 1)
            }
            c["suitability_score"] = round(composite, 2)

        # Step C: Deterministic ranking (Score DESC, Travel Time ASC, Beds DESC, ID ASC)
        eligible_candidates.sort(
            key=lambda x: (-x["suitability_score"], x["travel_time_minutes"], -x["beds_available"], x["hospital_id"])
        )

        best = eligible_candidates[0]

        # Generate detailed rationale for selection
        best["reasoning"] = (
            f"Recommended as top destination with a suitability score of {best['suitability_score']}/100. "
            f"It provides {best['beds_available']} available beds in {required_spec}, "
            f"an estimated arrival time of {best['travel_time_minutes']} minutes over a {best['distance_km']} km route "
            f"({ ' -> '.join(best['route']) }) with {best['average_traffic'].lower()} traffic conditions."
        )

        return {
            "success": True,
            "patient_node": patient_node,
            "required_specialization": required_spec,
            "severity": severity,
            "recommended": best,
            "all_candidates": eligible_candidates,
            "total_evaluated": len(hospitals),
            "total_eligible": len(eligible_candidates)
        }
