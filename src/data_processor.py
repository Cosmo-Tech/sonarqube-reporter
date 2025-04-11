"""
Data processing module for SonarQube Reporter.
Processes and organizes data from SonarQube API for quality gate report generation.
"""

import os
import yaml
import logging
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)


class DataProcessor:
    """Processes and organizes data from SonarQube for quality gate report generation."""

    def __init__(self, sonarqube_client):
        """
        Initialize the data processor.

        Args:
            sonarqube_client (SonarQubeClient): The SonarQube API client.
        """
        self.client = sonarqube_client
        self.included_projects = self._load_project_config()
        self.sonarqube_url = self.client.base_url

    def get_all_projects_data(self):
        """
        Get data for all projects including quality gate status.

        Returns:
            list: List of project data dictionaries.
        """
        logger.debug("Retrieving all projects from SonarQube")
        all_projects = self.client.get_projects()
        logger.debug(f"Retrieved {len(all_projects)} projects from SonarQube")

        # Filter projects if configuration exists
        if self.included_projects:
            projects = [p for p in all_projects if p["key"] in self.included_projects]
            logger.info(f"Filtered to {len(projects)} projects based on configuration")
        else:
            projects = all_projects
            logger.info("No project filtering configured, including all projects")

        projects_data = []

        for project in projects:
            project_key = project["key"]
            project_name = project.get("name", project_key)

            logger.debug(f"Processing project: {project_name} ({project_key})")

            # Get quality gate status
            quality_gate = self.client.get_quality_gate_status(project_key)

            # Get quality gate history
            logger.debug(f"Retrieving quality gate history for project: {project_name}")
            quality_gate_history = self.client.get_quality_gate_history(project_key)
            logger.debug(
                f"Retrieved {len(quality_gate_history)} historical quality gate statuses"
            )

            # Process history for visualization
            history_data = self._process_history_for_visualization(quality_gate_history)

            # Add quality gate status to project data
            project_data = {
                "key": project_key,
                "name": project_name,
                "last_analysis_date": self._format_date(
                    project.get("lastAnalysisDate")
                ),
                "quality_gate_status": quality_gate.get("status", "NONE"),
                "quality_gate_conditions": quality_gate.get("conditions", []),
                "url": f"{self.sonarqube_url}/dashboard?id={project_key}",
                "quality_gate_history": quality_gate_history,
                "history_data": history_data,
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
        status_counts = {"OK": 0, "WARN": 0, "ERROR": 0, "NONE": 0}

        for project in projects_data:
            status = project.get("quality_gate_status", "NONE")
            status_counts[status] = status_counts.get(status, 0) + 1

        logger.debug(f"Status counts: {status_counts}")

        # Determine overall status
        if status_counts.get("ERROR", 0) > 0:
            overall_status = {
                "status": "ERROR",
                "label": "FAILED",
                "css_class": "fail",
                "color": "#d4333f",
                "message": f"{status_counts.get('ERROR', 0)} projects failed quality gate",
            }
        elif status_counts.get("WARN", 0) > 0:
            overall_status = {
                "status": "WARN",
                "label": "WARNING",
                "css_class": "warn",
                "color": "#ed7d20",
                "message": f"{status_counts.get('WARN', 0)} projects have warnings",
            }
        elif status_counts.get("OK", 0) > 0:
            overall_status = {
                "status": "OK",
                "label": "PASSED",
                "css_class": "pass",
                "color": "#00aa00",
                "message": "All projects passed quality gate",
            }
        else:
            overall_status = None

        logger.debug(f"Calculated overall status: {overall_status}")
        return overall_status

    def _process_history_for_visualization(self, history):
        """
        Process quality gate history for visual representation.

        Args:
            history (list): List of historical quality gate statuses.

        Returns:
            dict: Processed data for quality gate history visualization.
        """
        if not history:
            return {"values": [], "colors": []}

        # Reverse to get chronological order (oldest to newest)
        history = list(reversed(history))

        values = []
        colors = []

        for item in history:
            status = item.get("status")

            # Map status to numeric value for sparkline
            if status == "OK":
                values.append(1)  # Pass
                colors.append("#00aa00")  # Green
            elif status == "WARN":
                values.append(0.5)  # Warning
                colors.append("#ed7d20")  # Orange
            else:
                values.append(0)  # Fail
                colors.append("#d4333f")  # Red

        return {"values": values, "colors": colors}

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
            date_obj = datetime.strptime(date_string.split("+")[0], "%Y-%m-%dT%H:%M:%S")
            formatted_date = date_obj.strftime("%Y-%m-%d %H:%M:%S")
            logger.debug(f"Formatted date: {date_string} -> {formatted_date}")
            return formatted_date
        except (ValueError, TypeError) as e:
            logger.debug(f"Error formatting date {date_string}: {str(e)}")
            return date_string

    def _load_project_config(self):
        """
        Load project filtering configuration from report-config.yaml.

        Returns:
            list: List of project keys to include, or empty list if no config exists.
        """
        try:
            config_path = "report-config.yaml"
            if not os.path.exists(config_path):
                logger.info("No report-config.yaml found, will include all projects")
                return []

            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            if not config or not isinstance(config, dict):
                logger.warning("Invalid configuration format in report-config.yaml")
                return []

            projects = config.get('projects', [])
            if not projects:
                logger.info("No projects specified in config, will include all projects")
                return []

            if not isinstance(projects, list):
                logger.warning("Projects configuration must be a list")
                return []

            logger.info(f"Loaded {len(projects)} projects from configuration")
            return projects

        except Exception as e:
            logger.error(f"Error loading project configuration: {str(e)}")
            return []
