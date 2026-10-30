"""Pure cleaning functions shared by all job sources."""

import math
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# Rules run in order, so data roles are matched before the sales/marketing
# exclusion: "Data Analyst - Marketing" is a data analyst role.
ROLE_RULES: list[tuple[str, re.Pattern[str]]] = [
    (family, re.compile(pattern))
    for family, pattern in [
        (
            "ml_engineer",
            r"machine learning|\bml\b|mlops|deep learning|artificial intelligence"
            r"|\bai (engineer|developer|specialist|architect|scientist|lead|platform)"
            r"|gen ?ai|generative ai|computer vision|\bnlp\b|\bllm\b",
        ),
        ("data_scientist", r"data scien|applied scientist"),
        (
            "data_engineer",
            r"data engineer|\betl\b|big data|data pipeline|data platform|data architect"
            r"|data model+er|databricks?\b",
        ),
        (
            "data_analyst",
            r"data anal|analytics|business intelligence|\bbi (analyst|developer)"
            r"|power bi|tableau|product analyst",
        ),
        ("business_analyst", r"business analy|business systems? analyst"),
        ("product_manager", r"product manager|product owner"),
        ("other", r"\bsales\b|recruit|marketing|account executive|business develop"),
        (
            "devops_cloud",
            r"devops|site reliability|\bsre\b|cloud (engineer|architect)"
            r"|platform engineer",
        ),
        ("qa_test", r"\bqa\b|quality assurance|test engineer|\bsdet\b|automation test"),
        (
            "software_engineer",
            r"software|developer|programmer|full[- ]?stack|back[- ]?end"
            r"|front[- ]?end|\bsde\b|web engineer|\.net",
        ),
    ]
]

CITY_ALIASES = {
    "bengaluru": "Bangalore",
    "bangalore rural": "Bangalore",
    "gurugram": "Gurgaon",
    "new delhi": "Delhi",
    "delhi ncr": "Delhi",
    "bombay": "Mumbai",
    "madras": "Chennai",
    "calcutta": "Kolkata",
    "secunderabad": "Hyderabad",
}
NON_CITY_TOKENS = {"", "india", "ncr", "remote", "hybrid", "not available", "pan india"}
METRO_AREA = re.compile(r"^Greater | Metropolitan Area$| Metroplex$| Bay Area$| Area$")

LINKEDIN_LEVELS = {
    "Internship": "intern",
    "Entry level": "entry",
    "Associate": "mid",
    "Mid-Senior level": "senior",
    "Director": "lead",
    "Executive": "lead",
}

# Annual salaries outside these bounds are treated as data errors.
SALARY_BOUNDS = {"USD": (15_000, 1_000_000), "INR": (100_000, 30_000_000)}


@dataclass
class JobRecord:
    source: str
    source_id: str
    title: str
    country: str
    fetched_at: datetime
    raw: dict[str, Any]
    description: str | None = None
    skills_raw: str | None = None
    company_name: str | None = None
    company_size: str | None = None
    location_raw: str | None = None
    locations: list[tuple[str | None, str | None, str]] = field(default_factory=list)
    is_remote: bool = False
    employment_type: str | None = None
    experience_level: str | None = None
    experience_min_years: float | None = None
    experience_max_years: float | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_mid: float | None = None
    salary_currency: str | None = None
    url: str | None = None
    listed_at: datetime | None = None
    original_listed_at: datetime | None = None


def clean(value: Any) -> Any:
    """Turn pandas/numpy values into JSON-safe Python, with NaN as None."""
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, str):
        return value.replace("\x00", "").strip() or None
    return value


def role_family(title: str) -> str:
    lowered = title.lower()
    for family, pattern in ROLE_RULES:
        if pattern.search(lowered):
            return family
    return "other"


def experience_level_from_years(min_years: float | None) -> str | None:
    if min_years is None:
        return None
    if min_years <= 1:
        return "entry"
    if min_years <= 4:
        return "mid"
    if min_years <= 9:
        return "senior"
    return "lead"


def canonical_city(name: str) -> str:
    key = re.sub(r"\s+", " ", name).strip().lower()
    return CITY_ALIASES.get(key, key.title())


def parse_india_location(raw: str | None) -> tuple[list[str], bool]:
    """Split a multi-city Naukri location into cities and a remote flag."""
    if not raw:
        return [], False
    text = re.sub(r"\(.*?\)", " ", raw).lower()
    text = re.sub(r"\bhybrid\s*-\s*", "", text)
    is_remote = "remote" in text
    cities: list[str] = []
    for token in re.split(r"[,/]", text):
        token = re.sub(r"\s+", " ", token).strip()
        if token in NON_CITY_TOKENS:
            continue
        city = canonical_city(token)
        if city not in cities:
            cities.append(city)
    return cities, is_remote


def _metro_city(raw: str) -> str | None:
    """Reduce 'New York City Metropolitan Area' or 'Greater Houston' to the main city."""
    if not METRO_AREA.search(raw):
        return None
    name = METRO_AREA.sub("", raw).split(",")[0].split("-")[0]
    return re.sub(r" (City|DC)$", "", name).strip() or None


def parse_us_location(raw: str | None) -> tuple[str | None, str | None, str]:
    """Return (city, region, country) for a LinkedIn location string."""
    if not raw:
        return None, None, "US"
    city = _metro_city(raw)
    if city:
        return city, None, "US"
    parts = [part.strip() for part in raw.split(",")]
    if parts[-1] == "India":
        city = canonical_city(parts[0]) if len(parts) > 1 else None
        return city, None, "IN"
    if len(parts) == 2 and re.fullmatch(r"[A-Z]{2}", parts[1]):
        return parts[0], parts[1], "US"
    if len(parts) == 2 and parts[1] == "United States":
        return None, parts[0], "US"
    return None, None, "US"


def plausible_salary(
    low: float | None, high: float | None, mid: float | None, currency: str
) -> tuple[float | None, float | None, float | None]:
    """Fill in the midpoint and drop salaries outside the plausible range."""
    if mid is None and low is not None and high is not None:
        mid = (low + high) / 2
    if mid is None:
        mid = low if low is not None else high
    if mid is None:
        return None, None, None
    floor, ceiling = SALARY_BOUNDS[currency]
    if not floor <= mid <= ceiling:
        return None, None, None
    return low, high, mid


def company_key(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip().lower()


def location_key(city: str | None, region: str | None, country: str) -> str:
    return f"{country}|{region or ''}|{(city or '').lower()}"
