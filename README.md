# Engineering Log: Serverless Spark Implementation

## Context: The objective was to deploy Apache Spark (PySpark) on AWS Lambda to enable serverless data processing. This architecture is non-standard due to the heavy JVM dependency and the strict resource constraints of the Lambda sandbox.

This log documents the architectural hurdles encountered during the build process, the specific error signatures observed, and the solutions implemented to resolve them.

## 1. Architecture Mismatch (ARM64 vs. AMD64)
Observation: The Docker image was built locally on an Apple Silicon (M1/M2) machine. Upon deployment to AWS, the Lambda function failed immediately during initialization.

Error Signature: exec /usr/local/bin/python: exec format error

Root Cause: AWS Lambda runs on the x86_64 instruction set. The local build produced an ARM64 binary, resulting in binary incompatibility at the OS level.

Resolution: We implemented cross-compilation in the build pipeline using Docker Buildx, forcing the target platform to Linux AMD64 regardless of the host machine's architecture.

Command: docker buildx build --platform linux/amd64 ...

## 2. OCI Metadata Incompatibility
Observation: After resolving the architecture mismatch, AWS ECR accepted the push, but the Lambda service refused to create a function from the image.

Error Signature: The image manifest, config or layer media type ... is not supported.

Root Cause: Newer versions of Docker Desktop default to the OCI Image Format, which includes "provenance" (attestation) metadata. The AWS Lambda container runtime relies on the legacy Docker V2 Schema 2 format and cannot parse OCI-compliant manifests.

Resolution: We modified the build command to explicitly strip build attestations and force the legacy schema.

Flag: --provenance=false

## 3. Build-Time Network Latency
Observation: The Docker build process consistently failed during the installation of the PySpark library.

Error Signature: ReadTimeoutError: HTTPSConnectionPool(host='files.pythonhosted.org', port=443): Read timed out.

Root Cause: PySpark is a significant artifact (~317MB). The default socket timeout for pip is insufficient for handling large binary downloads over variable network connections within a containerized build environment.

Resolution: We configured the package manager to increase the default timeout tolerance.

Configuration: pip install --default-timeout=1000 pyspark==3.5.0

## 4. Resource Starvation (Cold Start Failure)
Observation: The function deployed successfully, but invocation resulted in immediate timeouts or generic 502 errors.

Error Signature: Task timed out after 3.00 seconds

Root Cause: The JVM startup overhead for Spark is approximately 10-15 seconds. The default AWS Lambda configuration (128MB RAM, 3s timeout) is insufficient to bootstrap the SparkContext.

Resolution: We rightsized the Lambda configuration to accommodate the JVM heap and initialization time.

Memory: Increased to 2048 MB.

Timeout: Increased to 60 seconds.

## 5. Current Blocker: Sandbox Runtime Incompatibility
Observation: With resources provisioned, the function now attempts to initialize but crashes during the PySpark launch sequence.

Error Logs:

/dev/fd/62: No such file or directory

CMD: bad array subscript

Java gateway process exited before sending its port number

Analysis: This indicates a conflict between the PySpark 3.5.0 launch script and the AWS Lambda security sandbox.

The script uses Linux Process Substitution (reading from /dev/fd/).

AWS Lambda restricts access to file descriptors for security isolation, causing the script to fail before the Java Gateway can initialize.

Proposed Next Steps: We are currently evaluating two remediation strategies:

Patching: Manually modifying the spark-class script during the Docker build (using sed) to remove the incompatible shell code.

Downgrade: Reverting to PySpark 3.4.1, which utilizes a simpler launch mechanism known to be compatible with the Lambda environment.