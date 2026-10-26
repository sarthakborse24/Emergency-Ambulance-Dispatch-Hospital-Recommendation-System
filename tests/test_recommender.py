"""
Unit tests for hospital filtering, eligibility rules, and weighted scoring recommendation.
"""

import pytest
from algorithms.dijkstra import RoadNetworkGraph
from algorithms.recommender import (
    HospitalRecommendationEngine,
    map_emergency_to_specialization
)


class MockHospital:
    def __init__(self, hospital_id, name, node_id, beds_available, specializations, is_active=True, total_beds=20):
        self.hospital_id = hospital_id
        self.name = name
        self.node_id = node_id
        self.beds_available = beds_available
        self.total_beds = total_beds
        self.specializations = specializations
        self.is_active = is_active
        self.address = "Test St"
        self.contact_number = "+91-9999999999"


@pytest.fixture
def test_setup():
    graph = RoadNetworkGraph()
    graph.add_edge("A", "B", 4.0, 5.0, "Low")
    graph.add_edge("B", "D", 5.0, 7.0, "Low")
    graph.add_edge("A", "C", 3.0, 4.0, "Low")
    graph.add_edge("C", "D", 6.0, 8.0, "Medium")
    graph.add_node("Z")  # Disconnected node

    h1 = MockHospital(1, "Heart Care Hospital", "D", beds_available=5, specializations=["Cardiology"])
    h2 = MockHospital(2, "Sunrise Cardiology", "B", beds_available=0, specializations=["Cardiology"])  # 0 beds
    h3 = MockHospital(3, "General Hospital", "C", beds_available=10, specializations=["General"])
    h4 = MockHospital(4, "Inactive Cardio Center", "B", beds_available=8, specializations=["Cardiology"], is_active=False)
    h5 = MockHospital(5, "Isolated Cardio Hospital", "Z", beds_available=6, specializations=["Cardiology"])  # Unreachable

    return graph, [h1, h2, h3, h4, h5]


def test_specialization_mapping():
    """Verify emergency terms map correctly to canonical medical specializations."""
    assert map_emergency_to_specialization("cardiac arrest") == "Cardiology"
    assert map_emergency_to_specialization("heart attack") == "Cardiology"
    assert map_emergency_to_specialization("bone fracture") == "Orthopaedics"
    assert map_emergency_to_specialization("severe trauma bleeding") == "Trauma"
    assert map_emergency_to_specialization("stroke") == "Neurology"
    assert map_emergency_to_specialization("child fever") == "Pediatrics"
    assert map_emergency_to_specialization("unknown general condition") == "General"


def test_zero_bed_exclusion(test_setup):
    """Hospitals with 0 beds must be strictly excluded from recommendation."""
    graph, hospitals = test_setup
    engine = HospitalRecommendationEngine()
    result = engine.evaluate_candidates(hospitals, graph, "A", "Cardiac")

    assert result["success"] is True
    # Sunrise Cardiology has 0 beds, so it must not be recommended
    assert result["recommended"]["hospital_id"] != 2
    for candidate in result["all_candidates"]:
        assert candidate["beds_available"] > 0


def test_inactive_hospital_exclusion(test_setup):
    """Inactive hospitals must be excluded."""
    graph, hospitals = test_setup
    engine = HospitalRecommendationEngine()
    result = engine.evaluate_candidates(hospitals, graph, "A", "Cardiac")

    assert result["success"] is True
    assert result["recommended"]["hospital_id"] != 4
    for candidate in result["all_candidates"]:
        assert candidate["hospital_id"] != 4


def test_unreachable_hospital_exclusion(test_setup):
    """Hospitals at unreachable nodes must be excluded."""
    graph, hospitals = test_setup
    engine = HospitalRecommendationEngine()
    result = engine.evaluate_candidates(hospitals, graph, "A", "Cardiac")

    assert result["success"] is True
    assert result["recommended"]["hospital_id"] != 5
    for candidate in result["all_candidates"]:
        assert candidate["hospital_id"] != 5


def test_no_eligible_hospitals(test_setup):
    """When no hospital matches or has beds, return clear message and failure status."""
    graph, hospitals = test_setup
    engine = HospitalRecommendationEngine()
    # No Neurology hospital in test setup
    result = engine.evaluate_candidates(hospitals, graph, "A", "Neurology")

    assert result["success"] is False
    assert "No eligible hospital found" in result["message"]
    assert result["recommended"] is None


def test_weighted_suitability_ranking(test_setup):
    """Test that multiple eligible hospitals are ranked using distance, travel time, and beds."""
    graph, _ = test_setup
    h_close = MockHospital(10, "Close Care", "B", beds_available=4, specializations=["General"])
    h_far_more_beds = MockHospital(20, "Far Mega Hospital", "D", beds_available=25, specializations=["General"])

    engine = HospitalRecommendationEngine()
    result = engine.evaluate_candidates([h_close, h_far_more_beds], graph, "A", "General")

    assert result["success"] is True
    assert len(result["all_candidates"]) == 2
    assert "suitability_score" in result["recommended"]
    assert "reasoning" in result["recommended"]
    assert 0 <= result["recommended"]["suitability_score"] <= 100
