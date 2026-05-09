import logging
from urllib.parse import urlencode

import scrapy
from scrapy.crawler import CrawlerProcess

logger = logging.getLogger(__name__)

results: list[dict] = []


def resolve_path(data, path):
    """Extract a value from a dict using a dot-notation path. Returns data as-is if path is None."""
    if path is None:
        return data
    for key in str(path).split("."):
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def build_url(endpoint_cfg: dict, job_params: dict, offset: int = 0) -> str:
    fetch_cfg = endpoint_cfg.get("fetch", {})

    endpoint_params = dict(endpoint_cfg.get("params", {}))

    # inject offset param for paginated endpoints
    if fetch_cfg.get("type") == "paginated" and "offset_param" in fetch_cfg:
        endpoint_params[fetch_cfg["offset_param"]] = offset

    params = {**endpoint_params, **job_params}
    return f"{endpoint_cfg['base_url']}?{urlencode(params, doseq=True)}"


class MarketSpider(scrapy.Spider):
    name = "market"

    custom_settings = {
        "CONCURRENT_REQUESTS": 1,
        "LOG_LEVEL": "INFO",
        "USER_AGENT": "Mozilla/5.0",
    }

    def __init__(self, job: dict, endpoint_cfg: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.job = job
        self.endpoint_cfg = endpoint_cfg

    def start_requests(self):
        yield scrapy.Request(
            url=build_url(self.endpoint_cfg, self.job.get("params", {})),
            callback=self.parse,
            meta={"offset": 0},
        )

    def parse(self, response):
        data = response.json()
        logger.info("%s %s", response.status, response.url)

        rmap = self.endpoint_cfg.get("response_map", {})
        fetch_cfg = self.endpoint_cfg.get("fetch", {})

        items = resolve_path(data, rmap.get("items"))
        for item in (items or []):
            results.append(item)

        if fetch_cfg.get("type") == "paginated":
            total = resolve_path(data, rmap.get("total")) or 0
            page_size_default = fetch_cfg.get("page_size_default", 10)
            page_size = resolve_path(data, rmap.get("page_size")) or page_size_default

            # job-level max_pages overrides schema default
            max_pages = self.job.get("max_pages") or fetch_cfg.get("max_pages")

            current_offset = response.meta["offset"]
            next_offset = current_offset + page_size
            next_page_num = next_offset // page_size

            if next_offset < total and (max_pages is None or next_page_num < max_pages):
                yield scrapy.Request(
                    url=build_url(self.endpoint_cfg, self.job.get("params", {}), next_offset),
                    callback=self.parse,
                    meta={"offset": next_offset},
                )


def resolve_endpoint(job: dict, config: dict) -> dict:
    endpoint_cfg = config["endpoints"][job["endpoint"]]
    schema = config["schemas"][endpoint_cfg["schema"]]
    # schema is the base, endpoint keys override
    return {**schema, **endpoint_cfg}


def run(job: dict, config: dict, worker_id: str):
    from scrapworker.store import write_raw

    global results
    results = []

    endpoint_cfg = resolve_endpoint(job, config)

    process = CrawlerProcess()
    process.crawl(MarketSpider, job=job, endpoint_cfg=endpoint_cfg)
    process.start()

    logger.info("Crawl complete: %d results | run_id=%s | worker=%s", len(results), job["run_id"], worker_id)

    write_raw(config["rustfs"], job, results)
