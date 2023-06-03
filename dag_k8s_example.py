import logging
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator

log = logging.getLogger(__name__)

dag = DAG(
    "example_using_k8s_pod_operator",
    schedule_interval="0 1 * * *",
    max_active_runs=1,
    catchup=False,
    default_args={
        "owner": "admin",
        "depends_on_past": False,
        "start_date": datetime(2020, 8, 7),
        "email_on_failure": False,
        "email_on_retry": False,
        "retries": 2,
        "retry_delay": timedelta(seconds=30),
        "sla": timedelta(hours=23),
    },
)

with dag:
    task_1 = KubernetesPodOperator(
        image="ubuntu:16.04",
        namespace="airflow-k8spodoperator",
        cmds=["bash", "-cx"],
        arguments=["echo", "10"],
        labels={"foo": "bar"},
        name="test-using-k8spodoperator-task-1",
        task_id="task-1-echo",
        is_delete_operator_pod=False,
        in_cluster=True,
    )
    task_2 = KubernetesPodOperator(
        image="ubuntu:16.04",
        namespace="airflow-k8spodoperator",
        cmds=["sleep"],
        arguments=["300"],
        labels={"foo": "bar"},
        name="test-using-k8spodoperator-task-2",
        task_id="task-2-sleep",
        is_delete_operator_pod=False,
        in_cluster=True,
    )

secret_file = Secret('volume', '/etc/sql_conn', 'airflow-secrets', 'sql_alchemy_conn')
secret_env  = Secret('env', 'SQL_CONN', 'airflow-secrets', 'sql_alchemy_conn')
secret_all_keys  = Secret('env', None, 'airflow-secrets-2')
volume_mount = VolumeMount('test-volume', mount_path='/root/mount_file', sub_path=None, read_only=True)
port = Port('http', 80)
configmaps = ['test-configmap-1', 'test-configmap-2']
volume_config = { 'persistentVolumeClaim': { 'claimName': 'test-volume' } }
volume = Volume(name='test-volume', configs=volume_config)
with dag:
    k = KubernetesPodOperator(namespace='default',
                                image="ubuntu:16.04",
                                cmds=["bash", "-cx"],
                                arguments=["echo", "10"],
                                labels={"foo": "bar"},
                                secrets=[secret_file, secret_env, secret_all_keys],
                                ports=[port],
                                volumes=[volume],
                                volume_mounts=[volume_mount],
                                name="test",
                                task_id="task",
                                affinity=affinity,
                                is_delete_operator_pod=True,
                                hostnetwork=False,
                                tolerations=tolerations,
                                configmaps=configmaps
    )

task_1 >> task_2