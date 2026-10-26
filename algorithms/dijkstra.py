"""
Dijkstra's Shortest Path and Traffic-Aware Routing Algorithm.
Calculates optimal routes over a weighted directed/undirected graph
constructed from database road network edges.
"""

import heapq
from typing import Dict, List, Tuple, Optional, Any


class RoadNetworkGraph:
    """
    Adjacency-list graph representation of the road network.
    Supports both static road distance and traffic-adjusted travel time optimization.
    """

    def __init__(self):
        # adj[u] = list of (v, distance_km, travel_time_minutes, traffic_level, status)
        self.adj: Dict[str, List[Dict[str, Any]]] = {}
        self.nodes: set = set()

    def add_node(self, node_id: str):
        self.nodes.add(str(node_id).upper())
        if str(node_id).upper() not in self.adj:
            self.adj[str(node_id).upper()] = []

    def add_edge(
        self,
        source: str,
        destination: str,
        distance_km: float,
        travel_time_minutes: float,
        traffic_level: str = "Low",
        is_bidirectional: bool = True,
        status: str = "Open"
    ):
        u = str(source).upper()
        v = str(destination).upper()
        self.add_node(u)
        self.add_node(v)

        edge_data = {
            "to": v,
            "distance_km": float(distance_km),
            "travel_time_minutes": float(travel_time_minutes),
            "traffic_level": traffic_level,
            "status": status
        }
        self.adj[u].append(edge_data)

        if is_bidirectional:
            rev_edge = {
                "to": u,
                "distance_km": float(distance_km),
                "travel_time_minutes": float(travel_time_minutes),
                "traffic_level": traffic_level,
                "status": status
            }
            self.adj[v].append(rev_edge)

    @classmethod
    def from_database_edges(cls, edges) -> "RoadNetworkGraph":
        """Build graph instance directly from SQLAlchemy RoadEdge query results."""
        graph = cls()
        for e in edges:
            if e.status != "Closed":  # Exclude closed roads from pathfinding
                graph.add_edge(
                    source=e.source_node,
                    destination=e.destination_node,
                    distance_km=e.distance_km,
                    travel_time_minutes=e.travel_time_minutes,
                    traffic_level=e.traffic_level,
                    is_bidirectional=e.is_bidirectional,
                    status=e.status
                )
        return graph

    def dijkstra(
        self,
        start_node: str,
        target_node: str,
        optimize_by: str = "travel_time"  # 'travel_time' or 'distance'
    ) -> Optional[Dict[str, Any]]:
        """
        Find shortest path from start_node to target_node using priority queue (min-heap).
        
        Args:
            start_node: Origin node ID (e.g. 'A')
            target_node: Destination node ID (e.g. 'D')
            optimize_by: Cost metric to minimize ('travel_time' or 'distance')

        Returns:
            Dict containing route, total_distance_km, total_travel_time_minutes, edge_steps
            or None if no path exists or nodes are invalid.
        """
        start = str(start_node).upper()
        target = str(target_node).upper()

        if start not in self.nodes or target not in self.nodes:
            return None

        if start == target:
            return {
                "route": [start],
                "total_distance_km": 0.0,
                "total_travel_time_minutes": 0.0,
                "average_traffic": "Low",
                "steps": []
            }

        # Min-heap stores: (cost, current_node, path_nodes, cumulative_dist, cumulative_time, steps)
        pq = [(0.0, start, [start], 0.0, 0.0, [])]
        best_cost = {node: float("inf") for node in self.nodes}
        best_cost[start] = 0.0

        while pq:
            current_cost, u, path, cum_dist, cum_time, steps = heapq.heappop(pq)

            if current_cost > best_cost[u]:
                continue

            if u == target:
                traffic_levels = [s["traffic_level"] for s in steps]
                high_count = traffic_levels.count("High")
                med_count = traffic_levels.count("Medium")
                avg_traffic = "High" if high_count > len(steps) / 2 else ("Medium" if med_count + high_count > 0 else "Low")

                return {
                    "route": path,
                    "total_distance_km": round(cum_dist, 2),
                    "total_travel_time_minutes": round(cum_time, 2),
                    "average_traffic": avg_traffic,
                    "steps": steps
                }

            for edge in self.adj.get(u, []):
                v = edge["to"]
                edge_cost = edge["travel_time_minutes"] if optimize_by == "travel_time" else edge["distance_km"]
                new_cost = current_cost + edge_cost

                if new_cost < best_cost[v]:
                    best_cost[v] = new_cost
                    step = {
                        "from": u,
                        "to": v,
                        "distance_km": edge["distance_km"],
                        "travel_time_minutes": edge["travel_time_minutes"],
                        "traffic_level": edge["traffic_level"]
                    }
                    heapq.heappush(
                        pq,
                        (
                            new_cost,
                            v,
                            path + [v],
                            cum_dist + edge["distance_km"],
                            cum_time + edge["travel_time_minutes"],
                            steps + [step]
                        )
                    )

        return None
