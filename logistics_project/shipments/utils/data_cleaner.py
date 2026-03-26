"""
Data Cleaning & Processing Pipeline (v2 — Decision Intelligence)
=================================================================
Auto-maps columns from real-world logistics Excel files,
extracts financial/weight/transit fields, computes derived fields,
and handles cross-file deduplication.
"""

import logging
import json
from io import BytesIO
from datetime import timedelta
from typing import Tuple, List, Dict, Any

import pandas as pd

logger = logging.getLogger("shipments")

# ─── Column Mapping ──────────────────────────────────────────────────────────
COLUMN_ALIASES = {
    "shipment_id": [
        "shipment_id", "shipment id", "c/n no.", "c/n no", "cn no",
        "consignment no", "consignment_no", "lr no", "lr_no",
        "bill no.", "bill no", "bill_no", "docket no", "docket_no",
    ],
    "origin": [
        "origin", "from", "source", "pickup", "pickup_location",
        "stockyard", "stockyard\n/direct", "stockyard /direct",
    ],
    "destination": [
        "destination", "to", "dest", "delivery_location",
        "consignee_city", "unloading_point",
    ],
    "dispatch_date": [
        "dispatch_date", "dispatch date", "c/n\ndate", "c/n date",
        "cn date", "cn_date", "date", "lr_date", "lr date",
    ],
    "delivery_date": [
        "delivery_date", "delivery date", "delivered_date",
        "actual_delivery", "pod_date", "pod date",
    ],
    "expected_delivery_date": [
        "expected_delivery_date", "expected delivery date", "edd",
        "reporting date", "reporting_date",
    ],
    "vehicle_type": [
        "vehicle_type", "vehicle type", "material \ntpye",
        "material \ntype", "material tpye", "material type", "material_type",
    ],
}

EXTRA_ALIASES = {
    "vehicle_no": [
        "vehicle no", "vehicle_no", "vehicle no.", "truck_no", "truck no",
    ],
    "transit_permissible": [
        "transit time \npermissible (days) :", "transit time permissible (days)",
        "transit_time_permissible", "tat_days", "sla_days",
        "transit time permissible", "transit time\npermissible (days) :",
    ],
    "transit_taken": [
        "transit time \ntaken (days) :", "transit time taken (days)",
        "transit_time_taken", "transit time taken",
        "transit time\ntaken (days) :",
    ],
    "net_weight": [
        "net wt.\n(in mt)", "net wt. (in mt)", "net_wt", "net weight",
        "net wt", "net wt.\n(in mt)",
    ],
    "gross_weight": [
        "gross wt.\n(in mt)", "gross wt. (in mt)", "gross_wt", "gross weight",
    ],
    "charge_weight": [
        "charge wt.\n(in mt)", "charge wt. (in mt)", "charge_wt", "charge weight",
    ],
    "shortage": [
        "shortage (mt)", "shortage", "short",
    ],
    "rate_per_mt": [
        "rate\n(pmt)", "rate (pmt)", "rate", "rate_per_mt",
    ],
    "total_amount": [
        "total\namount", "total amount", "total_amount", "gross amount",
    ],
    "freight_deduction": [
        "less : freight deduction", "less: freight deduction",
        "freight deduction", "freight_deduction",
    ],
    "penalty": [
        "less : late delivery penalty", "less: late delivery penalty",
        "late delivery penalty", "penalty", "penalties",
    ],
    "amount_receivable": [
        "amount receivable", "amount_receivable", "net amount",
    ],
    "grn_date": [
        "grn date", "grn_date",
    ],
    "invoice_no": [
        "invoice no.", "invoice no", "invoice_no",
    ],
    "delivery_no": [
        "delivery no.", "delivery no", "delivery_no",
    ],
}

MINIMUM_REQUIRED = {"shipment_id", "dispatch_date"}
DATE_COLUMNS = ["dispatch_date", "delivery_date", "expected_delivery_date"]


class DataCleaningError(Exception):
    pass


def read_file(file_obj, file_name: str) -> pd.DataFrame:
    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    content = file_obj.read()
    try:
        if ext == "csv":
            df = pd.read_csv(BytesIO(content))
        elif ext in ("xlsx", "xls"):
            df = pd.read_excel(BytesIO(content), engine="openpyxl")
        else:
            raise DataCleaningError(f"Unsupported file format '.{ext}'.")
    except DataCleaningError:
        raise
    except Exception as e:
        raise DataCleaningError(f"Failed to read file: {str(e)}")
    if df.empty:
        raise DataCleaningError("The uploaded file contains no data rows.")
    return df


def _find_column(df_columns, aliases):
    col_lower_map = {col.strip().lower().replace("\r", ""): col for col in df_columns}
    for alias in aliases:
        normalized = alias.strip().lower().replace("\r", "")
        if normalized in col_lower_map:
            return col_lower_map[normalized]
    return None


def auto_map_columns(df):
    df_cols = list(df.columns)
    mapped, extra_mapped = {}, {}
    for name, aliases in COLUMN_ALIASES.items():
        found = _find_column(df_cols, aliases)
        if found:
            mapped[name] = found
    for name, aliases in EXTRA_ALIASES.items():
        found = _find_column(df_cols, aliases)
        if found:
            extra_mapped[name] = found
    return mapped, extra_mapped


def validate_minimum_columns(mapped, df_columns):
    missing = MINIMUM_REQUIRED - set(mapped.keys())
    if missing:
        available = ", ".join(sorted(str(c) for c in df_columns[:15]))
        raise DataCleaningError(
            f"Missing required columns: {', '.join(sorted(missing))}. "
            f"Available: [{available}]"
        )


def clean_data(df, mapped, extra_mapped):
    errors = []
    total_before = len(df)
    dup_count = 0

    # Rename mapped columns
    rename_map = {orig: internal for internal, orig in mapped.items()}
    df = df.rename(columns=rename_map)
    extra_rename = {orig: internal for internal, orig in extra_mapped.items()}
    df = df.rename(columns=extra_rename)

    # Ensure all expected columns exist
    all_fields = [
        "shipment_id", "origin", "destination", "dispatch_date",
        "delivery_date", "expected_delivery_date", "revenue", "vehicle_type",
        "vehicle_no", "transit_permissible", "transit_taken",
        "net_weight", "gross_weight", "charge_weight", "shortage",
        "rate_per_mt", "total_amount", "freight_deduction", "penalty",
        "amount_receivable",
    ]
    for col in all_fields:
        if col not in df.columns:
            df[col] = None

    # --- Shipment ID ---
    df["shipment_id"] = df["shipment_id"].astype(str).str.strip()
    df = df[~df["shipment_id"].isin(["", "nan", "None", "none", "NaN"])].copy()
    if df.empty:
        raise DataCleaningError("No valid shipment IDs found.")

    # --- Dedup ---
    dup_mask = df.duplicated(subset=["shipment_id"], keep="first")
    dup_count = int(dup_mask.sum())
    if dup_count > 0:
        for sid in df.loc[dup_mask, "shipment_id"].tolist()[:10]:
            errors.append({"row": "dup", "field": "shipment_id", "error": f"Duplicate '{sid}' removed"})
        df = df[~dup_mask].copy()

    # --- Date coercion ---
    for col in DATE_COLUMNS:
        if df[col].notna().any():
            original = df[col].copy()
            df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
            failed = df[col].isna() & original.notna() & (original.astype(str) != "nan")
            for idx in df.index[failed]:
                errors.append({"row": int(idx), "field": col, "error": f"Invalid date: '{original.loc[idx]}'"})

    # If expected_delivery_date missing, compute from transit_permissible
    if df["expected_delivery_date"].isna().all() and df.get("transit_permissible") is not None:
        transit = pd.to_numeric(df["transit_permissible"], errors="coerce")
        valid = df["dispatch_date"].notna() & transit.notna() & (transit > 0)
        if valid.any():
            df.loc[valid, "expected_delivery_date"] = (
                df.loc[valid, "dispatch_date"] + pd.to_timedelta(transit[valid], unit="D")
            )

    # If delivery_date missing, try grn_date
    if df["delivery_date"].isna().all() and "grn_date" in df.columns:
        df["delivery_date"] = pd.to_datetime(df["grn_date"], errors="coerce", dayfirst=True)

    # --- Numeric coercion for all numeric fields ---
    numeric_fields = [
        "revenue", "net_weight", "gross_weight", "charge_weight", "shortage",
        "rate_per_mt", "total_amount", "freight_deduction", "penalty",
        "amount_receivable", "transit_permissible", "transit_taken",
    ]
    for col in numeric_fields:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # --- Revenue: prefer total_amount, fallback to weight × rate ---
    if (df["revenue"] == 0).all():
        if (df["total_amount"] > 0).any():
            df["revenue"] = df["total_amount"]
        elif (df["net_weight"] > 0).any() and (df["rate_per_mt"] > 0).any():
            df["revenue"] = df["net_weight"] * df["rate_per_mt"]

    # --- Text standardization ---
    for col in ["origin", "destination"]:
        df[col] = df[col].astype(str).str.strip().str.title()
        df.loc[df[col].isin(["Nan", "None", ""]), col] = "Unknown"

    df["vehicle_type"] = df["vehicle_type"].astype(str).str.strip().str.lower()
    df.loc[df["vehicle_type"].isin(["", "nan", "none"]), "vehicle_type"] = "other"

    df["vehicle_no"] = df["vehicle_no"].astype(str).str.strip().str.upper()
    df.loc[df["vehicle_no"].isin(["", "NAN", "NONE"]), "vehicle_no"] = ""

    if (df["origin"] == "Unknown").all():
        df["origin"] = "Base"

    # --- Drop rows without dispatch_date ---
    no_dispatch = df["dispatch_date"].isna()
    for idx in df.index[no_dispatch]:
        errors.append({"row": int(idx), "field": "dispatch_date", "error": "Missing — row dropped"})
    df = df[~no_dispatch].copy()

    # --- Compute delay_days and is_on_time ---
    df["delay_days"] = 0
    df["is_on_time"] = True

    # Method 1: from transit times
    has_transit = (df["transit_taken"] > 0) & (df["transit_permissible"] > 0)
    if has_transit.any():
        df.loc[has_transit, "delay_days"] = (
            df.loc[has_transit, "transit_taken"] - df.loc[has_transit, "transit_permissible"]
        ).astype(int)
        df.loc[has_transit, "is_on_time"] = df.loc[has_transit, "delay_days"] <= 0

    # Method 2: from dates (fallback)
    has_dates = ~has_transit & df["delivery_date"].notna() & df["expected_delivery_date"].notna()
    if has_dates.any():
        df.loc[has_dates, "delay_days"] = (
            (df.loc[has_dates, "delivery_date"] - df.loc[has_dates, "expected_delivery_date"]).dt.days.astype(int)
        )
        df.loc[has_dates, "is_on_time"] = df.loc[has_dates, "delay_days"] <= 0

    # --- Derived flags ---
    df["has_shortage"] = df["shortage"] > 0
    df["has_penalty"] = df["penalty"] > 0

    total_after = len(df)
    logger.info(f"Cleaning: {total_before} → {total_after} rows, {dup_count} dups, {len(errors)} errors")

    return df, errors, dup_count


def process_file(file_obj, file_name: str):
    """
    Top-level: read → map → validate → clean.
    Returns (clean_df, error_log, duplicate_count).
    """
    logger.info(f"Processing file: {file_name}")
    df = read_file(file_obj, file_name)
    mapped, extra_mapped = auto_map_columns(df)
    logger.info(f"Mapped: {list(mapped.keys())}, Extra: {list(extra_mapped.keys())}")
    validate_minimum_columns(mapped, list(df.columns))
    clean_df, errors, dup_count = clean_data(df, mapped, extra_mapped)
    if clean_df.empty:
        raise DataCleaningError("No valid rows remaining after cleaning.")
    return clean_df, errors, dup_count
