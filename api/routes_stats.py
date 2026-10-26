"""
API routes for dashboard statistics and emergency dispatch history.
"""

from flask import Blueprint, jsonify, request
from sqlalchemy import desc, func
from database import get_session
from models import Hospital, Ambulance, EmergencyRequest, DispatchResult, RoadNode

stats_bp = Blueprint("stats", __name__)


@stats_bp.route("/stats", methods=["GET"])
def get_dashboard_stats():
    """Return aggregated real-time statistics from the SQL database."""
    session = get_session()
    try:
        total_hospitals = session.query(Hospital).filter(Hospital.is_active == True).count()
        total_beds = session.query(func.sum(Hospital.beds_available)).filter(Hospital.is_active == True).scalar() or 0
        total_ambulances = session.query(Ambulance).count()
        available_ambulances = session.query(Ambulance).filter(Ambulance.status == "Available").count()
        dispatched_ambulances = session.query(Ambulance).filter(Ambulance.status == "Dispatched").count()
        total_dispatches = session.query(EmergencyRequest).count()

        # 5 most recent dispatches
        recent = (
            session.query(EmergencyRequest)
            .order_by(desc(EmergencyRequest.request_timestamp))
            .limit(5)
            .all()
        )

        return jsonify({
            "total_hospitals": total_hospitals,
            "total_beds_available": int(total_beds),
            "total_ambulances": total_ambulances,
            "available_ambulances": available_ambulances,
            "dispatched_ambulances": dispatched_ambulances,
            "total_dispatches": total_dispatches,
            "recent_dispatches": [r.to_dict() for r in recent]
        })
    finally:
        session.close()


@stats_bp.route("/history", methods=["GET"])
def get_emergency_history():
    """Retrieve historical emergency requests and recommendation records with filtering."""
    session = get_session()
    try:
        search = request.args.get("search", "").strip().lower()
        severity = request.args.get("severity", "").strip()
        status = request.args.get("status", "").strip()
        spec = request.args.get("specialization", "").strip()

        query = session.query(EmergencyRequest).order_by(desc(EmergencyRequest.request_timestamp))

        if severity:
            query = query.filter(EmergencyRequest.severity.ilike(severity))
        if status:
            query = query.filter(EmergencyRequest.status.ilike(status))
        if spec:
            query = query.filter(EmergencyRequest.required_specialization.ilike(spec))

        records = query.all()

        results = []
        for r in records:
            d = r.to_dict()
            if search:
                # Search by patient node, hospital name, caller name or phone
                h_name = d.get("dispatch", {}).get("hospital_name", "") or ""
                matches = (
                    search in r.patient_location_node.lower() or
                    search in r.required_specialization.lower() or
                    search in h_name.lower() or
                    search in (r.caller_name or "").lower() or
                    search in (r.caller_phone or "").lower()
                )
                if not matches:
                    continue
            results.append(d)

        return jsonify({
            "total": len(results),
            "requests": results
        })
    finally:
        session.close()
