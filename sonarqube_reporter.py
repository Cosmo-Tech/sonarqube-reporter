#!/usr/bin/env python3
"""
SonarQube Reporter - Main Script

Generates HTML reports from SonarQube data for compliance/auditing and project management.
"""

import os
import sys
import argparse
import logging
from datetime import datetime

from src.config import Config
from src.sonarqube_client import SonarQubeClient
from src.data_processor import DataProcessor
from src.report_generator import ReportGenerator

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Generate reports from SonarQube data.')
    
    parser.add_argument('--config', '-c', default='config.ini',
                        help='Path to configuration file (default: config.ini)')
    
    parser.add_argument('--detailed-only', action='store_true',
                        help='Generate only the detailed compliance/auditing report')
    
    parser.add_argument('--quality-gate-only', action='store_true',
                        help='Generate only the quality gate report')
    
    parser.add_argument('--output-dir', '-o',
                        help='Output directory for reports (overrides config file)')
    
    return parser.parse_args()


def main():
    """Main function."""
    # Parse command-line arguments
    args = parse_arguments()
    
    try:
        # Load configuration
        logger.info(f"Loading configuration from {args.config}")
        config = Config(args.config)
        
        # Override output directory if specified
        if args.output_dir:
            config.config.set('reports', 'output_dir', args.output_dir)
            os.makedirs(args.output_dir, exist_ok=True)
        
        # Initialize SonarQube client
        logger.info(f"Connecting to SonarQube server at {config.get_sonarqube_url()}")
        client = SonarQubeClient(config.get_sonarqube_url(), config.get_sonarqube_token())
        
        # Initialize data processor
        data_processor = DataProcessor(client)
        
        # Get projects data
        logger.info("Retrieving projects data from SonarQube")
        projects_data = data_processor.get_all_projects_data()
        
        if not projects_data:
            logger.warning("No projects found in SonarQube")
            return
        
        logger.info(f"Found {len(projects_data)} projects")
        
        # Get detailed data for each project
        detailed_data = {}
        if not args.quality_gate_only:
            logger.info("Retrieving detailed data for each project")
            for project in projects_data:
                project_key = project['key']
                logger.info(f"Processing detailed data for project: {project['name']} ({project_key})")
                detailed_data[project_key] = data_processor.get_detailed_project_data(project_key)
        
        # Calculate summary statistics
        summary_statistics = data_processor.calculate_summary_statistics(
            [detailed_data.get(p['key'], p) for p in projects_data]
        )
        
        # Initialize report generator
        report_generator = ReportGenerator(config)
        
        # Generate reports
        if not args.detailed_only:
            logger.info("Generating quality gate report")
            quality_gate_report_path = report_generator.generate_quality_gate_report(projects_data)
            logger.info(f"Quality gate report generated: {quality_gate_report_path}")
        
        if not args.quality_gate_only:
            logger.info("Generating detailed compliance/auditing report")
            detailed_report_path = report_generator.generate_detailed_report(
                projects_data, detailed_data, summary_statistics
            )
            logger.info(f"Detailed report generated: {detailed_report_path}")
        
        logger.info("Report generation completed successfully")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())