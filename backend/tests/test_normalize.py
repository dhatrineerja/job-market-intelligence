import math

import pytest

from app.etl.naukri import listed_at_from_id as _listed_at
from app.etl.normalize import (
    clean,
    experience_level_from_years,
    parse_india_location,
    parse_naukri_salary,
    parse_us_location,
    parse_years_range,
    plausible_salary,
    role_family,
)


@pytest.mark.parametrize(
    ("title", "family"),
    [
        ("Machine Learning Engineer", "ml_engineer"),
        ("Senior MLOps Engineer", "ml_engineer"),
        ("Data Scientist II", "data_scientist"),
        ("Data Analyst - Marketing", "data_analyst"),
        ("Power BI Developer", "data_analyst"),
        ("Data Engineer", "data_engineer"),
        ("Insurance - Business Analyst", "business_analyst"),
        ("Software Sales Manager", "other"),
        ("Business Development Executive", "other"),
        ("DevOps Engineer", "devops_cloud"),
        ("QA Analyst", "qa_test"),
        (".NET Software Developer (Angular)", "software_engineer"),
        ("Registered Nurse", "other"),
        ("Artificial Intelligence Engineer", "ml_engineer"),
        ("Azure Data Architect", "data_engineer"),
        ("Senior Data Modeller", "data_engineer"),
        ("Salesforce Developer", "software_engineer"),
        ("Business System Analyst", "business_analyst"),
    ],
)
def test_role_family(title, family):
    assert role_family(title) == family


def test_parse_india_location_splits_and_normalizes_cities():
    cities, is_remote = parse_india_location("Hyderabad, Chennai, Bengaluru")
    assert cities == ["Hyderabad", "Chennai", "Bangalore"]
    assert is_remote is False


def test_parse_india_location_handles_aliases_and_duplicates():
    cities, _ = parse_india_location("Hybrid - Gurugram, Delhi / NCR, New Delhi")
    assert cities == ["Gurgaon", "Delhi"]


def test_parse_india_location_drops_states_and_merges_spellings():
    assert parse_india_location("Pune, Maharashtra, Bangalore/ Bengaluru, Karnataka") == (
        ["Pune", "Bangalore"],
        False,
    )
    assert parse_india_location("Cochin, Kochi, Trivandrum, Mysore")[0] == [
        "Kochi",
        "Thiruvananthapuram",
        "Mysuru",
    ]
    assert parse_india_location("Maharashtra") == ([], False)


def test_parse_india_location_ignores_temporary_wfh_notice():
    assert parse_india_location("Temp. WFH - Hyderabad") == (["Hyderabad"], False)
    assert parse_india_location("Temp. WFH due to covid, Pune")[0] == ["Pune"]


def test_parse_india_location_flags_remote():
    assert parse_india_location("Remote") == ([], True)


def test_parse_us_location():
    assert parse_us_location("New York, NY") == ("New York", "NY", "US")
    assert parse_us_location("Texas, United States") == (None, "Texas", "US")
    assert parse_us_location("United States") == (None, None, "US")
    assert parse_us_location("Bengaluru, Karnataka, India") == ("Bangalore", None, "IN")


@pytest.mark.parametrize(
    ("raw", "city"),
    [
        ("New York City Metropolitan Area", "New York"),
        ("San Francisco Bay Area", "San Francisco"),
        ("Greater Houston", "Houston"),
        ("Dallas-Fort Worth Metroplex", "Dallas"),
        ("Washington DC-Baltimore Area", "Washington"),
        ("Austin, Texas Metropolitan Area", "Austin"),
    ],
)
def test_parse_us_location_reduces_metro_areas_to_a_city(raw, city):
    assert parse_us_location(raw) == (city, None, "US")


def test_plausible_salary_fills_midpoint():
    assert plausible_salary(50_000, 70_000, None, "USD") == (50_000, 70_000, 60_000)


def test_plausible_salary_rejects_outliers():
    assert plausible_salary(1, 2, None, "USD") == (None, None, None)
    assert plausible_salary(None, None, 535_600_000, "USD") == (None, None, None)


def test_plausible_salary_uses_currency_bounds():
    assert plausible_salary(1_500_000, 3_000_000, None, "INR")[2] == 2_250_000


def test_experience_level_from_years():
    assert experience_level_from_years(None) is None
    assert experience_level_from_years(0) == "entry"
    assert experience_level_from_years(3) == "mid"
    assert experience_level_from_years(5) == "senior"
    assert experience_level_from_years(10) == "lead"


def test_clean_handles_nan_and_null_bytes():
    assert clean(math.nan) is None
    assert clean("  a\x00b ") == "ab"
    assert clean("   ") is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("10-20 Lacs PA", (1_000_000, 2_000_000)),
        ("3.5-4.5 Lacs PA", (350_000, 450_000)),
        ("12 Lacs PA", (1_200_000, 1_200_000)),
        ("15-30 Lacs PA (Including Variable: 10%)", (1_500_000, 3_000_000)),
        ("50,000-2.5 Lacs PA", (50_000, 250_000)),
        ("50,000-60,000 PA", (50_000, 60_000)),
        ("1-1.75 Cr PA", (10_000_000, 17_500_000)),
        ("40 Lacs-1 Cr PA", (4_000_000, 10_000_000)),
        ("15,000/month", (180_000, 180_000)),
        ("Not disclosed", None),
        ("Unpaid", None),
        ("Less than 5,000 PA", None),
        ("9.5 Cr and above PA", None),
        ("20-10 Lacs PA", None),
        (None, None),
    ],
)
def test_parse_naukri_salary(raw, expected):
    assert parse_naukri_salary(raw) == expected


def test_parse_years_range():
    assert parse_years_range("3-7 Yrs") == (3.0, 7.0)
    assert parse_years_range("5 Aug - 7 Aug") is None
    assert parse_years_range(None) is None


def test_naukri_listed_at_parses_id_prefix():
    assert _listed_at("140526021840").strftime("%Y-%m-%d") == "2026-05-14"
    assert _listed_at("row-5") is None
