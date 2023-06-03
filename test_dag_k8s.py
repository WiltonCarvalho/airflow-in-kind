from airflow import DAG
from datetime import datetime, timedelta
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.operators.dummy_operator import DummyOperator
import pendulum

local_tz = pendulum.timezone("America/Sao_Paulo")

default_args = {
  'owner': 'airflow',
  'depends_on_past': False,
  'start_date': datetime(2023, 6, 1, 20, 0, tzinfo=local_tz),
  'email': ['airflow@example.com'],
  'email_on_failure': False,
  'email_on_retry': False,
  'retries': 0,
  'retry_delay': timedelta(minutes=3)
}

dag = DAG('01_k8s', default_args=default_args, schedule_interval=timedelta(minutes=5), max_active_runs=1, catchup=False, tags=['01_test'])

first_task = DummyOperator(task_id='first-task', dag=dag)

script = """
set -ex
ps axu
python -c "print('[PYTHON TASK] Hello world!')"
exec sleep 120
"""
# Create a kubernetes pod using a python image
python_task = KubernetesPodOperator(namespace='airflow',
                                    image="python:3-alpine",
                                    cmds=["sh", "-c", script],
                                    #cmds=["python","-c"],
                                    #arguments=["print('[PYTHON TASK] Hello world!')"],
                                    labels={"foo": "bar"},
                                    name="python-k8s-task",
                                    task_id="python-task",
                                    get_logs=True,
                                    dag=dag
)

# Create a kubernetes pod using an ubuntu image
bash_task = KubernetesPodOperator(namespace='airflow',
                                  image="ubuntu:22.04",
                                  cmds=["echo"],
                                  arguments=["[BASH TASK] Hi world!"],
                                  labels={"foo": "bar"},
                                  name="bash-k8s-task",
                                  task_id="bash-task",
                                  get_logs=True,
                                  dag=dag
)

# Create a kubernetes pod using a nodejs image
node_task = KubernetesPodOperator(namespace='airflow',
                                  image="node:18-slim",
                                  cmds=["node", "-e"],
                                  arguments=["console.log('[NODEJS TASK] Hey world!')"],
                                  labels={"foo": "bar"},
                                  name="nodejs-k8s-task",
                                  task_id="nodejs-task",
                                  get_logs=True,
                                  dag=dag
)
# Create a kubernetes pod using a java image
java_task = KubernetesPodOperator(namespace='airflow',
                                  image="amazoncorretto:17",
                                  cmds=["java", "-version"],
                                  #arguments=[""],
                                  labels={"foo": "bar"},
                                  name="java-k8s-task",
                                  task_id="java-task",
                                  get_logs=True,
                                  dag=dag
)

# Define the order of the tasks in the DAG
# python_task.set_upstream(first_task)
# bash_task.set_upstream(python_task)
# node_task.set_upstream(python_task)
# java_task.set_upstream([bash_task, node_task])
first_task >> python_task >> [bash_task, node_task] >> java_task