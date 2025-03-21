"""
Data processing module for SonarQube Reporter.
Processes and organizes data from SonarQube API for quality gate report generation.
"""

import logging
from datetime import datetime
from rich.logging import RichHandler

# Set up logging
logger = logging.getLogger("sonarqube_reporter")


class DataProcessor:
    """Processes and organizes data from SonarQube for quality gate report generation."""

    def __init__(self, sonarqube_client):
        """
        Initialize the data processor.

        Args:
            sonarqube_client (SonarQubeClient): The SonarQube API client.
        """
        self.client = sonarqube_client
        self.sonarqube_url = self.client.base_url

    def get_all_projects_data(self):
        """
        Get data for all projects including quality gate status.

        Returns:
            list: List of project data dictionaries.
        """
        logger.debug("Retrieving all projects from SonarQube")
        projects = self.client.get_projects()
        logger.debug(f"Retrieved {len(projects)} projects from SonarQube")
        
        projects_data = []

        for project in projects:
            project_key = project['key']
            project_name = project.get('name', project_key)
            
            logger.debug(f"Processing project: {project_name} ({project_key})")
            
            # Get quality gate status
            quality_gate = self.client.get_quality_gate_status(project_key)
            
            # Add quality gate status to project data
            project_data = {
                'key': project_key,
                'name': project_name,
                'last_analysis_date': self._format_date(project.get('lastAnalysisDate')),
                'quality_gate_status': quality_gate.get('status', 'NONE'),
                'quality_gate_conditions': quality_gate.get('conditions', []),
                'url': f"{self.sonarqube_url}/dashboard?id={project_key}"
            }
            
            projects_data.append(project_data)
            
        logger.info(f"Processed data for {len(projects_data)} projects")
        return projects_data, self._calculate_overall_status(projects_data)
        
    def _calculate_overall_status(self, projects_data):
        """
        Calculate the overall status based on all projects.
        
        Args:
            projects_data (list): List of project data dictionaries.
            
        Returns:
            dict: Overall status information.
        """
        if not projects_data:
            logger.debug("No projects data available for overall status calculation")
            return None
            
        # Count projects by status
        status_counts = {
            'OK': 0,
            'WARN': 0,
            'ERROR': 0,
            'NONE': 0
        }
        
        for project in projects_data:
            status = project.get('quality_gate_status', 'NONE')
            status_counts[status] = status_counts.get(status, 0) + 1
            
        logger.debug(f"Status counts: {status_counts}")
        
        # Determine overall status
        if status_counts.get('ERROR', 0) > 0:
            overall_status = {
                'status': 'ERROR',
                'label': 'FAILED',
                'css_class': 'fail',
                'color': '#d4333f',
                'message': f"{status_counts.get('ERROR', 0)} projects failed quality gate"
            }
        elif status_counts.get('WARN', 0) > 0:
            overall_status = {
                'status': 'WARN',
                'label': 'WARNING',
                'css_class': 'warn',
                'color': '#ed7d20',
                'message': f"{status_counts.get('WARN', 0)} projects have warnings"
            }
        elif status_counts.get('OK', 0) > 0:
            overall_status = {
                'status': 'OK',
                'label': 'PASSED',
                'css_class': 'pass',
                'color': '#00aa00',
                'message': 'All projects passed quality gate'
            }
        else:
            overall_status = None
            
        logger.debug(f"Calculated overall status: {overall_status}")
        return overall_status

    def _format_date(self, date_string):
        """
        Format a date string from SonarQube.

        Args:
            date_string (str): Date string from SonarQube.

        Returns:
            str: Formatted date string.
        """
        if not date_string:
            logger.debug("Empty date string, returning N/A")
            return "N/A"
        
        try:
            # SonarQube date format: YYYY-MM-DDThh:mm:ss+0000
            date_obj = datetime.strptime(date_string.split('+')[0], '%Y-%m-%dT%H:%M:%S')
            formatted_date = date_obj.strftime('%Y-%m-%d %H:%M:%S')
            logger.debug(f"Formatted date: {date_string} -> {formatted_date}")
            return formatted_date
        except (ValueError, TypeError) as e:
            logger.debug(f"Error formatting date {date_string}: {str(e)}")
            return date_string