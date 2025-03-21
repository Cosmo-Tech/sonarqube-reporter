import sys
import os
import click
import logging

from src.sonarqube_client import SonarQubeClient
from src.data_processor import DataProcessor
from src.report_generator import ReportGenerator

logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose output"
)
def main(verbose):
    """Generate a quality gate report from SonarQube data.
    
    This tool connects to a SonarQube server, retrieves project data,
    and generates an HTML report showing the quality gate status for each project.
    """
    if verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled")
    token = os.getenv("SONARQUBE_REPORT_TOKEN")

    client = SonarQubeClient("http://localhost:9000", token)
    # Initialize data processor
    data_processor = DataProcessor(client)
    # Get projects data
    logger.info("Retrieving projects data from SonarQube")
    projects_data = data_processor.get_all_projects_data()
    logger.info(f"[bold green]Found {len(projects_data)} projects")
    
    # Create a simple config object with hardcoded values
    class SimpleConfig:
        def get_sonarqube_url(self):
            return "http://localhost:9000"
            
        def get_styling(self):
            return {
                'primary_color': '#4b9fd5',
                'secondary_color': '#236a97',
                'pass_color': '#00aa00',
                'fail_color': '#d4333f',
                'warning_color': '#ed7d20'
            }
            
        def get_quality_gate_report_path(self):
            # Ensure reports directory exists
            os.makedirs("reports", exist_ok=True)
            return "reports/quality_gate_report.html"
    
    # Initialize report generator with simple config
    report_generator = ReportGenerator(SimpleConfig())
    # Generate quality gate report
    report_generator.generate_quality_gate_report(projects_data)
    return 0

if __name__ == "__main__":
    sys.exit(main())