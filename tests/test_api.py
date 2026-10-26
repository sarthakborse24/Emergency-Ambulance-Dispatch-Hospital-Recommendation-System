"""
API endpoint integration tests covering status codes, JSON responses,
validation rules, and database updates.
"""

import json


def test_api_health(client):
    """Test health check returns 200 OK and online status."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "online"
    assert data["database"] == "connected"


def test_api_stats(client):
    """Test stats endpoint returns aggregate counts from SQL database."""
    res = client.get("/api/stats")
    assert res.status_code == 200
    data = res.get_json()
    assert "total_hospitals" in data
    assert "total_beds_available" in data
    assert "available_ambulances" in data
    assert data["total_hospitals"] >= 1


def test_api_hospitals_endpoints(client):
    """Test hospital listing, creation, and bed capacity update."""
    # List
    res = client.get("/api/hospitals")
    assert res.status_code == 200
    data = res.get_json()
    assert data["total"] >= 1
    first_id = data["hospitals"][0]["hospital_id"]

    # Quick update beds
    patch_res = client.patch(
        f"/api/hospitals/{first_id}/beds",
        json={"beds_available": 19}
    )
    assert patch_res.status_code == 200
    assert patch_res.get_json()["beds_available"] == 19

    # Create new
    post_res = client.post("/api/hospitals", json={
        "name": "St. Jude Emergency Center",
        "node_id": "A",
        "beds_available": 12,
        "total_beds": 30,
        "specializations": ["Cardiology", "General"]
    })
    assert post_res.status_code == 201
    assert post_res.get_json()["success"] is True


def test_api_ambulances_endpoints(client):
    """Test ambulance listing and status update."""
    res = client.get("/api/ambulances")
    assert res.status_code == 200
    data = res.get_json()
    assert data["total"] >= 1
    amb_id = data["ambulances"][0]["ambulance_id"]

    # Update status
    patch_res = client.patch(
        f"/api/ambulances/{amb_id}/status",
        json={"status": "Maintenance"}
    )
    assert patch_res.status_code == 200
    assert patch_res.get_json()["status"] == "Maintenance"


def test_api_network_endpoint(client):
    """Test road network topology endpoint."""
    res = client.get("/api/network")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["nodes"]) >= 4
    assert len(data["edges"]) >= 4


def test_api_route_calculation(client):
    """Test point-to-point Dijkstra route calculation between arbitrary nodes."""
    res = client.post("/api/route", json={
        "start": "A",
        "target": "H",
        "optimize_by": "travel_time"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["route"][0] == "A"
    assert data["route"][-1] == "H"
    assert data["total_distance_km"] > 0
    assert len(data["steps"]) >= 1


def test_api_dispatch_recommendation_flow(client):
    """Test full dispatch recommendation and database confirmation flow."""
    # 1. Evaluate dispatch
    eval_res = client.post("/api/dispatch", json={
        "location": "A",
        "emergency_type": "Cardiac",
        "severity": "High"
    })
    assert eval_res.status_code == 200
    eval_data = eval_res.get_json()
    assert eval_data["success"] is True
    assert eval_data["recommended"] is not None
    assert "route" in eval_data["recommended"]
    assert "travel_time_minutes" in eval_data["recommended"]
    assert "suitability_score" in eval_data["recommended"]

    # 2. Confirm and persist dispatch
    confirm_res = client.post("/api/dispatch/confirm", json={
        "location": "A",
        "emergency_type": "Cardiac",
        "severity": "High",
        "caller_name": "Emergency Operator 4",
        "recommended": eval_data["recommended"],
        "assigned_ambulance": eval_data.get("assigned_ambulance"),
        "all_candidates": eval_data.get("all_candidates")
    })
    assert confirm_res.status_code == 201
    confirm_data = confirm_res.get_json()
    assert confirm_data["success"] is True
    assert "request_id" in confirm_data
    assert "dispatch_id" in confirm_data

    # 3. Verify in emergency history
    hist_res = client.get("/api/history")
    assert hist_res.status_code == 200
    hist_data = hist_res.get_json()
    assert any(r["request_id"] == confirm_data["request_id"] for r in hist_data["requests"])


def test_api_dispatch_validation_errors(client):
    """Test validation errors for invalid location or missing parameters."""
    res = client.post("/api/dispatch", json={"location": "", "emergency_type": "Cardiac"})
    assert res.status_code == 400

    res_invalid_node = client.post("/api/dispatch", json={"location": "INVALID_NODE", "emergency_type": "Cardiac"})
    assert res_invalid_node.status_code == 404
