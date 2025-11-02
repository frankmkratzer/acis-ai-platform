#!/bin/bash
#
# Daily End-of-Day Pipeline
# Runs after market close (6 PM Pacific)
# - Refreshes materialized views
# - Trains all ML models
# - Performs database maintenance
# - Generates summary reports
#

# Run the comprehensive EOD pipeline
/home/fkratzer/acis-ai-platform/scripts/run_eod_pipeline.sh

exit $?
