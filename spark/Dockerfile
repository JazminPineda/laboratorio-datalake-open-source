FROM apache/spark:3.5.8-scala2.12-java17-python3-ubuntu

USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y --no-install-recommends python3.12 python3.12-dev && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 2 && \
    rm -rf /var/lib/apt/lists/*

USER spark
