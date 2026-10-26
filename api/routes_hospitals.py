"""
API routes for hospital registry, capacity updates, and specialization management.
"""

from flask import Blueprint, jsonify, request
from database import get_session
from models import Hospital, Specialization, RoadNode

hospitals_bp = Blueprint("hospitals", __name__)


@hospitals_bp.route("/hospitals", methods=["GET"])
def list_hospitals():
    """Retrieve all hospitals, optionally filtered by active status."""
    session = get_session()
    try:
        active_only = request.args.get("active_only", "false").lower() == "true"
        query = session.query(Hospital)
        if active_only:
            query = query.filter(Hospital.is_active == True)

        hospitals = query.order_by(Hospital.hospital_id).all()
        return jsonify({
            "total": len(hospitals),
            "hospitals": [h.to_dict() for h in hospitals]
        })
    finally:
        session.close()


@hospitals_bp.route("/hospitals/<int:hospital_id>", methods=["GET"])
def get_hospital(hospital_id):
    """Retrieve single hospital by ID."""
    session = get_session()
    try:
        hospital = session.query(Hospital).filter(Hospital.hospital_id == hospital_id).first()
        if not hospital:
            return jsonify({"error": f"Hospital ID {hospital_id} not found."}), 404
        return jsonify(hospital.to_dict())
    finally:
        session.close()


@hospitals_bp.route("/hospitals", methods=["POST"])
def create_hospital():
    """Register a new hospital with validation."""
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    node_id = str(data.get("node_id", data.get("node", ""))).strip().upper()
    beds = data.get("beds_available", 0)
    total_beds = data.get("total_beds", max(int(beds), 20))
    specializations = data.get("specializations", [])

    if not name:
        return jsonify({"error": "Hospital name is required."}), 400
    if not node_id:
        return jsonify({"error": "Hospital road node ID is required."}), 400

    session = get_session()
    try:
        # Validate node exists
        node = session.query(RoadNode).filter(RoadNode.node_id == node_id).first()
        if not node:
            return jsonify({"error": f"Node '{node_id}' does not exist in road network."}), 400

        try:
            beds = max(0, int(beds))
            total_beds = max(beds, int(total_beds))
        except ValueError:
            return jsonify({"error": "Bed numbers must be valid integers."}), 400

        hospital = Hospital(
            name=name,
            address=data.get("address", ""),
            latitude=float(data["latitude"]) if data.get("latitude") is not None else node.latitude,
            longitude=float(data["longitude"]) if data.get("longitude") is not None else node.longitude,
            node_id=node_id,
            beds_available=beds,
            total_beds=total_beds,
            contact_number=data.get("contact_number", ""),
            is_active=bool(data.get("is_active", True))
        )

        # Attach specializations
        if isinstance(specializations, str):
            specializations = [s.strip() for s in specializations.split(",") if s.strip()]

        for spec_name in specializations:
            s_obj = session.query(Specialization).filter(Specialization.name.ilike(spec_name.strip())).first()
            if not s_obj:
                s_obj = Specialization(name=spec_name.strip())
                session.add(s_obj)
                session.flush()
            hospital.specializations.append(s_obj)

        if not hospital.specializations:
            gen_spec = session.query(Specialization).filter(Specialization.name == "General").first()
            if gen_spec:
                hospital.specializations.append(gen_spec)

        session.add(hospital)
        session.commit()
        return jsonify({"success": True, "hospital": hospital.to_dict()}), 201
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()


@hospitals_bp.route("/hospitals/<int:hospital_id>", methods=["PUT"])
def update_hospital(hospital_id):
    """Update details of an existing hospital."""
    data = request.get_json(silent=True) or {}
    session = get_session()
    try:
        hospital = session.query(Hospital).filter(Hospital.hospital_id == hospital_id).first()
        if not hospital:
            return jsonify({"error": f"Hospital ID {hospital_id} not found."}), 404

        if "name" in data and str(data["name"]).strip():
            hospital.name = str(data["name"]).strip()
        if "address" in data:
            hospital.address = str(data["address"]).strip()
        if "node_id" in data or "node" in data:
            new_node = str(data.get("node_id", data.get("node"))).strip().upper()
            node = session.query(RoadNode).filter(RoadNode.node_id == new_node).first()
            if not node:
                return jsonify({"error": f"Node '{new_node}' not found."}), 400
            hospital.node_id = new_node
        if "beds_available" in data:
            beds = max(0, int(data["beds_available"]))
            hospital.beds_available = beds
            if beds > hospital.total_beds:
                hospital.total_beds = beds
        if "total_beds" in data:
            hospital.total_beds = max(hospital.beds_available, int(data["total_beds"]))
        if "contact_number" in data:
            hospital.contact_number = str(data["contact_number"]).strip()
        if "is_active" in data:
            hospital.is_active = bool(data["is_active"])
        if "latitude" in data and data["latitude"] is not None:
            hospital.latitude = float(data["latitude"])
        if "longitude" in data and data["longitude"] is not None:
            hospital.longitude = float(data["longitude"])

        if "specializations" in data:
            specs = data["specializations"]
            if isinstance(specs, str):
                specs = [s.strip() for s in specs.split(",") if s.strip()]
            hospital.specializations.clear()
            for spec_name in specs:
                s_obj = session.query(Specialization).filter(Specialization.name.ilike(spec_name.strip())).first()
                if not s_obj:
                    s_obj = Specialization(name=spec_name.strip())
                    session.add(s_obj)
                    session.flush()
                hospital.specializations.append(s_obj)

        session.commit()
        return jsonify({"success": True, "hospital": hospital.to_dict()})
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()


@hospitals_bp.route("/hospitals/<int:hospital_id>/beds", methods=["PATCH"])
def update_hospital_beds(hospital_id):
    """Quick update for bed availability."""
    data = request.get_json(silent=True) or {}
    if "beds_available" not in data:
        return jsonify({"error": "'beds_available' field is required."}), 400

    session = get_session()
    try:
        hospital = session.query(Hospital).filter(Hospital.hospital_id == hospital_id).first()
        if not hospital:
            return jsonify({"error": f"Hospital ID {hospital_id} not found."}), 404

        beds = max(0, int(data["beds_available"]))
        hospital.beds_available = beds
        if beds > hospital.total_beds:
            hospital.total_beds = beds

        session.commit()
        return jsonify({
            "success": True,
            "hospital_id": hospital_id,
            "beds_available": hospital.beds_available,
            "total_beds": hospital.total_beds
        })
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()


@hospitals_bp.route("/hospitals/<int:hospital_id>", methods=["DELETE"])
def delete_hospital(hospital_id):
    """Toggle hospital active status or delete."""
    session = get_session()
    try:
        hospital = session.query(Hospital).filter(Hospital.hospital_id == hospital_id).first()
        if not hospital:
            return jsonify({"error": f"Hospital ID {hospital_id} not found."}), 404

        # Toggle or deactivate
        hospital.is_active = not hospital.is_active
        session.commit()
        return jsonify({
            "success": True,
            "hospital_id": hospital_id,
            "is_active": hospital.is_active,
            "message": f"Hospital '{hospital.name}' active status set to {hospital.is_active}."
        })
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()


@hospitals_bp.route("/specializations", methods=["GET"])
def list_specializations():
    """Retrieve all distinct medical specializations."""
    session = get_session()
    try:
        specs = session.query(Specialization).order_by(Specialization.name).all()
        return jsonify({
            "specializations": [s.to_dict() for s in specs]
        })
    finally:
        session.close()
