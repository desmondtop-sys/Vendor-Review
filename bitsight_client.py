import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

load_dotenv(ROOT_DIR / ".env")

BITSIGHT_BASE_URL = "https://api.bitsighttech.com/ratings/v1"


def _build_auth(api_key: str) -> tuple[dict[str, str], tuple[str, str] | None]:
    """Build Bitsight request headers/auth based on configured auth mode.

    Supported modes via BITSIGHT_AUTH_TYPE:
    - bearer: Authorization: Bearer <key>
    - token:  Authorization: Token <key>
    - basic (default): HTTP Basic auth with key as username
    """
    auth_type = os.getenv("BITSIGHT_AUTH_TYPE", "basic").lower()
    headers = {"Accept": "application/json"}

    if auth_type == "bearer":
        headers["Authorization"] = f"Bearer {api_key}"
        return headers, None
    if auth_type == "token":
        headers["Authorization"] = f"Token {api_key}"
        return headers, None

    return headers, (api_key, "")


def get_company_rating_by_name(company_name: str) -> dict[str, Any] | None:
    api_key = os.getenv("BITSIGHT_API_KEY")
    if not api_key or not company_name:
        return None

    headers, auth = _build_auth(api_key)

    try:
        response = requests.get(
            f"{BITSIGHT_BASE_URL}/companies",
            headers=headers,
            params={"name": company_name},
            auth=auth,
            timeout=15,
        )
    except requests.RequestException:
        return None

    if response.status_code != 200:
        return None

    data = response.json()
    
    # API returns different structures depending on endpoint
    if isinstance(data, dict) and "companies" in data:
        results = data.get("companies", [])
    elif isinstance(data, dict) and "results" in data:
        results = data.get("results", [])
    elif isinstance(data, dict) and "name" in data:
        # Single company object returned directly
        results = [data]
    elif isinstance(data, list):
        results = data
    else:
        return None
    
    if not results:
        return None

    # Normalize names so formatting differences (spaces/punctuation/case)
    # do not prevent a valid company match.
    search_normalized = company_name.strip().lower().replace(" ", "").replace(".", "").replace("-", "")
    
    # First pass: require exact equality after normalization.
    # This avoids accidentally picking the wrong company in broad results.
    for company in results:
        returned_name = company.get("name", "")
        returned_normalized = returned_name.strip().lower().replace(" ", "").replace(".", "").replace("-", "")
        if returned_normalized == search_normalized:
            return {
                "company_guid": company.get("guid") or company.get("company_guid"),
                "company_name": returned_name,
                "rating": company.get("rating"),
                "rating_date": company.get("rating_date") or company.get("rating_date_utc"),
            }
    
    # Fallback pass: allow partial containment match for reasonably long names.
    # The 5-character minimum prevents overly permissive short-string matches.
    if len(search_normalized) >= 5:
        for company in results:
            returned_name = company.get("name", "")
            returned_normalized = returned_name.strip().lower().replace(" ", "").replace(".", "").replace("-", "")
            if search_normalized in returned_normalized or returned_normalized in search_normalized:
                return {
                    "company_guid": company.get("guid") or company.get("company_guid"),
                    "company_name": returned_name,
                    "rating": company.get("rating"),
                    "rating_date": company.get("rating_date") or company.get("rating_date_utc"),
                }
    
    # No acceptable match found
    return None


def search_companies_by_domain(domain: str) -> list[dict[str, Any]]:
    """Search for companies across Bitsight's entire database by domain.
    
    Args:
        domain: The domain to search for (e.g., "google.com", "microsoft.com")
    
    Returns:
        List of matching companies with their GUIDs and details
    """
    api_key = os.getenv("BITSIGHT_API_KEY")
    if not api_key or not domain:
        return []

    headers, auth = _build_auth(api_key)

    try:
        response = requests.get(
            f"{BITSIGHT_BASE_URL}/companies/search",
            headers=headers,
            params={"domain": domain},
            auth=auth,
            timeout=10,
        )
    except requests.RequestException:
        return []

    if response.status_code != 200:
        return []

    data = response.json()
    results = data.get("results", [])
    
    # Format results
    formatted = []
    for company in results:
        formatted.append({
            "guid": company.get("guid"),
            "name": company.get("name"),
            "industry": company.get("industry"),
            "primary_domain": company.get("primary_domain"),
            "description": company.get("description"),
            "website": company.get("website"),
        })
    
    return formatted