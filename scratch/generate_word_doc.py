import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn
import os

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def create_document():
    doc = Document()

    # Page Margins
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # Styles
    styles = doc.styles
    normal_style = styles['Normal']
    normal_font = normal_style.font
    normal_font.name = 'Segoe UI'
    normal_font.size = Pt(10.5)
    normal_font.color.rgb = RGBColor(0x1F, 0x29, 0x37) # Slate Dark

    # Colors
    PRIMARY_COLOR = RGBColor(0x0F, 0x17, 0x2A)   # Dark Navy
    SECONDARY_COLOR = RGBColor(0x02, 0x84, 0xC7) # Bright Cyan/Blue
    ACCENT_GREEN = RGBColor(0x05, 0x96, 0x69)    # Emerald Green
    ACCENT_AMBER = RGBColor(0xD9, 0x77, 0x06)    # Amber Gold
    ACCENT_RED = RGBColor(0xDC, 0x26, 0x26)      # Crimson Red

    # Helper Functions
    def add_title(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(text)
        run.font.size = Pt(24)
        run.font.bold = True
        run.font.color.rgb = PRIMARY_COLOR

    def add_subtitle(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(20)
        run = p.add_run(text)
        run.font.size = Pt(13)
        run.font.italic = True
        run.font.color.rgb = RGBColor(0x4B, 0x55, 0x63)

    def add_h1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(18)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.size = Pt(16)
        run.font.bold = True
        run.font.color.rgb = PRIMARY_COLOR

    def add_h2(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.size = Pt(13)
        run.font.bold = True
        run.font.color.rgb = SECONDARY_COLOR

    def add_h3(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.size = Pt(11.5)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0x37, 0x41, 0x51)

    def add_body(text, bold_prefix="", italic_prefix=""):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            r_bold = p.add_run(bold_prefix)
            r_bold.font.bold = True
            r_bold.font.color.rgb = PRIMARY_COLOR
        if italic_prefix:
            r_it = p.add_run(italic_prefix)
            r_it.font.italic = True
        p.add_run(text)
        return p

    def add_bullet(text, bold_prefix=""):
        p = doc.add_paragraph(style='List Bullet')
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            r_bold = p.add_run(bold_prefix)
            r_bold.font.bold = True
            r_bold.font.color.rgb = PRIMARY_COLOR
        p.add_run(text)
        return p

    def add_callout(text, title="KEY TAKEAWAY", border_hex="0284C7", bg_hex="F0F9FF"):
        tbl = doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = tbl.cell(0, 0)
        cell.width = Inches(6.5)
        set_cell_background(cell, bg_hex)
        set_cell_margins(cell, top=120, bottom=120, left=180, right=180)
        
        tcPr = cell._tc.get_or_add_tcPr()
        borders = parse_xml(f'''
            <w:tcBorders {nsdecls("w")}>
                <w:top w:val="none"/>
                <w:left w:val="single" w:sz="36" w:space="0" w:color="{border_hex}"/>
                <w:bottom w:val="none"/>
                <w:right w:val="none"/>
            </w:tcBorders>
        ''')
        tcPr.append(borders)

        cp = cell.paragraphs[0]
        cp.paragraph_format.space_after = Pt(2)
        r_title = cp.add_run(f"📌 {title}: ")
        r_title.font.bold = True
        r_title.font.size = Pt(10)
        r_title.font.color.rgb = PRIMARY_COLOR

        r_text = cp.add_run(text)
        r_text.font.size = Pt(10)
        
        # Spacer
        sp = doc.add_paragraph()
        sp.paragraph_format.space_after = Pt(4)

    # -------------------------------------------------------------
    # DOCUMENT COVER & HEADER
    # -------------------------------------------------------------
    add_title("OrbitGuard: Comprehensive Technical Architecture & Mission Manual")
    add_subtitle("Real-Time Satellite Telemetry Anomaly Detection, Dynamic Graph Root Cause Isolation (RCA), and Autonomous FDIR Mission Control")

    add_callout(
        "This technical document provides a comprehensive, concept-by-concept breakdown of the OrbitGuard aerospace system. It covers the underlying mathematics, dataset schemas, feature extraction pipelines, graph neural network algorithms, telemetry streaming engines, and a complete section-by-section walkthrough of the Frontend Mission Control Console.",
        title="DOCUMENT SCOPE & PURPOSE",
        border_hex="059669",
        bg_hex="F0FDF4"
    )

    # -------------------------------------------------------------
    # SECTION 1: EXECUTIVE OVERVIEW
    # -------------------------------------------------------------
    add_h1("1. Executive Summary & Aerospace Background")
    
    add_body("Modern low-Earth orbit (LEO) satellite missions, such as the European Space Agency's (ESA) OPS-SAT CubeSat, operate in dynamic, high-radiation space environments where hardware perturbations, attitude tumbling, sensor calibration drift, and solar array degradation frequently occur. Ground stations historically relied on out-of-limit (OOL) threshold monitoring (e.g., checking if voltage > 5V), which fails to detect subtle, cross-sensor anomaly patterns where individual values remain within bounds but their dynamic physical relationships deviate.")
    
    add_body("OrbitGuard is an end-to-end intelligent aerospace telemetry platform designed to solve three critical mission challenges:")
    add_bullet(" Streams 9 mission-critical flight telemetry sensors synchronously across the Attitude Determination and Control Subsystem (ADCS) and Electrical Power Subsystem (EPS) at 10 Hz.", "1. Real-Time Multi-Channel Telemetry Processing:")
    add_bullet(" Uses rolling-window mathematical feature extraction and Graph Neural Networks (GNNs) with dynamic cross-correlation adjacency matrices to capture multi-sensor coupling.", "2. Spatiotemporal Anomaly Detection:")
    add_bullet(" Unlike black-box models that merely raise a binary alarm, OrbitGuard pinpoints the exact 'Patient Zero' root cause sensor, illustrates fault propagation across physical links, and suggests official ESA Fault Detection, Isolation, and Recovery (FDIR) operational commands with a technician resolution queue.", "3. Root Cause Isolation & FDIR Remediation:")

    # -------------------------------------------------------------
    # SECTION 2: DATASET ARCHITECTURE
    # -------------------------------------------------------------
    add_h1("2. Telemetry Architecture & Dataset Deep Dive")
    add_body("The OrbitGuard platform is grounded in real flight telemetry recorded from ESA's OPS-SAT spacecraft during orbital operations at an altitude of approximately 510 km.")

    add_h2("2.1 Raw Telemetry Stream (dataset.csv)")
    add_body("The raw dataset contains 303,495 chronological telemetry samples recorded across 9 distinct sensor telemetry identifiers (CADC channels).")

    # Table of Channels
    tbl_ch = doc.add_table(rows=1, cols=4)
    tbl_ch.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers = ["Channel ID", "Sensor Name", "Spacecraft Subsystem", "Physical Unit & Description"]
    for i, h in enumerate(headers):
        cell = tbl_ch.cell(0, i)
        set_cell_background(cell, "0F172A")
        p = cell.paragraphs[0]
        r = p.add_run(h)
        r.font.bold = True
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        r.font.size = Pt(9.5)

    channels_info = [
        ("CADC0872", "Magnetometer X-Axis", "ADCS (Attitude Control)", "Tesla (T) - Primary magnetic field vector on X-axis"),
        ("CADC0873", "Magnetometer Y-Axis", "ADCS (Attitude Control)", "Tesla (T) - Primary magnetic field vector on Y-axis"),
        ("CADC0874", "Magnetometer Z-Axis", "ADCS (Attitude Control)", "Tesla (T) - Primary magnetic field vector on Z-axis"),
        ("CADC0884", "Photodiode Sensor 1", "EPS (Solar Array/Sun Sensor)", "Volts (V) - Solar array illuminated surface angle 1"),
        ("CADC0886", "Photodiode Sensor 2", "EPS (Solar Array/Sun Sensor)", "Volts (V) - Solar array illuminated surface angle 2"),
        ("CADC0888", "Photodiode Sensor 3", "EPS (Solar Array/Sun Sensor)", "Volts (V) - Central solar array optical flux sensor"),
        ("CADC0890", "Photodiode Sensor 4", "EPS (Solar Array/Sun Sensor)", "Volts (V) - Solar array illuminated surface angle 4"),
        ("CADC0892", "Photodiode Sensor 5", "EPS (Solar Array/Sun Sensor)", "Volts (V) - Solar array illuminated surface angle 5"),
        ("CADC0894", "Photodiode Sensor 6", "EPS (Solar Array/Sun Sensor)", "Volts (V) - Nadir/Auxiliary solar panel optical sensor")
    ]

    for ch_id, s_name, sub, desc in channels_info:
        row = tbl_ch.add_row()
        data = [ch_id, s_name, sub, desc]
        for i, val in enumerate(data):
            cell = row.cells[i]
            set_cell_background(cell, "F8FAFC" if row._tr.getparent().index(row._tr) % 2 == 0 else "FFFFFF")
            set_cell_margins(cell, top=60, bottom=60, left=100, right=100)
            p = cell.paragraphs[0]
            r = p.add_run(val)
            r.font.size = Pt(9)
            if i == 0:
                r.font.bold = True
                r.font.color.rgb = SECONDARY_COLOR

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    add_h2("2.2 Segment Extraction & The 19 Rolling Features (segments.csv)")
    add_body("Telemetry values in space are highly autocorrelated over time. Feeding single raw floating-point numbers into machine learning models ignores sequence context. OrbitGuard slices continuous telemetry into sliding windows and extracts 19 statistical and signal processing features:")
    
    add_bullet(" The arithmetic mean of telemetry readings in the rolling buffer. Identifies baseline operating shifts.", "1. Buffer Mean (Mean):")
    add_bullet(" Measures the spread of data points around the mean. Spikes indicate signal volatility.", "2. Standard Deviation (Std):")
    add_bullet(" The square of standard deviation, quantifying signal power dispersion.", "3. Variance:")
    add_bullet(" Measures asymmetry in the telemetry distribution. Positive or negative skew indicates directional signal drift.", "4. Skewness:")
    add_bullet(" Measures the 'tailedness' or sharpness of the distribution peak. High kurtosis detects heavy-tailed transient outlier spikes.", "5. Kurtosis:")
    add_bullet(" The absolute minimum and maximum values within the time segment.", "6 & 7. Minimum & Maximum:")
    add_bullet(" Total excursion dynamic range between peak high and valley low.", "8. Peak-to-Peak Amplitude:")
    add_bullet(" Sum of squared values normalized by window length, representing total electrical/magnetic energy.", "9. Signal Energy:")
    add_bullet(" Frequency at which telemetry crosses the mean baseline. Higher rates indicate high-frequency noise or oscillation.", "10. Zero-Crossing Rate:")
    add_bullet(" Mean and variance of first-order discrete differences (dx/dt), measuring rate-of-change velocity and acceleration.", "11 & 12. First-Difference Statistics:")
    add_bullet(" The 25th, 50th (median), and 75th percentiles of signal amplitude.", "13, 14, 15. Quantile Distributions (Q25, Q50, Q75):")
    add_bullet(" Difference between Q75 and Q25, robustly measuring core signal spread independent of outliers.", "16. Interquartile Range (IQR):")
    add_bullet(" Ratio of peak amplitude to the RMS value, detecting sudden sharp shock spikes.", "17. Crest Factor:")
    add_bullet(" Ratio of RMS value to the mean absolute value, characterizing signal waveform profile.", "18. Shape Factor:")
    add_bullet(" Normalized inter-channel Pearson correlation coefficient against coupled sister channels.", "19. Coupling Correlation Coefficient:")

    # -------------------------------------------------------------
    # SECTION 3: AI ARCHITECTURE & GNN
    # -------------------------------------------------------------
    add_h1("3. Artificial Intelligence & Dynamic Graph Formulation")
    
    add_h2("3.1 The Multi-Sensor Coupling Problem (Why Traditional ML Fails)")
    add_body("Traditional machine learning evaluates each sensor in a vacuum ('siloed models'). However, on a spacecraft:")
    add_bullet("If the satellite experiences an attitude tumble, Magnetometer X, Y, and Z will simultaneously undergo phase shifts, while Photodiodes 1-6 will see rotating sunlight angles.", "Physical Attitude Coupling:")
    add_bullet("If a solar array regulator fails, the Photodiode readings collapse, while magnetometers remain unaffected.", "Physical Power Isolation:")
    add_body("A simple model cannot distinguish between a legitimate attitude maneuver and a single failed sensor. OrbitGuard resolves this using Dynamic Graph Neural Networks.")

    add_h2("3.2 Dynamic Graph Anomaly Detector (ai/graph_model/)")
    add_body("OrbitGuard represents the 9 sensors as a dynamic attributed graph G(t) = (V, E(t), X(t)):")
    add_bullet(" The 9 spacecraft sensors (3 ADCS Magnetometers + 6 EPS Photodiodes).", "• Node Set V:")
    add_bullet(" Dynamic adjacency matrix where edge weights represent rolling Pearson correlation coefficients between sensor pairs: A_ij(t) = Corr(s_i, s_j).", "• Dynamic Edge Matrix E(t):")
    add_bullet(" The 19-dimensional mathematical feature vectors extracted from each sensor.", "• Node Feature Matrix X(t):")

    add_body("The model operates in two stages:")
    add_bullet(" Multi-layer graph convolutional layers perform spatial message passing across coupled sensors, aggregating neighbor representations according to the correlation adjacency matrix.", "1. Spatial Message Passing:")
    add_bullet(" A Gated Recurrent Unit (GRU) layer processes the sequence of graph embeddings across sliding time windows, capturing temporal degradation patterns.", "2. Temporal Recurrent Aggregation:")
    add_bullet(" The model outputs a global anomaly probability score P(Anomaly) and per-node anomaly attribution scores identifying which node contributed most heavily to the graph-level loss.", "3. Multi-Task Output:")

    add_h2("3.3 The Streaming Window Reality Gap (ai/investigations/findings.py)")
    add_body("A critical scientific finding documented in the project repository is the 'Streaming Window Reality Gap'. During offline training, models have access to pre-sliced, fully populated window segments. In real-time streaming operations, as new telemetry arrives:")
    add_bullet("Early Buffer (< 10 samples): ~81.4% Detection Accuracy (due to incomplete statistical variance estimation).")
    add_bullet("Half Buffer (10-25 samples): ~91.2% Detection Accuracy.")
    add_bullet("Full Rolling Buffer (40+ samples): ~98.6% Detection Accuracy.")
    add_body("OrbitGuard incorporates a calibrated rolling window buffer that ensures maximum detection fidelity while streaming live data.")

    # -------------------------------------------------------------
    # SECTION 4: ROOT CAUSE & FDIR
    # -------------------------------------------------------------
    add_h1("4. Autonomous Root Cause Isolation (RCA) & FDIR Framework")
    add_body("When an anomaly is detected, OrbitGuard immediately runs the Root Cause Isolation algorithm:")
    
    add_bullet(" The sensor node exhibiting the highest reconstruction residual and deviation from baseline nominal correlation.", "1. Patient Zero Identification:")
    add_bullet(" Tracing dynamic graph edges to identify which secondary sensors were pulled off-nominal by the root fault.", "2. Propagation Radius Tracing:")
    add_bullet(" Translates the fault into official ESA OPS-SAT aerospace remediation procedures:", "3. Actionable FDIR Recovery Mapping:")

    # Table of FDIR Procedures
    tbl_fdir = doc.add_table(rows=1, cols=3)
    tbl_fdir.alignment = WD_TABLE_ALIGNMENT.CENTER
    fdir_headers = ["Subsystem & Root Sensor", "Detected Spacecraft Failure Pattern", "Recommended FDIR Recovery Action"]
    for i, h in enumerate(fdir_headers):
        cell = tbl_fdir.cell(0, i)
        set_cell_background(cell, "0F172A")
        p = cell.paragraphs[0]
        r = p.add_run(h)
        r.font.bold = True
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        r.font.size = Pt(9.5)

    fdir_data = [
        ("ADCS (CADC0872–0874: Magnetometers)", "Magnetic Dipole Inversion / Attitude Axis Drift", "Execute ADCS Stabilization: Re-calibrate magnetometer bias, engage reaction wheel torque damping, and recalculate B-dot reference vector."),
        ("EPS (CADC0884–0894: Photodiodes)", "Solar Array Shadowing / Photodiode Discrepancy", "Execute EPS Safe-Mode: Verify solar panel sun-tracking orientation vector, check power bus regulation, and reset optical photodiode bus.")
    ]

    for sub, pat, act in fdir_data:
        row = tbl_fdir.add_row()
        for i, val in enumerate([sub, pat, act]):
            cell = row.cells[i]
            set_cell_background(cell, "F8FAFC" if row._tr.getparent().index(row._tr) % 2 == 0 else "FFFFFF")
            set_cell_margins(cell, top=60, bottom=60, left=100, right=100)
            p = cell.paragraphs[0]
            r = p.add_run(val)
            r.font.size = Pt(9)
            if i == 0:
                r.font.bold = True

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # -------------------------------------------------------------
    # SECTION 5: BACKEND ARCHITECTURE
    # -------------------------------------------------------------
    add_h1("5. Backend Software Architecture")
    add_body("The backend is built with high-performance Python 3, FastAPI, and WebSockets to handle real-time streaming at 10 Hz without thread blocking:")
    
    add_bullet(" Reads 303,495 rows from dataset.csv, chronologically interleaves all 9 channels, and streams them asynchronously to connected clients.", "• backend/telemetry_source.py:")
    add_bullet(" Maintains an in-memory sliding buffer for each channel and calculates the 19 mathematical features on-the-fly.", "• backend/feature_extractor.py:")
    add_bullet(" Loads the trained Scaler and Model pipelines, generates real-time predictions and calibrated probability scores.", "• backend/model_service.py:")
    add_bullet(" Exposes the REST health check endpoint and the high-throughput ws://127.0.0.1:8000/stream WebSocket route.", "• backend/main.py:")

    # -------------------------------------------------------------
    # SECTION 6: FRONTEND UI COMPLETE WALKTHROUGH
    # -------------------------------------------------------------
    add_h1("6. Frontend Mission Control Console: Section-by-Section Guide")
    add_body("The frontend dashboard is designed to provide high visual acuity, zero eye strain during extended mission monitoring, and seamless technician interaction. Below is the detailed breakdown of every section and visual element:")

    add_h2("6.1 Top Mission Header")
    add_bullet(" Displays the project identifier ('ORBITGUARD') in a warm amber gold badge.", "• Mission Identity Badge:")
    add_bullet(" 'ESA OPS-SAT Telemetry & Anomaly Analysis Console' with an orbital altitude badge ('LEO 510 km').", "• Mission Title:")
    add_bullet(" A live pulsing dot that blinks green during active telemetry transmission.", "• Live Telemetry Stream Heartbeat:")
    add_bullet(" Displays the exact number of unresolved incidents in red (e.g., '14 UNRESOLVED FAULTS') or green ('✓ 0 UNRESOLVED FAULTS').", "• Unresolved Fault Counter:")
    add_bullet(" Real-time Coordinated Universal Time (UTC) clock formatted down to the second.", "• UTC Mission Clock:")
    add_bullet(" A prominent button allowing operators to freeze incoming stream frames for inspection or resume live telemetry.", "• [PAUSE / RESUME] Stream Controls:")

    add_h2("6.2 Telemetry Waveform Oscilloscope (Top Left Panel)")
    add_bullet(" Plots real-time telemetry signal amplitude over rolling time frames in clean Emerald Green (#10B981).", "• High-Resolution Signal Canvas:")
    add_bullet(" When an anomaly occurs, the corresponding data point turns into a distinct Crimson Red (#EF4444) excursion marker.", "• Anomaly Excursion Points:")
    add_bullet(" 9 dedicated channel buttons (CADC0872–0894). Each button features a live status dot: Bright Emerald Green for nominal, Pulsing Crimson Red for active fault. Selected channels feature an amber gold outline.", "• 9-Channel Selector Strip:")
    add_bullet(" Displays the latest value in 4-digit scientific notation (e.g. 1.3400e-05 T).", "• Latest Reading Display:")
    add_bullet(" Displays '✓ NOMINAL STABLE' in green or '⚠️ FAULT DETECTED' in red.", "• Channel State Badge:")
    add_bullet(" Calibrated AI anomaly probability score (e.g. 98.4%).", "• Anomaly Risk Percentage:")

    add_h2("6.3 Dynamic Graph Topology & Root Cause Propagation (Bottom Left Panel)")
    add_bullet(" Upper bounding container grouping the 3-axis magnetometers (Mag X, Mag Y, Mag Z).", "• ADCS Attitude Triad Cluster:")
    add_bullet(" Lower bounding container housing the 6 solar array photodiode sensors (PD 1 through PD 6).", "• EPS Solar Sensor Cluster:")
    add_bullet(" 18px radius nodes with high-contrast white channel numbers and descriptive titles below. Clicking any node instantly focuses the oscilloscope on that channel.", "• Interactive Sensor Nodes:")
    add_bullet(" When a fault occurs, the identified root cause node pulses with an outer alert ring, and its correlation edges turn Crimson Red to illustrate physical cross-sensor propagation.", "• Root Cause Pulse & Fault Propagation Lines:")

    add_h2("6.4 Root Cause & Actionable FDIR Diagnostics Panel (Top Right Panel)")
    add_bullet(" Large bold readout displaying the exact channel ID, sensor title, and calibrated fault probability.", "• Root Cause Identification:")
    add_bullet(" Explicitly identifies whether the fault originates in Attitude Control (ADCS) or Power/Optical (EPS).", "• Affected Subsystem:")
    add_bullet(" Detailed failure description (e.g., Magnetic Dipole Inversion / Solar Shadowing).", "• Failure Pattern:")
    add_bullet(" Lists all secondary sensors experiencing coupled ripple effects.", "• Propagation Radius:")
    add_bullet(" Step-by-step operational recovery instructions following official ESA OPS-SAT mission guidelines.", "• Recommended FDIR Remediation:")
    add_bullet(" A prominent green button allowing the operator to execute the fix, mark the issue as resolved, and log the action.", "• [EXECUTE FIX & RESOLVE] Action Button:")

    add_h2("6.5 Technician Incident Inbox (Bottom Right Panel)")
    add_bullet(" Unlike standard dashboards where anomalies vanish on the next data packet, OrbitGuard generates persistent tickets (INC-101, INC-102...) that stay visible until resolved.", "• Persistent Problem Queue:")
    add_bullet(" A dedicated container with a custom titanium scrollbar allowing technicians to scroll smoothly through all recorded incident events.", "• Smooth Scrollable Feed:")
    add_bullet(" Displays the exact number of open vs resolved tickets (e.g. 'Open (18)').", "• Exact Ticket Counter:")
    add_bullet(" Switch between active 'Unresolved' issues and archived 'Resolved' history with resolution timestamps.", "• Open vs Resolved Tabs:")
    add_bullet(" Quick one-click action to clear and resolve all open incidents simultaneously.", "• 'Resolve All' Action:")

    add_h2("6.6 Stream Journal Footer")
    add_bullet(" Displays the total count of logged telemetry frames in the active session.", "• Logged Frames Counter:")
    add_bullet(" Confirms health of all 9 spacecraft sensors ('9 / 9 OPERATIONAL').", "• Active Sensor Tally:")
    add_bullet(" Displays active AI architecture ('DYNAMIC GRAPH ANOMALY DETECTOR + FDIR').", "• AI Model Badge:")

    # -------------------------------------------------------------
    # SECTION 7: STEP-BY-STEP EXECUTION
    # -------------------------------------------------------------
    add_h1("7. System Execution & Verification Guide")
    add_body("To launch and operate the OrbitGuard platform:")
    
    add_h2("Step 1: Start Backend Telemetry Server")
    add_body("Run the following command in the project root directory:")
    add_bullet("uvicorn backend.main:app --reload --port 8000", "Command: ")
    add_body("The server will initialize the multi-channel streaming engine and start listening on http://127.0.0.1:8000 and ws://127.0.0.1:8000/stream.")

    add_h2("Step 2: Start Frontend Mission Console")
    add_body("In a separate terminal, navigate to the frontend directory and start the Vite dev server:")
    add_bullet("cd frontend && npm run dev", "Command: ")
    add_body("Open http://localhost:5173 in your browser to access the OrbitGuard console.")

    add_h2("Step 3: Verify Anomaly Handling & Incident Resolution")
    add_bullet(" Observe the green waveform oscilloscope and live values streaming at 10 Hz across all 9 sensors.", "1. Normal Stream:")
    add_bullet(" When a telemetry anomaly occurs in the ESA OPS-SAT dataset, observe the waveform spike in red, the root sensor node pulse in the Dynamic Topology Graph, and a new incident ticket appear in the Technician Inbox.", "2. Anomaly Trigger:")
    add_bullet(" Click [EXECUTE FIX & RESOLVE] on the ticket to apply the FDIR action and archive it to the Resolved tab.", "3. Technician Resolution:")

    # Output file
    output_path = os.path.join(os.getcwd(), "OrbitGuard_Complete_Project_Documentation.docx")
    doc.save(output_path)
    print(f"Document successfully created at: {output_path}")

if __name__ == "__main__":
    create_document()
