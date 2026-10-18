"""Versioned descriptive proposals, deliberately separate from matchable groups.

These records express model-proposed approaches the skill catalogue cannot
represent. They are neither validated solutions nor evidence for skill updates.
"""
import re

CONTRACT_VERSION = 2
RECORD_TYPE = "unscored_approach"


def normalize_description(approach):
    if approach.get("comparison_support") != "UNSUPPORTED" or approach.get("patterns") != []:
        raise ValueError("An unsupported approach must declare empty pattern requirements")
    fields = {}
    for key in ("name", "description", "coverage_limit"):
        value = approach.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"An unsupported approach needs nonempty {key}")
        fields[key] = value.strip()
    return {**fields, "patterns": [], "comparison_support": "UNSUPPORTED"}


def description_record(approach, index, source_sha256):
    record = {**normalize_description(approach), "id": f"description_{index}",
              "record_type": RECORD_TYPE, "contract_version": CONTRACT_VERSION,
              "source_sha256": source_sha256, "authority_tier": "llm_proposed",
              "provenance": ["llm_proposed", "approach_contract_v2"]}
    validate_description_record(record)
    return record


def validate_description_record(record):
    """Reject corrupt/authority-bearing records before ordinary group loading."""
    normalize_description(record)
    if (record.get("record_type") != RECORD_TYPE
            or type(record.get("contract_version")) is not int or record["contract_version"] != CONTRACT_VERSION
            or record.get("authority_tier") != "llm_proposed"
            or record.get("provenance") != ["llm_proposed", "approach_contract_v2"]
            or not isinstance(record.get("id"), str) or not record["id"].strip()
            or not isinstance(record.get("source_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", record["source_sha256"])
            or set(record) != {"name", "description", "coverage_limit", "patterns", "comparison_support",
                               "id", "record_type", "contract_version", "source_sha256", "authority_tier", "provenance"}):
        raise ValueError("Unusable descriptive approach record")


def public_description(record):
    validate_description_record(record)
    return {key: record[key] for key in (
        "id", "name", "description", "coverage_limit", "patterns", "comparison_support",
        "contract_version", "source_sha256", "provenance", "authority_tier",
    )}
