"""
Unit tests for Dijkstra shortest path and traffic-aware routing algorithm.
"""

import pytest
from algorithms.dijkstra import RoadNetworkGraph


@pytest.fixture
def sample_graph():
    """
    Standard test graph:
    A --(4km, 6m)--> B --(5km, 7m)--> D
    |                                 ^
    (2km, 8m)                         |
    v                                 |
    C -----------(8km, 10m)-----------+
    """
    graph = RoadNetworkGraph()
    # A - B: 4km, 6 min, Low traffic
    graph.add_edge("A", "B", distance_km=4.0, travel_time_minutes=6.0, traffic_level="Low")
    # A - C: 2km, 8 min, High traffic
    graph.add_edge("A", "C", distance_km=2.0, travel_time_minutes=8.0, traffic_level="High")
    # B - D: 5km, 7 min, Low traffic
    graph.add_edge("B", "D", distance_km=5.0, travel_time_minutes=7.0, traffic_level="Low")
    # C - D: 8km, 10 min, Medium traffic
    graph.add_edge("C", "D", distance_km=8.0, travel_time_minutes=10.0, traffic_level="Medium")
    # Disconnected node Z
    graph.add_node("Z")
    return graph


def test_dijkstra_shortest_distance(sample_graph):
    """Test shortest distance pathfinding."""
    # By distance:
    # A -> B -> D is 4 + 5 = 9 km
    # A -> C -> D is 2 + 8 = 10 km
    # Shortest distance path should be A -> B -> D
    res = sample_graph.dijkstra("A", "D", optimize_by="distance")
    assert res is not None
    assert res["route"] == ["A", "B", "D"]
    assert res["total_distance_km"] == 9.0
    assert res["total_travel_time_minutes"] == 13.0


def test_dijkstra_fastest_travel_time(sample_graph):
    """Test fastest travel time pathfinding with traffic considerations."""
    # By travel time:
    # A -> B -> D is 6 + 7 = 13 minutes
    # A -> C -> D is 8 + 10 = 18 minutes
    res = sample_graph.dijkstra("A", "D", optimize_by="travel_time")
    assert res is not None
    assert res["route"] == ["A", "B", "D"]
    assert res["total_travel_time_minutes"] == 13.0


def test_dijkstra_same_start_and_target(sample_graph):
    """Path to self should be 0 cost."""
    res = sample_graph.dijkstra("A", "A")
    assert res is not None
    assert res["route"] == ["A"]
    assert res["total_distance_km"] == 0.0
    assert res["total_travel_time_minutes"] == 0.0


def test_dijkstra_unreachable_node(sample_graph):
    """Unreachable node must return None without raising exceptions."""
    res = sample_graph.dijkstra("A", "Z")
    assert res is None


def test_dijkstra_invalid_node(sample_graph):
    """Non-existent nodes must return None safely."""
    assert sample_graph.dijkstra("NON_EXISTENT", "D") is None
    assert sample_graph.dijkstra("A", "NON_EXISTENT") is None
