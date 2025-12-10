FROM public.ecr.aws/lambda/python:3.10

# 1. Install Java 17 and procps (Process tools required by Spark)
RUN yum update -y && \
    yum install -y java-17-amazon-corretto-headless procps && \
    yum clean all

# 2. Set Java Environment Variables
ENV JAVA_HOME="/usr/lib/jvm/java-17-amazon-corretto"
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# 3. Configure Spark Network & Storage 
# 127.0.0.1: Prevents Spark from trying to open public ports (crashes Lambda)
# /tmp: The ONLY writable folder in Lambda. Spark needs this to write temp files.
ENV SPARK_DRIVER_BINDADDRESS="127.0.0.1"
ENV SPARK_LOCAL_IP="127.0.0.1"
ENV SPARK_LOCAL_DIRS="/tmp"

# 4. Install PySpark 3.4.1 (FIX: 3.5.0 script is incompatible with Lambda)
# We use 3.4.1 because its launch script doesn't use /dev/fd
RUN pip install --default-timeout=1000 --no-cache-dir pyspark==3.4.1

# 5. Copy the application code
COPY app.py ${LAMBDA_TASK_ROOT}

# 6. Set the Docker entrypoint
CMD ["app.lambda_handler"]