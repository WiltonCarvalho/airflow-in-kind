FROM apache/airflow:2.6.1-python3.10
ENV TZ=America/Sao_Paulo
# RUN set -ex \
#     &&  AIRFLOW_VERSION=2.6.1 \
#         PYTHON_VERSION="$(python --version | cut -d " " -f 2 | cut -d "." -f 1-2)" \
#         CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt" \
#     && pip install --no-cache-dir "apache-airflow[kubernetes,mysql]==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"
COPY --chown=airflow:root pod_template.yaml /opt/airflow/pod_template.yaml