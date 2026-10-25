#!/bin/bash
# Full QC run. Each run gets its own throwaway DB (krishnalens_qc_<suffix>),
# which conftest.py drops at the end. Extra args go to pytest.
cd "$(dirname "$0")"
mkdir -p reports
.venv/bin/python -m pytest "$@" --junitxml=reports/last_run.xml
