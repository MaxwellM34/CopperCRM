# Extend the official Mautic image and bake in local scripts/config so Cloud Build
# can produce a deployable image without bind mounts.
ARG MAUTIC_IMAGE=mautic/mautic:5.0.3-apache
FROM ${MAUTIC_IMAGE}

ENV MAUTIC_CUSTOM_DIR=/opt/mautic

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR ${MAUTIC_CUSTOM_DIR}

COPY scripts/requirements.txt ${MAUTIC_CUSTOM_DIR}/scripts/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r ${MAUTIC_CUSTOM_DIR}/scripts/requirements.txt

COPY scripts ${MAUTIC_CUSTOM_DIR}/scripts
COPY cron ${MAUTIC_CUSTOM_DIR}/cron
COPY backup ${MAUTIC_CUSTOM_DIR}/backup
COPY static ${MAUTIC_CUSTOM_DIR}/static

RUN chmod +x ${MAUTIC_CUSTOM_DIR}/backup/backup_mautic.sh \
    ${MAUTIC_CUSTOM_DIR}/cron/install_cron.sh \
    ${MAUTIC_CUSTOM_DIR}/scripts/sql/run_lead_cleanup.sh || true
