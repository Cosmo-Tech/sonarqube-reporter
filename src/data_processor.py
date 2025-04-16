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
        Get data for all projects including quality gate status, organized by groups.

        Returns:
            tuple: (dict of grouped project data, overall status)
        """
        logger.debug("Retrieving all projects from SonarQube")
        all_projects = self.client.get_projects()
        logger.debug(f"Retrieved {len(all_projects)} projects from SonarQube")

        # Load configuration including groups
        included_projects, _ = self._load_project_config()

        # Filter projects if configuration exists
        if included_projects:
            projects = [p for p in all_projects if p["key"] in included_projects]
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
                "url": f"{self.sonarqube_url.rstrip('/')}/dashboard?id={project_key}",
                "quality_gate_history": quality_gate_history,
                "history_data": history_data,
            }

            projects_data.append(project_data)

        logger.info(f"Processed data for {len(projects_data)} projects")

        # Organize projects into groups
        grouped_data = self._process_groups(projects_data)
        overall_status = self._calculate_overall_status(projects_data)

        return grouped_data, overall_status

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
            tuple: (list of project keys to include, list of group configurations)
        """
        try:
            config_path = "report-config.yaml"
            if not os.path.exists(config_path):
                logger.info("No report-config.yaml found, will include all projects")
                return [], []

            with open(config_path, "r") as f:
                config = yaml.safe_load(f)

            if not config or not isinstance(config, dict):
                logger.warning("Invalid configuration format in report-config.yaml")
                return [], []

            # Load groups configuration
            groups = config.get("groups", [])
            if not isinstance(groups, list):
                logger.warning("Groups configuration must be a list")
                groups = []

            # Load ungrouped projects
            projects = config.get("projects", [])
            if not isinstance(projects, list):
                logger.warning("Projects configuration must be a list")
                projects = []

            # Combine all project keys for filtering
            all_projects = projects.copy()
            for group in groups:
                if isinstance(group, dict) and "projects" in group:
                    all_projects.extend(group["projects"])

            logger.info(
                f"Loaded {len(all_projects)} projects and {len(groups)} groups from configuration"
            )
            return all_projects, groups

        except Exception as e:
            logger.error(f"Error loading project configuration: {str(e)}")
            return [], []

    def _calculate_group_status(self, projects):
        """
        Calculate the overall status for a group of projects.

        Args:
            projects (list): List of project data dictionaries.

        Returns:
            dict: Status information for the group.
        """
        if not projects:
            return None

        # Count projects by status
        status_counts = {"OK": 0, "WARN": 0, "ERROR": 0, "NONE": 0}
        for project in projects:
            status = project.get("quality_gate_status", "NONE")
            status_counts[status] = status_counts.get(status, 0) + 1

        # Determine overall status
        if status_counts.get("ERROR", 0) > 0:
            return {
                "status": "ERROR",
                "label": "FAILED",
                "css_class": "fail",
                "color": "var(--fail-color)",
                "message": f"{status_counts['ERROR']} failed",
            }
        elif status_counts.get("WARN", 0) > 0:
            return {
                "status": "WARN",
                "label": "WARNING",
                "css_class": "warn",
                "color": "var(--warning-color)",
                "message": f"{status_counts['WARN']} warnings",
            }
        elif status_counts.get("OK", 0) > 0:
            return {
                "status": "OK",
                "label": "PASSED",
                "css_class": "pass",
                "color": "var(--pass-color)",
                "message": "All passed",
            }
        return None

    def _process_groups(self, projects_data):
        """
        Organize projects into their defined groups and calculate group statuses.

        Args:
            projects_data (list): List of project data dictionaries.

        Returns:
            dict: Projects organized by groups and "ungrouped" section with status information.
        """
        _, groups = self._load_project_config()

        # Initialize result structure
        grouped_projects = {"groups": [], "ungrouped": []}

        # Create a map of project key to project data for efficient lookup
        project_map = {p["key"]: p for p in projects_data}

        # Process each group
        for group in groups:
            group_projects = []

            # Add projects to group
            for project_key in group.get("projects", []):
                if project_key in project_map:
                    group_projects.append(project_map[project_key])
                    # Mark project as processed
                    project_map.pop(project_key)

            # Calculate group status
            group_data = {
                "name": group.get("name", "Unnamed Group"),
                "projects": group_projects,
                "status": self._calculate_group_status(group_projects),
            }

            grouped_projects["groups"].append(group_data)

        # Add remaining projects to ungrouped section with status
        ungrouped_projects = list(project_map.values())
        grouped_projects["ungrouped"] = ungrouped_projects
        grouped_projects["ungrouped_status"] = self._calculate_group_status(
            ungrouped_projects
        )

        logger.info(
            f"Processed {len(groups)} groups and {len(ungrouped_projects)} ungrouped projects"
        )
        return grouped_projects
