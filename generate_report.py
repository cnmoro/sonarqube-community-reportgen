# How to Use:
# 1.  Fill in the CONFIGURATION variables below with your SonarQube URL,
#     a user-generated access token, and the key of the project you want to analyze.
# 2.  Run the script from your terminal:
#     python generate_report.py

import requests
import os
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from reportlab.lib.units import inch

# --- CONFIGURATION ---
# Replace these values with your SonarQube server details and project key.
SONARQUBE_URL = "http://127.0.0.1:9000"  # Your SonarQube server URL
SONARQUBE_TOKEN = ""           # A SonarQube user token with analysis permissions
PROJECT_KEY = "" # The key of the project you want to analyze
OUTPUT_FILENAME = f"sonarqube_report_{PROJECT_KEY}.pdf"

# --- STYLING & CONSTANTS ---
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
styles.add(ParagraphStyle(name='ReportTitle', fontSize=24, alignment=TA_CENTER, spaceAfter=20))
styles.add(ParagraphStyle(name='SectionTitle', fontSize=16, spaceAfter=10, spaceBefore=20))
styles.add(ParagraphStyle(name='MetricValue', fontSize=28, alignment=TA_CENTER, leading=34))
styles.add(ParagraphStyle(name='MetricLabel', fontSize=10, alignment=TA_CENTER))
styles.add(ParagraphStyle(name='IssueMessage', fontSize=10, leading=12))
styles.add(ParagraphStyle(name='HistoryText', fontSize=8, leading=10))
styles.add(ParagraphStyle(name='HistoryDate', fontSize=8, leading=10, textColor=colors.grey))

METRIC_KEYS = [
    "bugs", "vulnerabilities", "code_smells", "coverage",
    "duplicated_lines_density", "ncloc" # ncloc = Non-commenting lines of code
]

SEVERITY_COLORS = {
    "BLOCKER": colors.HexColor("#B40404"),
    "CRITICAL": colors.HexColor("#FF0000"),
    "MAJOR": colors.HexColor("#FF8000"),
    "MINOR": colors.HexColor("#FACC2E"),
    "INFO": colors.HexColor("#0080FF")
}

STATUS_COLORS = {
    "OPEN": colors.HexColor("#FACC2E"),
    "REOPENED": colors.HexColor("#FF8000"),
    "CONFIRMED": colors.HexColor("#0080FF"),
    "RESOLVED": colors.HexColor("#088A08"),
    "CLOSED": colors.HexColor("#585858")
}

# --- API CLIENT ---

def call_sonarqube_api(endpoint, params={}):
    """Handles making a request to the SonarQube API."""
    headers = {'Accept': 'application/json'}
    auth = (SONARQUBE_TOKEN, '')
    url = f"{SONARQUBE_URL}/{endpoint}"
    
    try:
        response = requests.get(url, headers=headers, params=params, auth=auth)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling SonarQube API at endpoint '{endpoint}': {e}")
        if "401" in str(e):
            print("Authentication failed (401). Please check your SONARQUBE_TOKEN is valid.")
        elif "403" in str(e):
            print("Authorization failed (403). The user associated with the token may lack necessary permissions (e.g., 'Browse' permission on the project).")
        elif "404" in str(e):
             print(f"Project with key '{PROJECT_KEY}' not found (404). Please verify the PROJECT_KEY.")
        else:
            print(f"Please ensure SonarQube is running at {SONARQUBE_URL} and is accessible.")
        return None

# --- DATA FETCHING FUNCTIONS ---

def get_project_measures(project_key):
    """Fetches key metrics for a given project."""
    print(f"Fetching project measures for '{project_key}'...")
    params = {"component": project_key, "metricKeys": ",".join(METRIC_KEYS)}
    data = call_sonarqube_api("api/measures/component", params)
    if data and 'component' in data:
        return {m['metric']: m.get('value', 'N/A') for m in data['component']['measures']}
    return None

def get_quality_gate_status(project_key):
    """Fetches the quality gate status for a given project."""
    print(f"Fetching quality gate status for '{project_key}'...")
    params = {"projectKey": project_key}
    data = call_sonarqube_api("api/qualitygates/project_status", params)
    if data and 'projectStatus' in data:
        return data['projectStatus']
    return None

def get_all_issues_with_history(project_key):
    """Fetches all issues for a project, including their full changelog and comments."""
    print(f"Fetching all issues for '{project_key}'...")
    all_issues = []
    page = 1
    page_size = 500

    # Include all possible statuses and history in the search
    params = {
        "componentKeys": project_key,
        "p": page,
        "ps": page_size,
        "s": "CREATION_DATE",
        "asc": "false",
        "statuses": "OPEN,CONFIRMED,REOPENED,RESOLVED,CLOSED",
        "additionalFields": "_all" # Request all available fields, including comments
    }

    while True:
        params['p'] = page
        data = call_sonarqube_api("api/issues/search", params)
        if not data or 'issues' not in data:
            break

        issues_on_page = data['issues']
        all_issues.extend(issues_on_page)

        total_issues = data['total']
        if len(all_issues) >= total_issues:
            break

        page += 1
        print(f"  - Fetched {len(all_issues)} of {total_issues} issues so far...")

    print(f"Total issues processed: {len(all_issues)}")
    return all_issues

# --- PDF GENERATION ---

class ReportPDF:
    """Class to handle the creation of the PDF report."""
    def __init__(self, filename):
        self.doc = SimpleDocTemplate(filename,
                                     rightMargin=inch/2, leftMargin=inch/2,
                                     topMargin=inch/2, bottomMargin=inch/2)
        self.elements = []

    def add_header(self, project_name, analysis_date):
        """Adds the main title and report generation date."""
        self.elements.append(Paragraph("SonarQube Analysis Report", styles['ReportTitle']))
        self.elements.append(Paragraph(f"Project: {project_name}", styles['Center']))
        
        date_str = "N/A"
        if analysis_date:
            parsed_date = datetime.strptime(analysis_date, "%Y-%m-%dT%H:%M:%S%z")
            date_str = parsed_date.strftime('%B %d, %Y at %I:%M %p %Z')
        
        self.elements.append(Paragraph(f"Analysis Date: {date_str}", styles['Center']))
        self.elements.append(Paragraph(f"Report Generated: {datetime.now().strftime('%B %d, %Y')}", styles['Center']))
        self.elements.append(Spacer(1, 0.4 * inch))

    def add_quality_gate(self, status_data):
        """Adds the Quality Gate status section."""
        self.elements.append(Paragraph("Quality Gate Status", styles['SectionTitle']))
        status = status_data.get('status', 'UNKNOWN')
        status_text = {
            'OK': '<font color="green">PASSED</font>',
            'ERROR': '<font color="red">FAILED</font>'
        }.get(status, f'<font color="orange">{status}</font>')
        self.elements.append(Paragraph(status_text, styles['MetricValue']))
        self.elements.append(Spacer(1, 0.5 * inch))

    def add_summary_metrics(self, metrics):
        """Adds the main metrics summary in a table."""
        self.elements.append(Paragraph("Project Summary", styles['SectionTitle']))
        data = [
            [self._create_metric_cell(metrics, "bugs", "Bugs"),
             self._create_metric_cell(metrics, "vulnerabilities", "Vulnerabilities"),
             self._create_metric_cell(metrics, "code_smells", "Code Smells")],
            [self._create_metric_cell(metrics, "coverage", "Coverage", "%"),
             self._create_metric_cell(metrics, "duplicated_lines_density", "Duplications", "%"),
             self._create_metric_cell(metrics, "ncloc", "Lines of Code")]
        ]
        table = Table(data, colWidths=[self.doc.width/3.0]*3, rowHeights=1.2*inch)
        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('BOX', (0, 0), (-1, -1), 2, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        self.elements.append(table)

    def _create_metric_cell(self, metrics, key, label, suffix=""):
        value = metrics.get(key, '0')
        value_str = f"{value}{suffix}" if value != 'N/A' else 'N/A'
        return [Paragraph(value_str, styles['MetricValue']), Paragraph(label, styles['MetricLabel'])]

    def add_detailed_issues(self, issues):
        """Adds a detailed section for each issue and its history."""
        self.elements.append(PageBreak())
        self.elements.append(Paragraph("Detailed Issues Report (Including Full History)", styles['SectionTitle']))

        if not issues:
            self.elements.append(Paragraph("No issues found.", styles['Left']))
            return

        for issue in issues:
            self.elements.append(Spacer(1, 0.2 * inch))

            # Create the main issue table
            main_issue_table = self._create_main_issue_table(issue)
            self.elements.append(main_issue_table)

            # Create the history/changelog and comments table
            # Pass the whole issue object, not just the changelog
            history_table = self._create_history_table(issue)
            self.elements.append(history_table)

    def _create_main_issue_table(self, issue):
        """Creates the table for a single issue's main details."""
        severity = issue.get('severity', 'N/A')
        status = issue.get('status', 'N/A')
        resolution = issue.get('resolution', '')
        status_text = f"{status} ({resolution})" if resolution else status
        
        component_full = issue.get('component', 'N/A')
        component_short = component_full.split(':')[-1]
        line = issue.get('line', '-')
        
        # Create Paragraphs for styling within the table
        p_severity = Paragraph(severity, styles['Normal'])
        p_status = Paragraph(status_text, styles['Normal'])
        p_component = Paragraph(f"{component_short}<b>: {line}</b>", styles['Normal'])
        p_message = Paragraph(issue.get('message', 'N/A'), styles['IssueMessage'])
        
        data = [
            [p_severity, p_status, p_component],
            [p_message, '', ''] # Message spans all columns
        ]
        
        table = Table(data, colWidths=[inch, inch, self.doc.width - 2*inch])
        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            # Span the message cell across the whole row
            ('SPAN', (0, 1), (2, 1)),
            # Color severity
            ('BACKGROUND', (0, 0), (0, 0), SEVERITY_COLORS.get(severity, colors.lightgrey)),
            ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
            # Color status
            ('BACKGROUND', (1, 0), (1, 0), STATUS_COLORS.get(status, colors.lightgrey)),
            ('TEXTCOLOR', (1, 0), (1, 0), colors.white),
        ]))
        return table

    def _create_history_table(self, issue):
        """Creates a table for an issue's changelog, including comments."""
        header = [
            Paragraph("<b>Date</b>", styles['HistoryText']), 
            Paragraph("<b>User</b>", styles['HistoryText']), 
            Paragraph("<b>Change / Comment</b>", styles['HistoryText'])
        ]
        data = [header]

        history_items = []

        # Add comments from the 'comments' field
        for comment in issue.get('comments', []):
            history_items.append({
                'createdAt': comment.get('createdAt'),
                'user': comment.get('login'), # 'login' is used for comments
                'type': 'comment',
                'text': comment.get('markdown')
            })

        # Add diffs from the 'changelog' field
        for entry in issue.get('changelog', []):
            history_items.append({
                'createdAt': entry.get('createdAt'),
                'user': entry.get('user', {}).get('name'),
                'type': 'diff',
                'diffs': entry.get('diffs', [])
            })

        # Sort all history items by creation date
        history_items.sort(key=lambda x: datetime.strptime(x['createdAt'], "%Y-%m-%dT%H:%M:%S%z") if x.get('createdAt') else datetime.min)

        for entry in history_items:
            created_at_raw = entry.get('createdAt')
            if created_at_raw:
                created_at = datetime.strptime(created_at_raw, "%Y-%m-%dT%H:%M:%S%z").strftime('%Y-%m-%d %H:%M')
            else:
                created_at = "N/A"

            user = entry.get('user', 'System')

            change_details = []

            # Process comments
            if entry['type'] == 'comment':
                comment_text = entry.get('text', '').strip()
                if comment_text:
                    safe_text = comment_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    change_details.append(f"<b>Comment:</b> {safe_text}")

            # Process diffs
            elif entry['type'] == 'diff':
                for diff in entry.get('diffs', []):
                    old_val = diff.get('oldValue', '')
                    new_val = diff.get('newValue', '')
                    if old_val or new_val:
                        change_details.append(f"<i>{diff['key'].title()}</i> changed from '<b>{old_val}</b>' to '<b>{new_val}</b>'")

            if not change_details:
                continue

            p_date = Paragraph(created_at, styles['HistoryDate'])
            p_user = Paragraph(user, styles['HistoryText'])
            p_details = Paragraph("<br/>".join(change_details), styles['HistoryText'])

            data.append([p_date, p_user, p_details])

        if len(data) > 1:
            table = Table(data, colWidths=[1.2 * inch, 1.2 * inch, self.doc.width - 2.4 * inch])
            table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            return table
        return Spacer(0, 0)

    def build(self):
        """Generates the final PDF file."""
        print(f"Building PDF report: {self.doc.filename}...")
        self.doc.build(self.elements)
        print("Report generation complete!")

# --- MAIN EXECUTION ---

def main():
    """Main function to orchestrate the report generation."""
    print("--- SonarQube PDF Report Generator (Full History) ---")

    if not all([SONARQUBE_URL, SONARQUBE_TOKEN, PROJECT_KEY]):
        print("Configuration error: Please set SONARQUBE_URL, SONARQUBE_TOKEN, and PROJECT_KEY.")
        return

    measures = get_project_measures(PROJECT_KEY)
    quality_gate = get_quality_gate_status(PROJECT_KEY)
    issues = get_all_issues_with_history(PROJECT_KEY)

    if measures is None or quality_gate is None or issues is None:
        print("\nFailed to fetch required data from SonarQube. Aborting report generation.")
        return

    analysis_date = None
    if quality_gate.get('conditions'):
        analysis_date = quality_gate['conditions'][0].get('lastAnalysisTime')

    pdf = ReportPDF(OUTPUT_FILENAME)
    pdf.add_header(PROJECT_KEY, analysis_date)
    pdf.add_quality_gate(quality_gate)
    pdf.add_summary_metrics(measures)
    pdf.add_detailed_issues(issues)
    pdf.build()
    
    try:
        if os.name == 'nt': os.startfile(OUTPUT_FILENAME)
        elif os.uname().sysname == 'Darwin': os.system(f'open "{OUTPUT_FILENAME}"')
        else: os.system(f'xdg-open "{OUTPUT_FILENAME}"')
    except Exception:
        print(f"\nCould not automatically open the PDF. Please find it at: {os.path.abspath(OUTPUT_FILENAME)}")

if __name__ == "__main__":
    main()
