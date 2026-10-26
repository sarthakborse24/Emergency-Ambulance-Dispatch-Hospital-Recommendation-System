from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_BREAK

OUT = "Emergency_Ambulance_Dispatch_and_Hospital_Recommendation_System_Final_Report.docx"

doc = Document()
sec = doc.sections[0]
sec.top_margin = Inches(0.8)
sec.bottom_margin = Inches(0.75)
sec.left_margin = Inches(0.85)
sec.right_margin = Inches(0.85)

styles = doc.styles
styles['Normal'].font.name = 'Aptos'
styles['Normal']._element.rPr.rFonts.set(qn('w:ascii'), 'Aptos')
styles['Normal']._element.rPr.rFonts.set(qn('w:hAnsi'), 'Aptos')
styles['Normal'].font.size = Pt(10.5)
styles['Normal'].paragraph_format.space_after = Pt(6)
styles['Normal'].paragraph_format.line_spacing = 1.15
for name, size in [('Title', 23), ('Heading 1', 15), ('Heading 2', 12), ('Heading 3', 11)]:
    st = styles[name]
    st.font.name = 'Aptos Display' if name == 'Title' else 'Aptos'
    st._element.rPr.rFonts.set(qn('w:ascii'), st.font.name)
    st._element.rPr.rFonts.set(qn('w:hAnsi'), st.font.name)
    st.font.size = Pt(size)
    st.font.color.rgb = RGBColor(0, 0, 0)
    st.font.bold = True
    st.paragraph_format.space_before = Pt(14 if name != 'Title' else 0)
    st.paragraph_format.space_after = Pt(6)

code_style = styles.add_style('Code Block', WD_STYLE_TYPE.PARAGRAPH)
code_style.font.name = 'Consolas'
code_style._element.rPr.rFonts.set(qn('w:ascii'), 'Consolas')
code_style.font.size = Pt(8)
code_style.paragraph_format.left_indent = Inches(.25)
code_style.paragraph_format.space_after = Pt(2)
code_style.paragraph_format.line_spacing = 1.0

def shade(cell, color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd'); shd.set(qn('w:fill'), color); tcPr.append(shd)

def set_cell_margins(cell, top=80, start=100, bottom=80, end=100):
    tc = cell._tc; tcPr = tc.get_or_add_tcPr(); tcMar = tcPr.first_child_found_in('w:tcMar')
    if tcMar is None:
        tcMar = OxmlElement('w:tcMar'); tcPr.append(tcMar)
    for m, v in [('top', top), ('start', start), ('bottom', bottom), ('end', end)]:
        node = tcMar.find(qn('w:' + m))
        if node is None: node = OxmlElement('w:' + m); tcMar.append(node)
        node.set(qn('w:w'), str(v)); node.set(qn('w:type'), 'dxa')

def set_repeat_table_header(row):
    trPr = row._tr.get_or_add_trPr(); tblHeader = OxmlElement('w:tblHeader'); tblHeader.set(qn('w:val'), 'true'); trPr.append(tblHeader)

def table(headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers)); t.alignment = WD_TABLE_ALIGNMENT.CENTER; t.style = 'Table Grid'
    set_repeat_table_header(t.rows[0])
    for j,h in enumerate(headers):
        c=t.rows[0].cells[j]; c.text=h; shade(c,'17365D'); set_cell_margins(c); c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
        for r in c.paragraphs[0].runs: r.font.bold=True; r.font.color.rgb=RGBColor(255,255,255); r.font.size=Pt(9)
    for i,row in enumerate(rows):
        cells=t.add_row().cells
        for j,val in enumerate(row):
            cells[j].text=str(val); set_cell_margins(cells[j]); cells[j].vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if i%2==1: shade(cells[j],'EEF3F8')
            for p in cells[j].paragraphs:
                p.paragraph_format.space_after=Pt(1)
                for r in p.runs: r.font.size=Pt(9)
    if widths:
        for row in t.rows:
            for j,w in enumerate(widths): row.cells[j].width=Inches(w)
    doc.add_paragraph().paragraph_format.space_after=Pt(3)
    return t

def p(text='', boldlead=None):
    para=doc.add_paragraph()
    if boldlead and text.startswith(boldlead):
        r=para.add_run(boldlead); r.bold=True; para.add_run(text[len(boldlead):])
    else: para.add_run(text)
    return para

def heading(text, level=1): return doc.add_heading(text, level=level)
def bullets(items):
    for x in items: doc.add_paragraph(x, style='List Bullet')
def pagebreak(): doc.add_page_break()

# Cover page
for _ in range(4): doc.add_paragraph()
q=doc.add_paragraph(); q.alignment=WD_ALIGN_PARAGRAPH.CENTER
r=q.add_run('PROJECT REPORT ON'); r.bold=True; r.font.size=Pt(13)
q=doc.add_paragraph(style='Title'); q.alignment=WD_ALIGN_PARAGRAPH.CENTER
q.add_run('Emergency Ambulance Dispatch and Hospital Recommendation System')
q=doc.add_paragraph(); q.alignment=WD_ALIGN_PARAGRAPH.CENTER
r=q.add_run('A decision support prototype for routing emergency patients to an appropriate available hospital'); r.italic=True; r.font.size=Pt(12)
for _ in range(4): doc.add_paragraph()
for line in ['Submitted in partial fulfillment of the requirements for the award of', '[Degree Name]', '', 'Submitted by', '[Student Name]  |  [Roll Number]', '', 'Under the guidance of', '[Guide Name]', '', '[Department Name]', '[College Name]', '[University Name]', 'Academic Year 2026 2027']:
    q=doc.add_paragraph(); q.alignment=WD_ALIGN_PARAGRAPH.CENTER; q.add_run(line)
pagebreak()

# Front matter
heading('Certificate',1)
p('This is to certify that the project report entitled Emergency Ambulance Dispatch and Hospital Recommendation System is a bona fide work carried out by [Student Name] under my supervision in partial fulfillment of the requirements for [Degree Name].')
p('\nDate: ____________                                      Guide Signature: ____________')
p('Place: ____________                                     Head of Department: ____________')
pagebreak()
heading('Declaration',1)
p('I hereby declare that this report is my original work. It has not been submitted, either in whole or in part, for the award of any other degree or diploma. All sources used in preparing this report have been acknowledged in the references section.')
p('\nStudent Signature: ____________                         Date: ____________')
pagebreak()
heading('Acknowledgement',1)
p('I express sincere gratitude to my project guide, department faculty, and institution for their guidance and support. I also thank my peers and family for their encouragement during the development of this project.')
pagebreak()
heading('Abstract',1)
p('Emergency care outcomes can be affected when an ambulance is sent to the geographically nearest hospital without verifying whether that hospital has an available bed or the clinical capability needed for the case. This project presents a small decision support prototype that recommends a hospital by combining shortest-path routing, bed availability, and emergency-specific specialization. The prototype models a road network as a weighted graph and applies Dijkstra’s algorithm to identify travel distance and route. Hospitals with zero available beds or an unsuitable specialization are excluded. The remaining candidates are ranked using a weighted score that favors shorter travel distance while also rewarding bed availability.')
p('The implemented console application accepts a patient location, emergency type, and severity, then displays the recommended hospital, available beds, specialization, route, distance, and an estimated travel time. The current implementation is intentionally compact: it uses a four-node sample graph and in-memory hospital records. It demonstrates the decision logic required for a larger dispatch platform. A production version can extend this base with GPS feeds, traffic APIs, hospital information systems, secure databases, clinician override, and audit logging.')
p('Keywords: emergency dispatch, hospital recommendation, Dijkstra algorithm, shortest path, bed availability, clinical specialization, decision support.')
pagebreak()
heading('Table of Contents',1)
toc = [
('Abstract','Front matter'),('Chapter 1 Introduction','Background, problem, objectives, scope'),('Chapter 2 System Study','Existing and proposed approaches'),('Chapter 3 Requirements and Design','Requirements, architecture, data design'),('Chapter 4 Methodology and Algorithms','Workflow, Dijkstra algorithm, ranking'),('Chapter 5 Implementation','Technology, modules, code logic'),('Chapter 6 Testing and Results','Test cases and sample results'),('Chapter 7 Conclusion and Future Work','Conclusion, enhancements, safety'),('References','Source list'),('Appendix A Source Code','Prototype source listing')]
table(['Section','Coverage'], toc, [2.45,4.05])
pagebreak()

heading('Chapter 1 Introduction',1)
heading('1.1 Background',2)
p('Emergency dispatch is a time-sensitive coordination problem. The closest facility may be unable to accept a patient because no bed is available, or it may not have the specialty needed for a cardiac, orthopaedic, or general emergency. A useful dispatch decision must therefore look beyond proximity. It should identify a medically suitable hospital, verify capacity, and estimate a feasible route.')
p('This project demonstrates this idea with a transparent rule-and-score-based prototype. The route layer is represented by a weighted graph. Each graph node is a location, and each edge weight represents a road distance. Hospital records carry the hospital name, available bed count, specialization, and graph node. The system filters infeasible hospitals before ranking the feasible choices.')
heading('1.2 Problem Statement',2)
p('Design an intelligent ambulance dispatch system that recommends a suitable hospital for an emergency based on distance, available bed capacity, and the type of emergency, instead of routing every patient blindly to the nearest hospital. The intended real-world evolution also considers live traffic conditions; the current prototype estimates travel time from static graph distance.')
heading('1.3 Objectives',2)
bullets(['Model a road network as a weighted graph and compute a shortest route from patient location to hospital.', 'Map the emergency type to a required hospital specialization.', 'Reject hospitals with no available beds or a non-matching specialization.', 'Rank eligible hospitals using distance and available beds.', 'Show a clear dispatch recommendation with route, distance, capacity, and estimated travel time.', 'Provide a small, understandable foundation for later integration with live operational data.'])
heading('1.4 Scope and Limitations',2)
table(['In scope','Not implemented in the prototype'], [
['Static road network with four locations','Live traffic congestion or road closures'],
['Cardiac, orthopaedic, and general classification','Clinical triage, diagnosis, or treatment advice'],
['In-memory hospital capacities and specialties','Real-time hospital information system synchronization'],
['Single best recommendation','Ambulance fleet tracking and dispatch assignment'],
['Console-based interaction','Authentication, user roles, mobile UI, and audit logging']], [3.1,3.4])
heading('1.5 Significance',2)
p('The project illustrates how operational constraints can be made explicit in an emergency-routing decision. Its main contribution is not a claim of medical autonomy; it is a transparent recommendation process that can help a dispatcher compare appropriate candidates. In a real deployment, a trained dispatcher and clinical protocols must remain responsible for the final decision.')
pagebreak()

heading('Chapter 2 System Study',1)
heading('2.1 Existing Approach',2)
p('A basic dispatch workflow often routes an ambulance to the nearest hospital. This is simple but incomplete. It can lead to diversions, delays, or transfers when the chosen facility lacks an open bed or the required specialization. Manual calls to hospitals can improve the decision but are slow and may rely on stale information.')
heading('2.2 Proposed System',2)
p('The proposed system accepts patient location, emergency type, and severity. It translates the emergency type into a specialization requirement, filters hospital records by availability and specialization, calculates routes to each eligible hospital, scores the candidates, and returns the best-ranked hospital. The severity value is displayed in the result in the current implementation; it is retained as a future input for priority-aware weights and dispatch escalation.')
table(['Aspect','Nearest hospital approach','Proposed prototype'], [
['Selection basis','Distance only','Distance, bed availability, and specialization'],
['Capacity check','Usually absent','Hospitals with zero beds are excluded'],
['Clinical fit','Usually absent','Emergency type is mapped to specialization'],
['Route computation','May be manual','Dijkstra shortest path on the graph'],
['Decision explanation','Limited','Route, distance, beds, and score inputs are visible']], [1.65,2.2,2.65])
heading('2.3 Feasibility Study',2)
heading('Technical Feasibility',3)
p('The prototype uses standard Python and the built-in heapq priority queue module. No external services are required for the demonstrated dataset. Dijkstra’s algorithm is well suited to a non-negative weighted road graph.')
heading('Operational Feasibility',3)
p('The console workflow is easy to demonstrate and explains why a particular hospital is recommended. A production deployment would require validation of incoming data, staff training, escalation procedures, and continuous data integration.')
heading('Economic Feasibility',3)
p('The prototype is low cost because it uses a small local dataset and open Python tooling. Operational rollout costs would be driven by mapping, traffic, healthcare-system integration, hosting, security, and support rather than the core algorithm.')
pagebreak()

heading('Chapter 3 Requirements and Design',1)
heading('3.1 Functional Requirements',2)
table(['ID','Requirement','Current behavior'], [
['FR1','Accept patient location','Validates A, B, C, or D'],
['FR2','Accept emergency category','Accepts Cardiac, Orthopaedic, or General'],
['FR3','Determine suitable specialty','Maps emergency category to hospital specialization'],
['FR4','Check capacity','Requires beds greater than zero'],
['FR5','Compute route','Uses Dijkstra shortest path'],
['FR6','Recommend hospital','Ranks eligible candidates by weighted score'],
['FR7','Display dispatch details','Shows hospital, beds, specialty, route, distance, ETA']], [0.55,2.55,3.4])
heading('3.2 Non Functional Requirements',2)
table(['Quality attribute','Expectation'], [
['Correctness','Recommendation must obey capacity and specialization filters before ranking.'],
['Usability','Input prompts and outcome text must be clear to a nontechnical operator.'],
['Performance','For the small graph, response is effectively immediate; larger graphs require efficient data structures.'],
['Maintainability','Hospital records and graph definitions should be easy to update or move into a database.'],
['Safety','The software should provide decision support and preserve human dispatcher control.'],
['Security for deployment','Protect patient information, restrict access, and log decisions without exposing sensitive data.']], [1.6,4.9])
heading('3.3 System Architecture',2)
p('The prototype follows a simple layered flow. The user interface collects inputs. The decision layer maps emergency type, filters hospitals, calculates routes, and ranks candidates. The data layer stores the road graph and hospital records. In a production system, the data layer would be replaced or supplemented by map, traffic, hospital-capacity, and ambulance-fleet services.')
table(['Layer','Component','Responsibility'], [
['Presentation','Console prompts','Collect location, emergency type, and severity; show recommendation.'],
['Decision','find_hospital','Filter, calculate, score, sort, and select a hospital.'],
['Routing','dijkstra','Calculate least-distance path over the road graph.'],
['Rules','get_specialization','Map emergency type to required clinical specialty.'],
['Data','graph and hospitals','Store road edges and sample hospital attributes.']], [1.1,1.7,3.7])
heading('3.4 Data Design',2)
table(['Entity','Field','Description','Example'], [
['Road edge','source, destination, weight','Connected locations and distance','A to C, 2'],
['Hospital','name','Facility name','City Care Hospital'],
['Hospital','beds','Currently available beds','5'],
['Hospital','specialization','Supported emergency category','Cardiology'],
['Hospital','node','Location in road graph','D'],
['Request','location','Patient location node','A'],
['Request','emergency type','Emergency category','Cardiac'],
['Request','severity','Operator-entered urgency','High']], [1.05,1.2,3.1,1.15])
pagebreak()

heading('Chapter 4 Methodology and Algorithms',1)
heading('4.1 Recommendation Workflow',2)
for i, x in enumerate(['Receive location, emergency type, and severity.', 'Map the emergency type to a required specialization.', 'Select hospitals with a matching specialization and beds greater than zero.', 'For each eligible hospital, run Dijkstra’s algorithm from the patient location to the hospital node.', 'Calculate a score from distance and bed availability.', 'Sort candidates in descending score order and return the first result.', 'Calculate the prototype ETA by multiplying graph distance by two minutes and display the recommendation.'], 1):
    p(f'{i}. {x}')
heading('4.2 Dijkstra Shortest Path Algorithm',2)
p('Dijkstra’s algorithm finds the lowest-total-weight path from a starting node to a target node when all edge weights are non-negative. The implementation uses a min-heap containing tuples of cumulative distance, current node, and route. A node is skipped if it has already been visited. When the target node is removed from the heap, the corresponding distance and route are returned.')
table(['Property','Prototype detail'], [
['Input','Weighted adjacency-list graph, start node, end node'],['Output','Shortest distance and ordered route'],['Priority structure','Python heapq min-heap'],['Assumption','All road weights are non-negative'],['Time complexity','O((V + E) log V) with a binary heap in the standard formulation']], [1.8,4.7])
heading('4.3 Ranking Model',2)
p('After the feasibility filter, each hospital is scored using the following prototype formula:')
q=doc.add_paragraph(); q.alignment=WD_ALIGN_PARAGRAPH.CENTER
r=q.add_run('Score = 0.7 x (10 - Distance) + 0.3 x Available Beds'); r.bold=True; r.font.size=Pt(12)
p('Distance receives a weight of 70 percent and available beds receive a weight of 30 percent. The term 10 - Distance makes smaller distances more desirable on the sample scale. This is appropriate only for the small controlled graph and should be normalized in a production system; otherwise negative distance scores or incomparable units can distort ranking.')
heading('4.4 Emergency Type Mapping',2)
table(['Emergency input','Required specialization','Prototype behavior'], [
['Cardiac','Cardiology','Considers only cardiology hospitals with beds.'],['Orthopaedic','Orthopaedics','Considers only orthopaedic hospitals with beds.'],['Any other input','General','Uses the general specialization fallback.']], [1.5,1.7,3.3])
heading('4.5 Future Traffic Aware Extension',2)
p('To incorporate live traffic, replace static edge distance with time-dependent travel cost. For example, each road edge can carry current travel time obtained from a routing service, with updates for congestion and closures. The objective can become expected time to definitive care rather than geographic distance alone. This extension requires data freshness checks and a policy for degraded operation when traffic data is unavailable.')
pagebreak()

heading('Chapter 5 Implementation',1)
heading('5.1 Technology Stack',2)
table(['Technology','Purpose'], [['Python 3','Application language'],['heapq','Priority queue used by Dijkstra routing'],['Dictionary and list structures','In-memory graph and hospital data'],['Command line interface','Input collection and result display']], [2.1,4.4])
heading('5.2 Module Description',2)
table(['Module','Description'], [
['graph','Adjacency-list dictionary for locations A, B, C, and D.'],
['hospitals','List of hospital dictionaries containing name, beds, specialization, and node.'],
['dijkstra','Returns shortest distance and path between two nodes.'],
['get_specialization','Converts emergency text into the matching specialization string.'],
['find_hospital','Filters hospitals, calculates route information, applies score, and selects the best result.'],
['main','Manages input validation and presentation of the result.']], [2.0,4.5])
heading('5.3 Core Logic',2)
for line in [
'required_specialization = get_specialization(emergency_type)',
'available_hospitals = []',
'for hospital in hospitals:',
'    if hospital["beds"] > 0 and hospital["specialization"] == required_specialization:',
'        distance, route = dijkstra(graph, location, hospital["node"])',
'        hospital_copy = hospital.copy()',
'        hospital_copy["distance"] = distance',
'        hospital_copy["route"] = route',
'        available_hospitals.append(hospital_copy)',
'',
'distance_score = 10 - hospital["distance"]',
'bed_score = hospital["beds"]',
'hospital["score"] = (0.7 * distance_score) + (0.3 * bed_score)']:
    doc.add_paragraph(line, style='Code Block')
heading('5.4 Input Validation and Error Handling',2)
p('The main function validates location input against the graph keys before computing a recommendation. When no hospital remains after filtering, the system returns None and displays “No suitable hospital is available.” This protects the user from receiving a recommendation that does not satisfy the implemented availability and specialization rules.')
heading('5.5 Implementation Notes',2)
bullets(['The current severity input is captured and displayed but does not change ranking.', 'Road distance is treated as kilometers in the output, and one graph-distance unit is assumed to equal approximately two minutes.', 'A copy of each hospital record is used before adding route, distance, and score fields, preserving the original sample data.', 'The code uses a visited list; a set would be preferable for larger graphs because membership tests are faster.'])
pagebreak()

heading('Chapter 6 Testing and Results',1)
heading('6.1 Test Strategy',2)
p('Testing focuses on validating the input guard, specialization mapping, capacity filter, route calculation, ranking behavior, and no-result path. The examples below are derived from the supplied sample graph and hospital data. They are functional demonstrations of the prototype, not measurements from a live ambulance operation.')
heading('6.2 Test Cases',2)
table(['ID','Input','Expected result','Observed logic'], [
['TC1','Location A; Cardiac; High','City Care Hospital is eligible; route A to B to D; distance 9','Pass: Sunrise is excluded because beds are 0.'],
['TC2','Location A; Orthopaedic; Medium','Bone and Joint Hospital; route A to B; distance 4','Pass: matching specialty and 3 available beds.'],
['TC3','Location A; General; Low','General Care Hospital; route A to C; distance 2','Pass: matching specialty and 8 available beds.'],
['TC4','Location X; Cardiac; High','Invalid location message','Pass: computation stops before routing.'],
['TC5','No eligible facility','No suitable hospital is available','Pass: returned when filtered list is empty.']], [0.45,1.45,2.55,2.0])
heading('6.3 Sample Result Interpretation',2)
p('For a cardiac emergency from node A, City Care Hospital at node D is the only eligible cardiology hospital because Sunrise Hospital has zero beds. Dijkstra’s algorithm returns A -> B -> D with a distance of 9. Based on the two-minutes-per-distance-unit assumption, the displayed estimated travel time is 18 minutes. The recommendation is therefore determined by feasibility first and ranking second.')
p('For an orthopaedic emergency from A, Bone and Joint Hospital at node B is selected via A -> B, distance 4, with an estimated travel time of 8 minutes. For a general emergency from A, General Care Hospital at node C is selected via A -> C, distance 2, with an estimated travel time of 4 minutes.')
heading('6.4 Validation Against Objectives',2)
table(['Objective','Evidence'], [
['Shortest route','dijkstra returns path and total graph distance.'],['Capacity awareness','Hospital is considered only when beds are greater than zero.'],['Specialization match','get_specialization and equality filter enforce matching category.'],['Recommendation','Eligible candidates are scored and sorted.'],['Clear output','main prints facility, route, distance, beds, specialization, severity, and ETA.']], [2.2,4.25])
heading('6.5 Known Limitations from Testing',2)
p('The score uses a fixed maximum-distance reference of 10 and does not normalize bed values. Consequently, it should not be applied unchanged to a larger map or a hospital network with widely different capacities. The application also does not validate emergency-type spelling, does not resolve ties explicitly, and does not test dynamic updates because its data is static.')
pagebreak()

heading('Chapter 7 Conclusion and Future Work',1)
heading('7.1 Conclusion',2)
p('The Emergency Ambulance Dispatch and Hospital Recommendation System demonstrates a practical decision-support pattern for emergency routing. Rather than selecting the nearest facility indiscriminately, it first applies hospital availability and specialization constraints, then calculates a shortest route and ranks feasible options. The supplied Python prototype successfully shows this workflow with a weighted graph, sample hospitals, Dijkstra’s algorithm, and a transparent score.')
p('The system is appropriate as an academic prototype because its behavior is easy to inspect and explain. It also highlights an important operational principle: distance alone is not sufficient when accepting capacity and clinical fit matter. Any deployment in real emergency services must use verified real-time data, clinical governance, safety testing, privacy controls, and human dispatch oversight.')
heading('7.2 Future Enhancements',2)
bullets(['Integrate GPS coordinates, geocoding, and a mapping service for real road topology.', 'Use live travel-time and closure data to optimize expected arrival time.', 'Connect to hospital bed-management systems with timestamps and freshness indicators.', 'Add ambulance availability, vehicle capability, crew status, and nearest-unit allocation.', 'Incorporate severity into a policy-controlled ranking model and escalation workflow.', 'Support multiple clinical specialties, trauma level, ICU capacity, equipment, and diversion status.', 'Move records to a database and provide web or mobile dashboards with role-based access.', 'Add audit logs, explainable recommendation details, and dispatcher override reasons.', 'Normalize score inputs and evaluate the model using historical, de-identified dispatch data.', 'Implement fail-safe behavior when external data sources are unavailable or inconsistent.'])
heading('7.3 Ethical and Safety Considerations',2)
p('This system should support, not replace, professional judgement. Recommendations should be explainable, overrideable, and based on validated data. Patient-identifying information must be minimized, protected in transit and at rest, and accessed only by authorized personnel. Before operational use, the system should undergo clinical review, usability testing, incident-response planning, and appropriate regulatory assessment.')
pagebreak()

heading('References',1)
refs = [
'E. W. Dijkstra, “A Note on Two Problems in Connexion with Graphs,” Numerische Mathematik, vol. 1, pp. 269–271, 1959.',
'Python Software Foundation, “heapq — Heap queue algorithm,” Python Documentation. Available: https://docs.python.org/3/library/heapq.html',
'Python Software Foundation, “Python 3 Documentation.” Available: https://docs.python.org/3/',
'World Health Organization, “Emergency care systems framework,” World Health Organization, 2019.',
'National Academies of Sciences, Engineering, and Medicine, The Future of Emergency Care. Washington, DC: The National Academies Press, 2007.'
]
for x in refs: doc.add_paragraph(x, style='List Number')
pagebreak()

heading('Appendix A Source Code',1)
p('The following is the source logic used by the prototype. Formatting is preserved for readability.')
code = '''import heapq

graph = {
    "A": {"B": 4, "C": 2},
    "B": {"A": 4, "D": 5},
    "C": {"A": 2, "D": 8},
    "D": {"B": 5, "C": 8}
}

hospitals = [
    {"name": "City Care Hospital", "beds": 5, "specialization": "Cardiology", "node": "D"},
    {"name": "Sunrise Hospital", "beds": 0, "specialization": "Cardiology", "node": "B"},
    {"name": "General Care Hospital", "beds": 8, "specialization": "General", "node": "C"},
    {"name": "Bone and Joint Hospital", "beds": 3, "specialization": "Orthopaedics", "node": "B"}
]

def dijkstra(graph, start, end):
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
    for hospital in hospitals:
        if hospital["beds"] > 0 and hospital["specialization"] == required_specialization:
            distance, route = dijkstra(graph, location, hospital["node"])
            hospital_copy = hospital.copy()
            hospital_copy["distance"] = distance
            hospital_copy["route"] = route
            available_hospitals.append(hospital_copy)
    if len(available_hospitals) == 0:
        return None
    for hospital in available_hospitals:
        distance_score = 10 - hospital["distance"]
        bed_score = hospital["beds"]
        hospital["score"] = (0.7 * distance_score) + (0.3 * bed_score)
    available_hospitals.sort(key=lambda hospital: hospital["score"], reverse=True)
    return available_hospitals[0]'''
for line in code.splitlines(): doc.add_paragraph(line, style='Code Block')

# Header/footer from chapter pages onward
for section in doc.sections:
    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    hr=header.add_run('Emergency Ambulance Dispatch and Hospital Recommendation System')
    hr.font.size=Pt(8); hr.font.color.rgb=RGBColor(90,90,90)
    footer=section.footer.paragraphs[0]
    footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
    fr=footer.add_run('Project Report')
    fr.font.size=Pt(8); fr.font.color.rgb=RGBColor(90,90,90)

doc.core_properties.title = 'Emergency Ambulance Dispatch and Hospital Recommendation System'
doc.core_properties.subject = 'Project report'
doc.core_properties.author = '[Student Name]'
doc.save(OUT)
print(OUT)
