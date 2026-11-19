#!/bin/sh
# This is a trusted static runner script baked into the pinned sandbox image.
# Everything in /input is untrusted model-produced code or original fixtures.
# This process runs with NO network, NO Azure secrets, NO writeable host repo.
set -u
mkdir -p /tmp/cloudfide-candidate
cp -R /input/. /tmp/cloudfide-candidate/
cd /tmp/cloudfide-candidate || exit 90
python -m pytest -q test_virtual_column.py tests > /out/tests.log 2>&1
tests_result=$?
printf "%s\n" "$tests_result" > /out/test_exit_code.txt
if [ "$tests_result" -eq 0 ]; then
    python pipeline.py --input sales.csv --output /out/revenue_by_region.csv > /out/pipeline.log 2>&1
    pipeline_result=$?
else
    printf "%s\n" "Pipeline not started: candidate tests failed" > /out/pipeline.log
    pipeline_result=98
fi
printf "%s\n" "$pipeline_result" > /out/pipeline_exit_code.txt
# Return 0 so an independent, TRUSTED P3 oracle always decides success/failure.
exit 0
