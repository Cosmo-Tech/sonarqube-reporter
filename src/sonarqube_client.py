import requests
from requests.auth import HTTPBasicAuth
import logging

# Set up logging
logger = logging.getLogger(__name__)


class SonarQubeClient:
    """Client for interacting with the SonarQube API."""

    def __init__(self, url, token):
        """
        Initialize the SonarQube API client.

        Args:
            url (str): The base URL of the SonarQube server.
            token (str): The authentication token for the SonarQube API.
        """
        self.base_url = url
        self.token = token
        
        # Debug token information
        if not token:
            logger.error("SonarQube token is None. Please set the SONARQUBE_REPORT_TOKEN environment variable.")
            raise ValueError("SonarQube token is None. Please set the SONARQUBE_REPORT_TOKEN environment variable.")
        else:
            # Mask the token for security in logs
            masked_token = token[:4] + '*' * (len(token) - 8) + token[-4:] if len(token) > 8 else '****'
            logger.debug(f"Using SonarQube token: {masked_token}")
        
        self.auth = HTTPBasicAuth(token, '')
        self.session = requests.Session()
        self.session.auth = self.auth
        
        # Test connection
        self.test_connection()

    def test_connection(self):
        """Test the connection to the SonarQube server."""
        try:
            logger.debug(f"Testing connection to SonarQube server at {self.base_url}")
            response = self.session.get(f"{self.base_url}/api/system/status")
            response.raise_for_status()
            status_info = response.json()
            logger.info(f"Successfully connected to SonarQube server at {self.base_url}")
            logger.debug(f"SonarQube server status: {status_info}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to SonarQube server: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.debug(f"Response status code: {e.response.status_code}")
                logger.debug(f"Response content: {e.response.text}")
            raise ConnectionError(f"Could not connect to SonarQube server at {self.base_url}: {e}")

    def _make_request(self, endpoint, method="GET", params=None, data=None):
        """
        Make a request to the SonarQube API.

        Args:
            endpoint (str): The API endpoint to request.
            method (str): The HTTP method to use (GET, POST, etc.).
            params (dict, optional): Query parameters for the request.
            data (dict, optional): Data to send in the request body.

        Returns:
            dict: The JSON response from the API.
        """
        url = f"{self.base_url}{endpoint}"
        
        logger.debug(f"Making {method} request to {endpoint}")
        if params:
            logger.debug(f"Request parameters: {params}")
        if data:
            logger.debug(f"Request data: {data}")
        
        try:
            if method == "GET":
                response = self.session.get(url, params=params)
            elif method == "POST":
                response = self.session.post(url, params=params, json=data)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            json_response = response.json()
            logger.debug(f"API request successful: {endpoint}")
            return json_response
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status code: {e.response.status_code}")
                logger.error(f"Response content: {e.response.text}")
            raise

    def get_projects(self, page_size=500):
        """
        Get all projects from SonarQube.

        Args:
            page_size (int): Number of projects to fetch per page.

        Returns:
            list: List of project dictionaries.
        """
        logger.debug(f"Fetching all projects with page size {page_size}")
        projects = []
        page = 1
        
        while True:
            logger.debug(f"Fetching projects page {page}")
            params = {
                'p': page,
                'ps': page_size
            }
            
            response = self._make_request("/api/projects/search", params=params)
            
            components = response.get('components', [])
            if not components:
                logger.debug(f"No more projects found on page {page}")
                break
            
            logger.debug(f"Found {len(components)} projects on page {page}")
            projects.extend(components)
            
            if len(components) < page_size:
                logger.debug(f"Reached last page of projects (page {page})")
                break
                
            page += 1
        
        logger.info(f"Retrieved {len(projects)} projects from SonarQube")
        return projects

    def get_quality_gate_status(self, project_key):
        """
        Get the quality gate status for a project.

        Args:
            project_key (str): The project key.

        Returns:
            dict: Quality gate status information.
        """
        params = {
            'projectKey': project_key
        }
        
        response = self._make_request("/api/qualitygates/project_status", params=params)
        return response.get('projectStatus', {})
        
    def get_project_analyses(self, project_key, max_count=10):
        """
        Get the analysis history for a project.
        
        Args:
            project_key (str): The project key.
            max_count (int): Maximum number of analyses to retrieve.
            
        Returns:
            list: List of analysis data dictionaries.
        """
        params = {
            'project': project_key,
            'ps': max_count
        }
        
        response = self._make_request("/api/project_analyses/search", params=params)
        return response.get('analyses', [])
        
    def get_quality_gate_history(self, project_key, max_count=10):
        """
        Get the quality gate status history for a project.
        
        Args:
            project_key (str): The project key.
            max_count (int): Maximum number of historical statuses to retrieve.
            
        Returns:
            list: List of historical quality gate statuses.
        """
        analyses = self.get_project_analyses(project_key, max_count)
        history = []
        
        for analysis in analyses:
            analysis_key = analysis.get('key')
            if not analysis_key:
                continue
                
            params = {
                'analysisId': analysis_key
            }
            
            try:
                response = self._make_request("/api/qualitygates/project_status", params=params)
                status = response.get('projectStatus', {}).get('status')
                if status:
                    history.append({
                        'date': analysis.get('date'),
                        'status': status
                    })
            except Exception as e:
                logger.error(f"Error getting quality gate status for analysis {analysis_key}: {e}")
                
        return history