# bookworm fijado: trixie ya no empaqueta OpenJDK 17 (Spark 3.5 soporta hasta Java 17)
FROM python:3.11-slim-bookworm

# Java para Spark
RUN apt-get update \
 && apt-get install -y --no-install-recommends openjdk-17-jre-headless curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Conector Kafka de Spark (se hornea en la imagen: sin --packages en runtime)
ARG SPARK_VERSION=3.5.3
ARG SCALA=2.12
RUN SPARK_JARS=$(python -c "import pyspark, os; print(os.path.join(os.path.dirname(pyspark.__file__), 'jars'))") \
 && curl -fsSL -o "$SPARK_JARS/spark-sql-kafka-0-10_${SCALA}-${SPARK_VERSION}.jar" \
      "https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_${SCALA}/${SPARK_VERSION}/spark-sql-kafka-0-10_${SCALA}-${SPARK_VERSION}.jar" \
 && curl -fsSL -o "$SPARK_JARS/spark-token-provider-kafka-0-10_${SCALA}-${SPARK_VERSION}.jar" \
      "https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_${SCALA}/${SPARK_VERSION}/spark-token-provider-kafka-0-10_${SCALA}-${SPARK_VERSION}.jar" \
 && curl -fsSL -o "$SPARK_JARS/kafka-clients-3.4.1.jar" \
      "https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.4.1/kafka-clients-3.4.1.jar" \
 && curl -fsSL -o "$SPARK_JARS/commons-pool2-2.11.1.jar" \
      "https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.11.1/commons-pool2-2.11.1.jar"

COPY app/ .

CMD ["python", "streaming_job.py"]
