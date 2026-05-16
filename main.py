from fastapi import FastAPI
import requests
from urllib.parse import quote_plus

app = FastAPI(
    title="Market Access API",
    version="1.0.0",
    description="API pour rechercher des informations utiles aux analyses d'accès au marché des dispositifs médicaux en France.",
    servers=[
        {
            "url": "https://market-access-api.onrender.com"
        }
    ]
)

SOURCES = {
    "has": "has-sante.fr",
    "legifrance": "legifrance.gouv.fr",
    "aideaucodage": "aideaucodage.fr",
    "lpp_ameli": "codage.ext.cnamts.fr/codif/tips",
    "atih_tarifs": "atih.sante.fr/tarifs-mco-et-had"
}


@app.get("/")
def home():
    return {
        "message": "Market Access API is running",
        "available_endpoints": [
            "/search_pubmed",
            "/search_clinicaltrials",
            "/search_has",
            "/search_legifrance",
            "/search_aideaucodage",
            "/search_lpp_ameli",
            "/search_atih_tarifs",
            "/search_all"
        ]
    }


def build_site_search(source_name: str, query: str):
    domain = SOURCES[source_name]
    search_query = f"site:{domain} {query}"
    duckduckgo_url = "https://duckduckgo.com/html/?q=" + quote_plus(search_query)

    return {
        "source": source_name,
        "query": query,
        "site_restricted_query": search_query,
        "search_url": duckduckgo_url,
        "note": "Open this URL to review site-specific results. This endpoint creates a targeted search URL."
    }


@app.get("/search_has")
def search_has(query: str):
    return build_site_search("has", query)


@app.get("/search_legifrance")
def search_legifrance(query: str):
    return build_site_search("legifrance", query)


@app.get("/search_aideaucodage")
def search_aideaucodage(query: str):
    return build_site_search("aideaucodage", query)


@app.get("/search_lpp_ameli")
def search_lpp_ameli(query: str):
    return build_site_search("lpp_ameli", query)


@app.get("/search_atih_tarifs")
def search_atih_tarifs(query: str):
    return build_site_search("atih_tarifs", query)


@app.get("/search_pubmed")
def search_pubmed(query: str, max_results: int = 10):
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

    search_params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": max_results
    }

    search_response = requests.get(search_url, params=search_params, timeout=20)
    search_response.raise_for_status()
    search_data = search_response.json()

    ids = search_data.get("esearchresult", {}).get("idlist", [])

    if not ids:
        return {
            "source": "pubmed",
            "query": query,
            "results": []
        }

    summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

    summary_params = {
        "db": "pubmed",
        "id": ",".join(ids),
        "retmode": "json"
    }

    summary_response = requests.get(summary_url, params=summary_params, timeout=20)
    summary_response.raise_for_status()
    summary_data = summary_response.json()

    results = []

    for pmid in ids:
        item = summary_data.get("result", {}).get(pmid, {})
        results.append({
            "pmid": pmid,
            "title": item.get("title"),
            "journal": item.get("fulljournalname"),
            "publication_date": item.get("pubdate"),
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        })

    return {
        "source": "pubmed",
        "query": query,
        "results": results
    }


@app.get("/search_clinicaltrials")
def search_clinicaltrials(query: str, max_results: int = 10):
    url = "https://clinicaltrials.gov/api/v2/studies"

    params = {
        "query.term": query,
        "pageSize": max_results
    }

    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    data = response.json()

    results = []

    for study in data.get("studies", []):
        protocol = study.get("protocolSection", {})
        identification = protocol.get("identificationModule", {})
        status = protocol.get("statusModule", {})
        conditions = protocol.get("conditionsModule", {})

        nct_id = identification.get("nctId")

        results.append({
            "nct_id": nct_id,
            "title": identification.get("briefTitle"),
            "status": status.get("overallStatus"),
            "conditions": conditions.get("conditions"),
            "url": f"https://clinicaltrials.gov/study/{nct_id}" if nct_id else None
        })

    return {
        "source": "clinicaltrials.gov",
        "query": query,
        "results": results
    }


@app.get("/search_all")
def search_all(query: str):
    return {
        "query": query,
        "has": build_site_search("has", query),
        "legifrance": build_site_search("legifrance", query),
        "aideaucodage": build_site_search("aideaucodage", query),
        "lpp_ameli": build_site_search("lpp_ameli", query),
        "atih_tarifs": build_site_search("atih_tarifs", query),
        "pubmed_endpoint": f"/search_pubmed?query={quote_plus(query)}",
        "clinicaltrials_endpoint": f"/search_clinicaltrials?query={quote_plus(query)}"
    }
