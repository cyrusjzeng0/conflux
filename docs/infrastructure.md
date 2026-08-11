# Conflux - Infrastructure Guide

This doc provides a summary of Docker, `docker-compose.yml`, how it runs Kafka and Clickhouse locally and the concepts behind each setting.

## Docker Overview

Docker is used to package applications and all its parts (like code, settings and tool) into _containers_, which makes it easy to launch and scale apps. One neat feature is that by downloading _images_ of external applications entirely through Docker, you can run them without ever needing to download or configure them locally. We use this feature to get access to Kafka and Clickhouse (more on these later).

Some terminology:

- **Container** = a lightweight box running one application without installing it locally.
- **Image** = a template for a container, e.g apache/kafka:3.8.0 (Apache Kafka version 3.8.0.)
- **Port** = a virtual communication endpoint used by OS to route network data to specific programs.
- **Docker Hub** = cloud-based registry where devs find, share and store Docker images. Often used to host images for widely-used apps like Python, Kafka, etc.

## Docker Compose Overview

Docker Compose is a tool within Docker allowing you to define and run multi-container apps using a single configuration file. This config file does each of the following:

- Launches the app and any containers simultaneously on command.
- Creates a _shared private network_ for all containers to allow them to talk to each other naturally (this also means extra config is required to allow the local machine to talk to the network).
- _Configures environment variables_ by storing all system ports and configuration settings.
- _Controls startup order_; for example, ensuring DB is running before the application tries to connect to it so no crashes occur.

This file is `docker-compose.yml`. In our case, it tells Docker to run Clickhouse and Kafka, which ports they use to connect to the local machine (my Mac) and where their data is stored. It is written using YAML syntax.

Some basic Docker / Docker Compose commands:

```bash
docker compose up -d # start up Docker; d = run in background
docker compose down # stop Docker
docker compose down -v # fresh start; wipe all stored data
docker compose logs -f # streams live consolidated logs from all running containers to terminal. can add 'kafka' or 'clickhouse' after to specify
docker ps # lists currently running Docker containers
```

## Project Structure

Flow: `Producer → Kafka → Spark → ClickHouse → API/UI`

```
┌──────────────────────────────────────────────────────────────┐
│  LOCAL MACHINE                                               │
│                                                              │
│  producer/generate-events.py   ──► localhost:9092            │
│                                                              │
│  spark_jobs / (PySpark)        ──► localhost:9092  (read)    │
│                                ──► localhost:8123 or 9000    │
│                                    (write aggregates)        │
│                                                              │
│  UI / API                      ──► localhost:8123  (read)    │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Docker (private network)                              │  │
│  │                                                        │  │
│  │   Kafka ◄── raw JSON events                            │  │
│  │   port 9092                                            │  │
│  │                                                        │  │
│  │   ClickHouse ◄── aggregated metrics tables             │  │
│  │   ports 8123 / 9000                                    │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

Shown above, the Python event generation script communicates with Kafka via 9092:9092 connection, and the UI / API communicates with Clickhouse via 8123:8123.

Technologies used include Spark (run on local machine), and Kafka and ClickHouse (run via Docker) as described below:

- **Spark** is used to turn the raw JSON events into metrics that can be appended to the ClickHouse DB. Carries out stream processing.
- **Kafka** is an event buffer for producers (generate-events.py) and consumers (Spark).
- **Clickhouse** is an OLAP columnar DB which stores aggregated metrics for fast querying; serves as analytics store for UI.

In the Docker Compose network, Kafka acts as a server (serving data to Spark) while Clickhouse acts as a client (requesting data from Spark). Only servers are required to list the ports they listen on, which is why 29092 is only listed in kafka, not clickhouse.

## `docker-compose.yml` in depth

As stated above, `docker-compose.yml` is used to give Docker important info regarding which external images we want to use and how to use them. Here's a high-level line-by-line breakdown:

### Common Fields

- `image`: download + run official image (e.g Apache Kafka v3.8.0) from Docker Hub.
- `container_name`: fixes an identifiable container name in `docker ps` and logs
- `ports`: expose container's external listener port to localhost; maps localhost ports to container ports e.g 9092:9092. Acts as input port for Kafka (generate-events.py -> Kafka for data ingestion), list of output ports for ClickHouse (ClickHouse -> API / UI for data analytics / dashboarding).
- `volumes`: stores where database files persist. e.g `kafka-data:/var/lib/kafka/data` -> data persists at `/var/lib/...` in volume named `kafka-data`.

### Kafka Environment

Used to configure Kafka at startup without editing container files.

- `KAFKA_NODE_ID`: single node's ID in cluster. A node is a broker, and a cluster is a group of brokers. In this case, we have one node - so we need one broker with ID 1.
- `KAFKA_PROCESS_ROLES`: `broker` stores messages + serves producers / consumers; `controller` manages metadata (e.g topics, partitions, leaders). Each partition has a leader broker that "leads" reads / writes for that shard.
- `LISTENERS` group: establishes where Kafka opens sockets inside the Docker container. `PLAINTEXT` = internal client door (communication between containers e.g Kafka and ClickHouse); `CONTROLLER` = KRaft internal metadata coordination; `EXTERNAL` = communication between Docker network and localhost.
  - `KAFKA_LISTENERS`: addresses where server binds. `0.0.0.0` -> listen on all interfaces inside the container.
  - `KAFKA_ADVERTISED_LISTENERS`: addresses Kafka tells clients to use after they connect. Mac clients advertise localhost; container clients advertise kafka.
  - `KAFKA_LISTENER_SECURITY_PROTOCOL_MAP`: maps each listener name to a security protocol. `PLAINTEXT` protocol -> no encryption, which is efficient for local development. `PLAINTEXT` protocol ≠ `PLAINTEXT` listener.

### ClickHouse ulimits.nofile

Establishes how many files ClickHouse can open simultaneously (columnar DB -> many small files kept per table). This sets a safe limit for DB workload.
