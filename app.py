"""
MedRoute — Emergency Ambulance Dispatch & Hospital Recommendation System
Main Flask Application Entry Point.
Serves the unified emergency response dashboard, static assets, and REST API.
"""

import os
import sys
from datetime import datetime, timezone
from flask import Flask, jsonify, request, send_from_directory

from config import Config
from database import init_db, get_session
from api.routes_stats import stats_bp
from api.routes_hospitals import hospitals_bp
from api.routes_ambulances import ambulances_bp
from api.routes_network import network_bp
from api.routes_dispatch import dispatch_bp

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def create_app(config_class=Config):
    """Application factory for Flask application."""
    app = Flask(
        __name__,
        static_folder=BASE_DIR,
        static_url_path=""
    )
    app.config.from_object(config_class)

    # Initialize SQL database tables
    init_db(app.config["SQLALCHEMY_DATABASE_URI"])

    # Register API Blueprints
    app.register_blueprint(stats_bp, url_prefix="/api")
    app.register_blueprint(hospitals_bp, url_prefix="/api")
    app.register_blueprint(ambulances_bp, url_prefix="/api")
    app.register_blueprint(network_bp, url_prefix="/api")
    app.register_blueprint(dispatch_bp, url_prefix="/api")

    # Global CORS headers
    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        return response

    # Frontend Single Page Application routes
    @app.route("/", methods=["GET"])
    def index():
        return send_from_directory(BASE_DIR, "index.html")

    @app.route("/<path:filename>", methods=["GET"])
    def static_assets(filename):
        file_path = os.path.join(BASE_DIR, filename)
        if os.path.isfile(file_path):
            return send_from_directory(BASE_DIR, filename)
        return send_from_directory(BASE_DIR, "index.html")

    # Health check
    @app.route("/api/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "online",
            "service": "MedRoute Emergency Dispatch API",
            "database": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    return app


app = create_app()


def main_cli():
    """Interactive command-line interface for manual execution or testing."""
    from models import RoadEdge, Hospital
    from algorithms.dijkstra import RoadNetworkGraph
    from algorithms.recommender import HospitalRecommendationEngine

    session = get_session()
    try:
        edges = session.query(RoadEdge).filter(RoadEdge.status != "Closed").all()
        road_graph = RoadNetworkGraph.from_database_edges(edges)
        hospitals = session.query(Hospital).filter(Hospital.is_active == True).all()

        print("=" * 55)
        print(" Emergency Ambulance Dispatch & Recommendation (CLI)")
        print("=" * 55)
        print(f"Available Network Nodes: {', '.join(sorted(road_graph.nodes))}")

        location = input("Patient Location Node: ").strip().upper()
        if location not in road_graph.nodes:
            print(f"Error: Invalid location '{location}'. Available: {', '.join(sorted(road_graph.nodes))}")
            return

        emergency_type = input("Emergency Type (Cardiac/Trauma/Ortho/Neuro/General): ").strip()
        severity = input("Severity (High/Medium/Low): ").strip() or "Medium"

        engine = HospitalRecommendationEngine()
        result = engine.evaluate_candidates(
            hospitals=hospitals,
            road_graph=road_graph,
            patient_node=location,
            emergency_type=emergency_type,
            severity=severity
        )

        if not result.get("success"):
            print("\nRecommendation Result: " + result.get("message", "No hospital found."))
            for r in result.get("reasons", []):
                print(f" - {r}")
            return

        best = result["recommended"]
        print("\n" + "-" * 50)
        print(" Recommended Hospital Destination")
        print("-" * 50)
        print(f"Hospital Name       : {best['name']}")
        print(f"Location Node       : Node {best['node_id']}")
        print(f"Available Beds      : {best['beds_available']} / {best['total_beds']}")
        print(f"Specialization      : {best['specialization']}")
        print(f"Calculated Route    : {' -> '.join(best['route'])}")
        print(f"Distance            : {best['distance_km']} km")
        print(f"Estimated Travel ETA: {best['travel_time_minutes']} minutes")
        print(f"Suitability Score   : {best['suitability_score']} / 100")
        print(f"Rationale           : {best['reasoning']}")
        print("-" * 50)
    finally:
        session.close()


if __name__ == "__main__":
    if "--cli" in sys.argv:
        main_cli()
    else:
        port = int(os.environ.get("PORT", 5000))
        print("=" * 68)
        print(" MedRoute — Emergency Ambulance Dispatch & Recommendation System")
        print(f" Server active at: http://127.0.0.1:{port}")
        print(" API endpoints registered:")
        print(f"   • GET  http://127.0.0.1:{port}/api/health")
        print(f"   • GET  http://127.0.0.1:{port}/api/stats")
        print(f"   • GET  http://127.0.0.1:{port}/api/hospitals")
        print(f"   • GET  http://127.0.0.1:{port}/api/ambulances")
        print(f"   • GET  http://127.0.0.1:{port}/api/network")
        print(f"   • POST http://127.0.0.1:{port}/api/dispatch")
        print(f"   • POST http://127.0.0.1:{port}/api/dispatch/confirm")
        print(f"   • GET  http://127.0.0.1:{port}/api/history")
        print(" Web Dashboard:")
        print(f"   • Open http://127.0.0.1:{port}/ in your web browser")
        print("=" * 68)
        app.run(host="0.0.0.0", port=port, debug=False)
