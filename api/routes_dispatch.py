"""
API routes for emergency dispatch request handling, hospital recommendation calculation,
and database persistence.
"""

import json
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from database import get_session
from models import Hospital, RoadEdge, Ambulance, EmergencyRequest, DispatchResult
from algorithms.dijkstra import RoadNetworkGraph
from algorithms.recommender import HospitalRecommendationEngine, map_emergency_to_specialization

dispatch_bp = Blueprint("dispatch", __name__)


def find_nearest_ambulance(road_graph: RoadNetworkGraph, patient_node: str, session) -> tuple:
    """Find the closest Available ambulance to the patient location node."""
    available_ambulances = session.query(Ambulance).filter(Ambulance.status == "Available").all()
    if not available_ambulances:
        return None, None, None

    best_amb = None
    best_time = float("inf")
    best_route = None

    for amb in available_ambulances:
        route_res = road_graph.dijkstra(amb.current_node, patient_node, optimize_by="travel_time")
        if route_res and route_res["total_travel_time_minutes"] < best_time:
            best_time = route_res["total_travel_time_minutes"]
            best_amb = amb
            best_route = route_res

    return best_amb, best_time, best_route


@dispatch_bp.route("/dispatch", methods=["POST", "OPTIONS"])
def evaluate_dispatch():
    """
    Evaluate hospital recommendations for an emergency:
    Input JSON: {
        "location": "A",
        "emergency_type": "Cardiac",
        "severity": "High",
        "caller_name": "...",
        "caller_phone": "..."
    }
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    data = request.get_json(silent=True) or {}
    location = str(data.get("location", "")).strip().upper()
    emergency_type = str(data.get("emergency_type", "")).strip()
    severity = str(data.get("severity", "Medium")).strip().capitalize()

    if not location:
        return jsonify({"success": False, "error": "Patient location node is required."}), 400
    if not emergency_type:
        return jsonify({"success": False, "error": "Emergency type is required."}), 400

    session = get_session()
    try:
        # Load road edges from SQL database
        edges = session.query(RoadEdge).filter(RoadEdge.status != "Closed").all()
        road_graph = RoadNetworkGraph.from_database_edges(edges)

        # Load active hospitals from SQL database
        hospitals = session.query(Hospital).filter(Hospital.is_active == True).all()

        # Execute recommendation engine
        engine = HospitalRecommendationEngine()
        result = engine.evaluate_candidates(
            hospitals=hospitals,
            road_graph=road_graph,
            patient_node=location,
            emergency_type=emergency_type,
            severity=severity
        )

        if not result.get("success"):
            return jsonify(result), 404

        # Find closest available ambulance
        nearest_amb, amb_time, amb_route = find_nearest_ambulance(road_graph, location, session)
        if nearest_amb:
            result["assigned_ambulance"] = {
                "ambulance_id": nearest_amb.ambulance_id,
                "vehicle_number": nearest_amb.vehicle_number,
                "current_node": nearest_amb.current_node,
                "driver_name": nearest_amb.driver_name,
                "eta_to_patient_minutes": amb_time,
                "route_to_patient": amb_route["route"] if amb_route else [nearest_amb.current_node, location]
            }
        else:
            result["assigned_ambulance"] = None

        return jsonify(result)
    finally:
        session.close()


@dispatch_bp.route("/dispatch/confirm", methods=["POST"])
def confirm_dispatch():
    """
    Save the confirmed emergency request and dispatch outcome to the SQL database.
    Updates assigned ambulance status to 'Dispatched'.
    """
    data = request.get_json(silent=True) or {}
    location = str(data.get("location", "")).strip().upper()
    emergency_type = str(data.get("emergency_type", "")).strip()
    severity = str(data.get("severity", "Medium")).strip().capitalize()
    recommended = data.get("recommended") or {}

    if not location or not recommended:
        return jsonify({"error": "Invalid confirmation payload. Location and recommendation required."}), 400

    hospital_id = recommended.get("hospital_id")
    if not hospital_id:
        return jsonify({"error": "Recommended hospital ID is required."}), 400

    session = get_session()
    try:
        # 1. Create EmergencyRequest record
        req_record = EmergencyRequest(
            patient_location_node=location,
            severity=severity,
            required_specialization=map_emergency_to_specialization(emergency_type),
            caller_name=str(data.get("caller_name", "Emergency Dispatch")).strip(),
            caller_phone=str(data.get("caller_phone", "")).strip(),
            status="Dispatched",
            request_timestamp=datetime.now(timezone.utc)
        )
        session.add(req_record)
        session.flush()

        # 2. Assign ambulance if available
        ambulance_id = None
        amb_data = data.get("assigned_ambulance")
        if amb_data and "ambulance_id" in amb_data:
            amb = session.query(Ambulance).filter(Ambulance.ambulance_id == amb_data["ambulance_id"]).first()
            if amb and amb.status == "Available":
                amb.status = "Dispatched"
                ambulance_id = amb.ambulance_id

        # 3. Create DispatchResult record
        route = recommended.get("route", [location, recommended.get("node_id", location)])
        alt_candidates = data.get("all_candidates", [])[1:5]  # Next 4 alternatives

        disp_record = DispatchResult(
            request_id=req_record.request_id,
            recommended_hospital_id=hospital_id,
            assigned_ambulance_id=ambulance_id,
            calculated_route=json.dumps(route),
            total_distance_km=float(recommended.get("distance_km", 0.0)),
            estimated_travel_time_minutes=float(recommended.get("travel_time_minutes", 0.0)),
            suitability_score=float(recommended.get("suitability_score", 0.0)),
            selection_reasoning=str(recommended.get("reasoning", "")),
            alternative_candidates=json.dumps(alt_candidates),
            created_at=datetime.now(timezone.utc)
        )
        session.add(disp_record)

        session.commit()

        return jsonify({
            "success": True,
            "request_id": req_record.request_id,
            "dispatch_id": disp_record.dispatch_id,
            "message": "Emergency dispatch confirmed and recorded in database.",
            "record": req_record.to_dict()
        }), 201
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()
