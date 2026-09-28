import heapq

# Road network graph (adjacency list)
graph = {
    "A": {"B": 4, "C": 2},
    "B": {"A": 4, "D": 5},
    "C": {"A": 2, "D": 8},
    "D": {"B": 5, "C": 8}
}

# Small sample data. The same rows can be shown in MySQL Workbench.
hospitals = [
    {"name": "City Care Hospital", "beds": 5, "specialization": "Cardiology", "node": "D"},
    {"name": "Sunrise Hospital", "beds": 0, "specialization": "Cardiology", "node": "B"},
    {"name": "General Care Hospital", "beds": 8, "specialization": "General", "node": "C"},
    {"name": "Bone and Joint Hospital", "beds": 3, "specialization": "Orthopaedics", "node": "B"}
]


def dijkstra(graph, start, end):
    """Find the shortest distance and route using a priority queue (min heap)."""
    queue = [(0, start, [start])]
    visited = []

    while queue:
        distance, current, path = heapq.heappop(queue)
        if current in visited:
            continue

        visited.append(current)
        if current == end:
            return distance, path

        for neighbour, weight in graph[current].items():
            if neighbour not in visited:
                heapq.heappush(queue, (distance + weight, neighbour, path + [neighbour]))

    return None, []


def get_specialization(emergency_type):
    if emergency_type.lower() == "cardiac":
        return "Cardiology"
    elif emergency_type.lower() == "orthopaedic":
        return "Orthopaedics"
    return "General"


def find_hospital(location, emergency_type):
    
    required_specialization = get_specialization(emergency_type)
    available_hospitals = []

    # Filter: hospital must have beds and the correct specialization.
    for hospital in hospitals:
        if hospital["beds"] > 0 and hospital["specialization"] == required_specialization:
            distance, route = dijkstra(graph, location, hospital["node"])
            hospital_copy = hospital.copy()
            hospital_copy["distance"] = distance
            hospital_copy["route"] = route
            available_hospitals.append(hospital_copy)

    if len(available_hospitals) == 0:
        return None

    # Simple score: 70% distance and 30% available beds.
    for hospital in available_hospitals:
        distance_score = 10 - hospital["distance"]
        bed_score = hospital["beds"]
        hospital["score"] = (0.7 * distance_score) + (0.3 * bed_score)

    available_hospitals.sort(key=lambda hospital: hospital["score"], reverse=True)
    return available_hospitals[0]


def main():
    print("---------------------------------------")
    print(" Emergency Ambulance Dispatch System")
    print("---------------------------------------")
    print("Available locations: A, B, C, D")

    location = input("Patient Location: ").upper()
    if location not in graph:
        print("Invalid location. Please enter A, B, C, or D.")
        return

    emergency_type = input("Emergency Type (Cardiac/Orthopaedic/General): ")
    severity = input("Severity (High/Medium/Low): ")
    recommended = find_hospital(location, emergency_type)

    if recommended is None:
        print("\nNo suitable hospital is available.")
        return

    # Assumption: one graph-distance unit takes approximately two minutes.
    eta = recommended["distance"] * 2
    print("\n---------------------------------------")
    print(" Recommended Hospital")
    print("---------------------------------------")
    print("Hospital:", recommended["name"])
    print("Beds Available:", recommended["beds"])
    print("Specialization:", recommended["specialization"])
    print("Severity:", severity)
    print("Route:", " -> ".join(recommended["route"]))
    print("Distance:", recommended["distance"], "km")
    print("Estimated Travel Time:", eta, "minutes")
    print("---------------------------------------")


main()
