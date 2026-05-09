# Infraestructura de Ingesta y Base de Datos (ELT) en Docker

[English](./README.en.md)

Este proyecto despliega un laboratorio local diseñado para implementar una capa de ingesta de datos robusta, escalable y basada íntegramente en tecnologías de código abierto. El enfoque principal es establecer los cimientos técnicos de un Data Lake —cubriendo el almacenamiento de objetos, el formato de tabla y la catalogación— antes de escalar hacia capas de analítica o gobernanza.

A diferencia de las implementaciones teóricas, este repositorio aborda directamente fallos reales de integración, como discrepancias de versiones en entornos Python y configuraciones críticas de catálogos y particiones.

**Objetivos y Tecnologías Core**
El laboratorio levanta un entorno de nodo único mediante Docker Compose que integra:

* Capa de Almacenamiento: RustFS (Object Storage).

* Formato de Tabla y Catálogo: Apache Iceberg gestionado a través de Project Nessie para control de versiones de datos.

* Orquestación y Procesamiento: Apache Airflow gestionando procesos por lotes (Batch) con PySpark.

* Patrón de Ingesta Real: Desacoplamiento de procesos mediante Redis, utilizando un web scraper externo que interactúa con tablas de señales (signals).

**Alcance del Proyecto:** Este laboratorio se centra estrictamente en la "E" (Extracción) y la base de la carga dentro de un flujo ELT.

**Incluido:** Configuración de infraestructura, gestión de metadatos, particionamiento de tablas Iceberg y orquestación de la ingesta.

**Fuera de alcance:** Transformaciones complejas (dbt), motores de consulta distribuida (Trino) o visualización (Superset). Estas herramientas representan la capa subsiguiente que se apoyará sobre la base construida aquí.
