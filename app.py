import json
import os
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("LambdaSpark") \
    .master("local[*]") \
    .config("spark.driver.bindAddress", "127.0.0.1") \
    .config("spark.ui.enabled", "false") \
    .getOrCreate()


data = [("James", "Sales", 3000),
        ("Michael", "Sales", 4600),
        ("Robert", "Sales", 4100),
        ("Maria", "Finance", 3000)]
columns = ["EmployeeName", "Department", "Salary"]
base_df = spark.createDataFrame(data, columns)

def lambda_handler(event, context):
    try:
        # 1. Parse Query Parameters
        params = event.get("queryStringParameters") or {}
        dept_filter = params.get("dept")  # e.g., ?dept=Sales


        df = base_df


        if dept_filter:
            df = df.filter(df.Department == dept_filter)


        avg_salary = df.agg({"Salary": "avg"}).collect()[0][0]


        result_rows = [row.asDict() for row in df.collect()]


        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "message": "PySpark is working!",
                "filter_applied": dept_filter if dept_filter else "None",
                "employee_count": df.count(),
                "average_salary": avg_salary,
                "data": result_rows
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": str(e),
                "type": type(e).__name__
            })
        }