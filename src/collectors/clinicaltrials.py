from datetime import date, datetime, timedelta

import requests

STUDIES_URL = "https://clinicaltrials.gov/api/v2/studies"
FIELDS = "NCTId,BriefTitle,LastUpdatePostDate,BriefSummary"
PAGE_SIZE = 50


def _cutoff_date(lookback_days):
    return date.today() - timedelta(days=lookback_days)


def _extract_study(study):
    protocol = study.get("protocolSection", {})
    identification = protocol.get("identificationModule", {})
    status = protocol.get("statusModule", {})
    description = protocol.get("descriptionModule", {})

    nct_id = identification.get("nctId")
    last_update = status.get("lastUpdatePostDateStruct", {}).get("date")
    return {
        "id": nct_id,
        "title": identification.get("briefTitle", ""),
        "url": f"https://clinicaltrials.gov/study/{nct_id}",
        "date": last_update,
        "source": "clinicaltrials",
        "snippet": (description.get("briefSummary") or "")[:600],
    }


def collect(config):
    search_terms = config["search_terms"]
    lookback_days = config["lookback_days"]
    cutoff = _cutoff_date(lookback_days)

    results = []
    page_token = None
    while True:
        params = {
            "query.cond": " OR ".join(search_terms),
            "fields": FIELDS,
            "sort": "LastUpdatePostDate:desc",
            "pageSize": PAGE_SIZE,
        }
        if page_token:
            params["pageToken"] = page_token

        resp = requests.get(STUDIES_URL, params=params, timeout=30)
        resp.raise_for_status()
        payload = resp.json()

        stop = False
        for study in payload.get("studies", []):
            item = _extract_study(study)
            if not item["date"]:
                continue
            fmt = "%Y-%m-%d" if len(item["date"]) == 10 else "%Y-%m"
            item_date = datetime.strptime(item["date"], fmt).date()
            if item_date < cutoff:
                stop = True
                break
            results.append(item)

        page_token = payload.get("nextPageToken")
        if stop or not page_token:
            break

    return results
