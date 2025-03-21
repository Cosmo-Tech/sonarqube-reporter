"""
Report generation module for SonarQube Reporter.
Generates a quality gate report from processed SonarQube data.
"""

import os
import logging
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from rich.logging import RichHandler

# Set up logging
logger = logging.getLogger("sonarqube_reporter")


class ReportGenerator:
    """Generates a quality gate report from processed SonarQube data."""

    def __init__(self, config, templates_dir="templates"):
        """
        Initialize the report generator.

        Args:
            config (Config): Configuration object.
            templates_dir (str): Directory containing HTML templates.
        """
        self.config = config
        self.sonarqube_url = config.get_sonarqube_url()
        self.styling = config.get_styling()
        
        # Set up Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=True
        )
        
        # Add custom filters
        self.env.filters['format_date'] = self._format_date
        self.env.filters['status_to_color'] = self._status_to_color

    def generate_quality_gate_report(self, projects_data_tuple):
        """
        Generate a quality gate report.

        Args:
            projects_data_tuple (tuple): Tuple containing (projects_data, overall_status).

        Returns:
            str: Path to the generated report.
        """
        projects_data, overall_status = projects_data_tuple
            
        logger.debug("Loading quality gate report template")
        template = self.env.get_template('quality_gate_report.html')
        
        # Prepare template context
        generation_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.debug(f"Report generation date: {generation_date}")
        
        # Determine title based on overall status
        if overall_status:
            title = f"[{overall_status['label']}] SonarQube Quality Gate Report"
        else:
            title = 'SonarQube Quality Gate Report'
        
        context = {
            'title': title,
            'generation_date': generation_date,
            'sonarqube_url': self.sonarqube_url,
            'projects': projects_data,
            'styling': self.styling,
            'overall_status': overall_status
        }
        
        # Render template
        logger.debug("Rendering quality gate report template")
        html = template.render(**context)
        
        # Create reports directory if it doesn't exist
        output_path = self.config.get_quality_gate_report_path()
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)
        
        # Create CSS directory in reports
        css_dir = os.path.join(output_dir, 'css')
        os.makedirs(css_dir, exist_ok=True)
        
        # Copy CSS file
        css_source = os.path.join(os.path.dirname(self.env.loader.searchpath[0]), 'templates', 'css', 'report_styles.css')
        css_dest = os.path.join(css_dir, 'report_styles.css')
        
        logger.debug(f"Copying CSS file from {css_source} to {css_dest}")
        try:
            with open(css_source, 'r', encoding='utf-8') as src_file:
                css_content = src_file.read()
                
            with open(css_dest, 'w', encoding='utf-8') as dest_file:
                dest_file.write(css_content)
        except Exception as e:
            logger.error(f"Error copying CSS file: {str(e)}")
        
        # Write HTML to file
        logger.debug(f"Writing quality gate report to: {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"Generated quality gate report: {output_path}")
        return output_path

    def _format_date(self, date_string):
        """
        Format a date string for display in reports.

        Args:
            date_string (str): Date string.

        Returns:
            str: Formatted date string.
        """
        if not date_string or date_string == 'N/A':
            logger.debug(f"Empty or N/A date string, returning N/A")
            return 'N/A'
        
        try:
            date_obj = datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')
            formatted_date = date_obj.strftime('%b %d, %Y %H:%M')
            logger.debug(f"Formatted date for display: {date_string} -> {formatted_date}")
            return formatted_date
        except ValueError as e:
            logger.debug(f"Error formatting date {date_string} for display: {str(e)}")
            return date_string

    def _status_to_color(self, status):
        """
        Convert a status to a color.

        Args:
            status (str): Status string (OK, ERROR, WARN, etc.).

        Returns:
            str: Color hex code.
        """
        status_map = {
            'OK': self.styling['pass_color'],
            'ERROR': self.styling['fail_color'],
            'WARN': self.styling['warning_color']
        }
        
        color = status_map.get(status, '#999')
        logger.debug(f"Status to color mapping: {status} -> {color}")
        return color