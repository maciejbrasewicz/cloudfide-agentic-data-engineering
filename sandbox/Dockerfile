# Trusted sandbox image: candidate source is NOT copied or built into this image.
# Only this static, source-reviewed build has network access to install pins.
FROM python:3.12-slim
RUN python -m pip install --no-cache-dir --disable-pip-version-check \
    pandas==2.3.3 numpy==2.5.5 pytest==9.2.0 \
    pydantic==2.14.3 pandera==0.29.0 hypothesis==6.170.15
COPY run-candidate.sh /opt/cloudfide/run-candidate.sh
RUN chmod 0555 /opt/cloudfide/run-candidate.sh
ENV PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
    PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1
USER 65534:65534
ENTRYPOINT ["/bin/sh", "/opt/cloudfide/run-candidate.sh"]
