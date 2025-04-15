# SonarQube Reporter

A Python tool to generate a quality gate report from SonarQube data.It creates a simple html report with the quality gate status selected projects using the sonarqube web-api

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
Adapt the `report-config.yaml` example file and run the script

Create a script `report.sh`

```shell
#!/bin/bash
set -ex
export SONARQUBE_REPORT_TOKEN=your_sonarqube_token
cd /home/terminator/sonarqube-reporter
. .venv/bin/activate
sonarqube-reporter
cp -r reports/* /var/www/html/reports

```

Configure crontab by running `crontab -e` and adapt the following:

```
0 1 * * * * /home/terminator/sonarqube-reporter/report.sh > sonarqube_reporter_last_run.log 2>&1
```