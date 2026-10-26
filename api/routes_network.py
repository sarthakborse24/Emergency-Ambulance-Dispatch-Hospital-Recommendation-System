"""
API routes for road network topology, nodes, weighted traffic edges,
and point-to-point Dijkstra route calculation.
"""

from flask import Blueprint, jsonify, request
from database import get_session
from models import RoadNode, RoadEdge
from algorithms.dijkstra import RoadNetworkGraph

network_bp = Blueprint("network", __name__)


@network_bp.route("/network", methods=["GET"])
def get_road_network():
    """Retrieve all road network nodes and edges for visualization and routing."""
    session = get_session()
    try:
        nodes = session.query(RoadNode).order_by(RoadNode.node_id).all()
        edges = session.query(RoadEdge).order_by(RoadEdge.edge_id).all()

        nodes_list = [n.to_dict() for n in nodes]
        edges_list = [e.to_dict() for e in edges]

        # Adjacency map for fast client lookup
        adj = {n.node_id: {} for n in nodes}
        for e in edges:
            if e.status != "Closed":
                adj[e.source_node][e.destination_node] = {
                    "distance_km": e.distance_km,
                    "travel_time_minutes": e.travel_time_minutes,
                    "traffic_level": e.traffic_level
                }
                if e.is_bidirectional:
                    adj[e.destination_node][e.source_node] = {
                        "distance_km": e.distance_km,
                        "travel_time_minutes": e.travel_time_minutes,
                        "traffic_level": e.traffic_level
                    }

        return jsonify({
            "nodes": nodes_list,
            "edges": edges_list,
            "graph": adj
        })
    finally:
        session.close()


@network_bp.route("/nodes", methods=["GET"])
def list_nodes():
    """Retrieve lightweight list of road network nodes."""
    session = get_session()
    try:
        nodes = session.query(RoadNode).order_by(RoadNode.node_id).all()
        return jsonify({
            "nodes": [{"node_id": n.node_id, "name": n.name} for n in nodes]
        })
    finally:
        session.close()


@network_bp.route("/route", methods=["POST", "GET"])
def calculate_route():
    """
    Calculate the shortest / fastest Dijkstra route between any two arbitrary nodes in the road network.
    Accepts:
      POST JSON: { "start": "A", "target": "H", "optimize_by": "travel_time" }
      or GET Query: ?start=A&target=H&optimize_by=travel_time
    """
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        start = str(data.get("start", data.get("source", ""))).strip().upper()
        target = str(data.get("target", data.get("destination", ""))).strip().upper()
        optimize_by = str(data.get("optimize_by", "travel_time")).strip().lower()
    else:
        start = request.args.get("start", request.args.get("source", "")).strip().upper()
        target = request.args.get("target", request.args.get("destination", "")).strip().upper()
        optimize_by = request.args.get("optimize_by", "travel_time").strip().lower()

    if not start or not target:
        return jsonify({"error": "Both 'start' and 'target' node parameters are required."}), 400

    session = get_session()
    try:
        edges = session.query(RoadEdge).filter(RoadEdge.status != "Closed").all()
        road_graph = RoadNetworkGraph.from_database_edges(edges)

        if start not in road_graph.nodes:
            return jsonify({"error": f"Start node '{start}' does not exist in road network."}), 404
        if target not in road_graph.nodes:
            return jsonify({"error": f"Target node '{target}' does not exist in road network."}), 404

        route_res = road_graph.dijkstra(start, target, optimize_by=optimize_by)

        if not route_res:
            return jsonify({
                "success": False,
                "error": f"No accessible route exists between Node '{start}' and Node '{target}'."
            }), 404

        nodes_dict = {n.node_id: n.name for n in session.query(RoadNode).all()}
        route_res["success"] = True
        route_res["start_node"] = start
        route_res["target_node"] = target
        route_res["start_name"] = nodes_dict.get(start, f"Node {start}")
        route_res["target_name"] = nodes_dict.get(target, f"Node {target}")

        return jsonify(route_res)
    finally:
        session.close()
