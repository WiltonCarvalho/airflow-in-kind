from airflow import DAG
from datetime import datetime
from airflow.operators.python import PythonOperator
import pendulum

local_tz = pendulum.timezone("America/Sao_Paulo")

def print_message():
  print("HELLO WORLD!!!")

with DAG("01_basic", start_date=datetime(2023, 6, 1, 20, 0, tzinfo=local_tz), schedule_interval="*/5 * * * *", max_active_runs=1, tags=['01_test']) as dag:
  task = PythonOperator(task_id="dag_basic",
                        python_callable=print_message
  )

task