"""
API routes for ambulance fleet management, location tracking, and status updates.
"""

from flask import Blueprint, jsonify, request
from database import get_session
from models import Ambulance, RoadNode

ambulances_bp = Blueprint("ambulances", __name__)


@ambulances_bp.route("/ambulances", methods=["GET"])
def list_ambulances():
    """Retrieve all registered ambulances in the fleet."""
    session = get_session()
    try:
        ambulances = session.query(Ambulance).order_by(Ambulance.ambulance_id).all()
        return jsonify({
            "total": len(ambulances),
            "ambulances": [a.to_dict() for a in ambulances]
        })
    finally:
        session.close()


@ambulances_bp.route("/ambulances/<int:ambulance_id>", methods=["GET"])
def get_ambulance(ambulance_id):
    """Retrieve details for a specific ambulance."""
    session = get_session()
    try:
        ambulance = session.query(Ambulance).filter(Ambulance.ambulance_id == ambulance_id).first()
        if not ambulance:
            return jsonify({"error": f"Ambulance ID {ambulance_id} not found."}), 404
        return jsonify(ambulance.to_dict())
    finally:
        session.close()


@ambulances_bp.route("/ambulances", methods=["POST"])
def create_ambulance():
    """Register a new ambulance unit into the fleet."""
    data = request.get_json(silent=True) or {}
    vehicle_number = str(data.get("vehicle_number", "")).strip().upper()
    current_node = str(data.get("current_node", data.get("node", ""))).strip().upper()
    status = str(data.get("status", "Available")).capitalize()

    if not vehicle_number:
        return jsonify({"error": "Vehicle number is required."}), 400
    if not current_node:
        return jsonify({"error": "Current station/node is required."}), 400

    session = get_session()
    try:
        # Check node exists
        node = session.query(RoadNode).filter(RoadNode.node_id == current_node).first()
        if not node:
            return jsonify({"error": f"Node '{current_node}' does not exist in road network."}), 400

        # Check vehicle number uniqueness
        existing = session.query(Ambulance).filter(Ambulance.vehicle_number == vehicle_number).first()
        if existing:
            return jsonify({"error": f"Ambulance '{vehicle_number}' is already registered."}), 400

        ambulance = Ambulance(
            vehicle_number=vehicle_number,
            current_node=current_node,
            latitude=float(data["latitude"]) if data.get("latitude") is not None else node.latitude,
            longitude=float(data["longitude"]) if data.get("longitude") is not None else node.longitude,
            status=status if status in ["Available", "Dispatched", "Maintenance", "Unavailable"] else "Available",
            driver_name=str(data.get("driver_name", "")).strip(),
            contact_number=str(data.get("contact_number", "")).strip()
        )
        session.add(ambulance)
        session.commit()
        return jsonify({"success": True, "ambulance": ambulance.to_dict()}), 201
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()


@ambulances_bp.route("/ambulances/<int:ambulance_id>", methods=["PUT"])
def update_ambulance(ambulance_id):
    """Update details of an existing ambulance."""
    data = request.get_json(silent=True) or {}
    session = get_session()
    try:
        ambulance = session.query(Ambulance).filter(Ambulance.ambulance_id == ambulance_id).first()
        if not ambulance:
            return jsonify({"error": f"Ambulance ID {ambulance_id} not found."}), 404

        if "vehicle_number" in data and str(data["vehicle_number"]).strip():
            ambulance.vehicle_number = str(data["vehicle_number"]).strip().upper()
        if "current_node" in data or "node" in data:
            new_node = str(data.get("current_node", data.get("node"))).strip().upper()
            node = session.query(RoadNode).filter(RoadNode.node_id == new_node).first()
            if not node:
                return jsonify({"error": f"Node '{new_node}' not found."}), 400
            ambulance.current_node = new_node
        if "status" in data:
            st = str(data["status"]).capitalize()
            if st in ["Available", "Dispatched", "Maintenance", "Unavailable"]:
                ambulance.status = st
        if "driver_name" in data:
            ambulance.driver_name = str(data["driver_name"]).strip()
        if "contact_number" in data:
            ambulance.contact_number = str(data["contact_number"]).strip()

        session.commit()
        return jsonify({"success": True, "ambulance": ambulance.to_dict()})
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()


@ambulances_bp.route("/ambulances/<int:ambulance_id>/status", methods=["PATCH"])
def update_ambulance_status(ambulance_id):
    """Quick status update for an ambulance (Available, Dispatched, Maintenance)."""
    data = request.get_json(silent=True) or {}
    status = str(data.get("status", "")).capitalize()
    if status not in ["Available", "Dispatched", "Maintenance", "Unavailable"]:
        return jsonify({"error": "Invalid status. Allowed: Available, Dispatched, Maintenance, Unavailable."}), 400

    session = get_session()
    try:
        ambulance = session.query(Ambulance).filter(Ambulance.ambulance_id == ambulance_id).first()
        if not ambulance:
            return jsonify({"error": f"Ambulance ID {ambulance_id} not found."}), 404

        ambulance.status = status
        session.commit()
        return jsonify({"success": True, "ambulance_id": ambulance_id, "status": ambulance.status})
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()
