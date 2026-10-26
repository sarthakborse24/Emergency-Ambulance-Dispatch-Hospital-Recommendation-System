"""
Integration tests for database models, relationships, constraints, and persistence.
"""

import pytest
from models import Hospital, Ambulance, RoadNode, RoadEdge, EmergencyRequest, DispatchResult, Specialization


def test_database_hospitals_crud(db_session):
    """Test creating, reading, updating, and querying hospitals."""
    node = db_session.query(RoadNode).filter(RoadNode.node_id == "A").first()
    assert node is not None

    spec = db_session.query(Specialization).filter(Specialization.name == "Cardiology").first()
    assert spec is not None

    new_hosp = Hospital(
        name="Test Community Hospital",
        address="123 Test Way",
        node_id="A",
        beds_available=6,
        total_beds=20,
        contact_number="+91-1234567890",
        is_active=True
    )
    new_hosp.specializations.append(spec)
    db_session.add(new_hosp)
    db_session.commit()

    saved = db_session.query(Hospital).filter(Hospital.name == "Test Community Hospital").first()
    assert saved is not None
    assert saved.beds_available == 6
    assert saved.specializations[0].name == "Cardiology"

    # Update beds
    saved.beds_available = 10
    db_session.commit()
    assert db_session.query(Hospital).filter(Hospital.name == "Test Community Hospital").first().beds_available == 10


def test_database_ambulances_crud(db_session):
    """Test ambulance registration and status tracking."""
    amb = Ambulance(
        vehicle_number="MH-12-TEST-99",
        current_node="B",
        status="Available",
        driver_name="Test Driver",
        contact_number="+91-9988776655"
    )
    db_session.add(amb)
    db_session.commit()

    saved = db_session.query(Ambulance).filter(Ambulance.vehicle_number == "MH-12-TEST-99").first()
    assert saved is not None
    assert saved.status == "Available"

    # Update status to Dispatched
    saved.status = "Dispatched"
    db_session.commit()
    assert db_session.query(Ambulance).filter(Ambulance.vehicle_number == "MH-12-TEST-99").first().status == "Dispatched"


def test_emergency_request_dispatch_result_persistence(db_session):
    """Test full persistence of emergency request linked to dispatch recommendation result."""
    hosp = db_session.query(Hospital).first()
    amb = db_session.query(Ambulance).first()

    req = EmergencyRequest(
        patient_location_node="A",
        severity="High",
        required_specialization="Cardiology",
        caller_name="Caller One",
        caller_phone="+91-9900000000",
        status="Dispatched"
    )
    db_session.add(req)
    db_session.flush()

    disp = DispatchResult(
        request_id=req.request_id,
        recommended_hospital_id=hosp.hospital_id,
        assigned_ambulance_id=amb.ambulance_id,
        calculated_route='["A", "B", "D"]',
        total_distance_km=9.5,
        estimated_travel_time_minutes=13.0,
        suitability_score=91.2,
        selection_reasoning="Fastest high-capacity facility."
    )
    db_session.add(disp)
    db_session.commit()

    retrieved = db_session.query(EmergencyRequest).filter(EmergencyRequest.request_id == req.request_id).first()
    assert retrieved is not None
    assert retrieved.dispatch_result is not None
    assert retrieved.dispatch_result.total_distance_km == 9.5
    assert retrieved.dispatch_result.get_route_list() == ["A", "B", "D"]
