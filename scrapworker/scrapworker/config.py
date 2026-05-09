import os
import yaml


def load_config() -> dict:
    path = os.environ.get("CONFIG_PATH", "config/config.yaml")
    with open(path) as f:
        config = yaml.safe_load(f)
    config["rustfs"]["access_key"] = os.environ["RUSTFS_ACCESS_KEY"]
    config["rustfs"]["secret_key"] = os.environ["RUSTFS_SECRET_KEY"]
    return config


def build_catalog_config(config: dict) -> dict:
    return {
        "type": "rest",
        "uri": config["nessie"]["uri"],
        "prefix": config["nessie"]["prefix"],
        "s3.endpoint": config["rustfs"]["endpoint"],
        "s3.access-key-id": config["rustfs"]["access_key"],
        "s3.secret-access-key": config["rustfs"]["secret_key"],
        "s3.path-style-access": str(config["rustfs"]["path_style"]).lower(),
    }
