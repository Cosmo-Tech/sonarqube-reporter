# SonarQube Reporter

A Python tool to generate a quality gate report from SonarQube data.It creates a simple html report with the quality gate status for each project using the sonarqube web-api

## Requirements

- Python 3.6+
- SonarQube Community Edition (or higher)
- Access token for SonarQube API

## Installation and setup

### Installation

```bash
uv venv
uv pip install .
```

```bash
# Set the environment variable
export SONARQUBE_REPORT_TOKEN=your_sonarqube_token

# Run the script to generate the quality gate report
python sonarqube_reporter.py
```

The report will be generated in the `./reports` directory.

Configure crontabl by running `crontab -e` and adapt the following:

```
0 1 * * * export SONARQUBE_TOKEN=<replace with Global Scan Token>; PATH=$PATH:/usr/local/bin; $HOME/sonarqube-reporter/.venv/bin/sonarqube-reporter > $HOME/sonarqube_reporter_last_run.log 2&>1
```