## SonarQube PDF Report Generator

This Python script connects to a SonarQube instance, fetches a comprehensive analysis of a specified project, and generates a detailed PDF report. The report includes key project metrics, Quality Gate status, and a full, chronological history of every issue, including user-added comments and status changes.

### Key Features

*   **Comprehensive Metrics:** Captures and displays key metrics like Bugs, Vulnerabilities, Code Smells, Coverage, and Duplication.
*   **Quality Gate Status:** Clearly shows whether the project has passed or failed its Quality Gate.
*   **Full Issue History:** Goes beyond the current issue status to include a detailed changelog for each issue, capturing all attribute changes and valuable user comments from the SonarQube UI.
*   **Efficient API Calls:** Optimizes data retrieval by using a single API endpoint to fetch issues and their comments, improving performance and reliability.
*   **Automated PDF Generation:** Uses the `reportlab` library to create a clean, well-structured, and print-friendly PDF document.
*   **Cross-Platform Compatibility:** Includes logic to automatically open the generated PDF on Windows, macOS, and Linux.

### Prerequisites

Before you run the script, ensure you have Python3 installed. Then, install the required libraries using pip:

```plaintext
pip install -r requirements.txt
```

### Configuration

1.  **Clone or Download:** Get a copy of the `sonarqube_pdf_report_generator.py` script.
2.  **Edit the Script:** Open the file in a text editor.
3.  **Update Variables:** In the `--- CONFIGURATION ---` section at the top of the file, replace the placeholder values with your specific details:
    *   `SONARQUBE_URL`: The full URL of your SonarQube server (e.g., `"http://localhost:9000"`).
    *   `SONARQUBE_TOKEN`: A SonarQube user token with "Browse" permissions on the project. You can generate one in your SonarQube account settings.
    *   `PROJECT_KEY`: The unique key of the project you want to analyze (e.g., `"my_awesome_project"`).

### Usage

To generate the report, simply run the script from your terminal:

```plaintext
python generate_report.py
```

The script will fetch the data, generate a PDF named `sonarqube_report_[PROJECT_KEY]_full.pdf` in the same directory, and attempt to open it automatically.

### Notes

*   This script has been tested with SonarQube Community Edition and is designed to handle paginated API responses.
*   For very large projects with thousands of issues, the initial data fetch may take some time.
*   Ensure the user token has sufficient permissions to access all project data.

### Contributing

Contributions are welcome! If you find a bug or have an idea for an improvement, feel free to open an issue or submit a pull request.

### License

This project is open-source and available under the MIT License.
