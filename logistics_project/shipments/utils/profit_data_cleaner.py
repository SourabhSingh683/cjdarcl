"""
Profit Data Cleaner — Ingestion pipeline for Gross Margin Fusion MIS reports.
==============================================================================
Reads the MIS Excel (header on row 2), maps columns to ProfitRecord fields,
and returns a cleaned DataFrame ready for bulk insertion.
"""

import logging
from io import BytesIO
from typing import Tuple, List, Dict, Any

import pandas as pd

logger = logging.getLogger("shipments")


# Excel column → model field mapping
COLUMN_MAP = {
    "SAPDelivery No": "sap_delivery_no",
    "SAPExternal No": "sap_external_no",
    "CNDate": "cn_date",
    "Podat": "pod_date",
    "Booking Branch": "booking_branch",
    "Loading State": "loading_state",
    "Loading City Name": "loading_city",
    "Delivery State": "delivery_state",
    "Delivery City Name": "delivery_city",
    "Customer Name": "customer_name",
    "Consignor": "consignor",
    "Consignee Name": "consignee_name",
    "Service Agent Name": "service_agent",
    "Contract Owner Name": "contract_owner",
    "Customer Load Type": "vehicle_type",
    "Darcl Material Name": "material_name",
    "Contract Types": "contract_type",
    "Gross Weight": "gross_weight",
    "Net Weight": "net_weight",
    "Charge Wt": "charge_weight",
    "Distance": "distance",
    "Value Of Goods": "value_of_goods",
    "Freight": "freight",
    "Fleet Freight": "fleet_freight",
    "Lorry Hire": "lorry_hire",
    "Lorry Hire TOPF": "lorry_hire_topf",
    "Rake Exp": "rake_exp",
    "Freight Deduction": "freight_deduction",
    "Extra Lorry Hire": "extra_lorry_hire",
    "Transhipment Cost": "transhipment_cost",
    "GM1": "gm1",
    "GM1  %": "gm1_pct",
    "Freight Incentive": "freight_incentive",
    "Operational Other Income": "operational_other_income",
    "Labour": "labour",
    "Wages": "wages",
    "Insurance": "insurance",
    "Other Direct Exp": "other_direct_exp",
    "LRP": "lrp",
    "GM2": "gm2",
    "GM2 %": "gm2_pct",
    "GM3": "gm3",
    "Claim": "claim",
    "Detention": "detention",
    "LDP": "ldp",
    "Other Operation Ded": "other_operation_ded",
    "GM4": "gm4",
    "Interest": "interest",
    "GM5": "gm5",
    "GM5 %": "gm5_pct",
    "Cash Discount": "cash_discount",
    "Transaction Charges": "transaction_charges",
    "PLI": "pli",
    "Broker Discount": "broker_discount",
    "Petro Incentive": "petro_incentive",
    "GM6": "gm6",
    "GM6 %": "gm6_pct",
    "GM7": "gm7",
    "Projected Margin": "projected_margin",
}

# "Own Fleet Frt Other Exp" appears twice — take the first one
OWN_FLEET_COL = "Own Fleet Frt Other Exp"
REIMB_COL = "Reimb Exp\n"  # Note the newline in the actual header


class ProfitDataError(Exception):
    pass


def process_profit_file(uploaded_file, file_name: str) -> Tuple[pd.DataFrame, List[Dict[str, Any]], int]:
    """
    Process a Gross Margin MIS Excel file.
    Returns: (clean_df, errors, duplicate_count)
    """
    try:
        content = uploaded_file.read()
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)

        df = pd.read_excel(BytesIO(content), header=1)
    except Exception as e:
        raise ProfitDataError(f"Cannot read file: {e}")

    logger.info(f"Profit file '{file_name}': {len(df)} rows, {len(df.columns)} columns")

    if len(df) == 0:
        raise ProfitDataError("File contains no data rows.")

    # Validate key columns exist
    required = ["SAPDelivery No", "CNDate", "Freight", "GM1"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ProfitDataError(f"Missing required columns: {missing}")

    errors = []
    clean_rows = []

    for idx, row in df.iterrows():
        try:
            record = {}

            # Map standard columns
            for excel_col, model_field in COLUMN_MAP.items():
                val = row.get(excel_col)
                if pd.isna(val):
                    val = None
                record[model_field] = val

            # Handle "Own Fleet Frt Other Exp" (first occurrence)
            own_fleet_val = row.get(OWN_FLEET_COL, 0)
            record["own_fleet_exp"] = 0 if pd.isna(own_fleet_val) else own_fleet_val

            # Handle "Reimb Exp\n" (has newline in header)
            reimb_val = row.get(REIMB_COL, 0)
            record["reimb_exp"] = 0 if pd.isna(reimb_val) else reimb_val

            # Validate required fields
            if not record.get("sap_delivery_no"):
                errors.append({"row": idx + 3, "error": "Missing SAP Delivery No"})
                continue

            if not record.get("cn_date"):
                errors.append({"row": idx + 3, "error": "Missing CNDate"})
                continue

            # Convert dates
            for date_field in ["cn_date", "pod_date"]:
                val = record.get(date_field)
                if val is not None:
                    try:
                        record[date_field] = pd.to_datetime(val).date()
                    except Exception:
                        record[date_field] = None

            # Convert SAP No to string
            record["sap_delivery_no"] = str(record["sap_delivery_no"]).strip()

            # Ensure numeric fields default to 0
            numeric_fields = [
                "gross_weight", "net_weight", "charge_weight", "distance", "value_of_goods",
                "freight", "fleet_freight", "lorry_hire", "lorry_hire_topf", "own_fleet_exp",
                "rake_exp", "freight_deduction", "extra_lorry_hire", "transhipment_cost",
                "gm1", "gm1_pct", "freight_incentive", "operational_other_income",
                "labour", "wages", "insurance", "other_direct_exp", "lrp",
                "gm2", "gm2_pct", "reimb_exp", "gm3",
                "claim", "detention", "ldp", "other_operation_ded", "gm4",
                "interest", "gm5", "gm5_pct",
                "cash_discount", "transaction_charges", "pli", "broker_discount", "petro_incentive",
                "gm6", "gm6_pct", "gm7", "projected_margin",
            ]
            for nf in numeric_fields:
                val = record.get(nf)
                if val is None or (isinstance(val, float) and pd.isna(val)):
                    record[nf] = 0
                else:
                    try:
                        record[nf] = float(val)
                    except (ValueError, TypeError):
                        record[nf] = 0

            # Weight Normalization: If charge_weight > 50, assume it's in KG and convert to Tonnes
            cw = record.get("charge_weight", 0)
            if cw > 50:
                record["charge_weight"] = cw / 1000.0
                # Optionally normalize net/gross if they are also high
                for w_field in ["net_weight", "gross_weight"]:
                    wv = record.get(w_field, 0)
                    if wv > 50:
                        record[w_field] = wv / 1000.0

            # Ensure string fields default to ""
            string_fields = [
                "booking_branch", "loading_state", "loading_city", "delivery_state", "delivery_city",
                "customer_name", "consignor", "consignee_name", "service_agent", "contract_owner",
                "vehicle_type", "material_name", "contract_type",
            ]
            for sf in string_fields:
                val = record.get(sf)
                if val is None or (isinstance(val, float) and pd.isna(val)):
                    record[sf] = ""
                else:
                    val = str(val).strip()
                    # Normalization: TATA STEEL LIMITED-JAMSHEDPUR -> TSL-jamshedpur
                    if sf == "customer_name" and val == "TATA STEEL LIMITED-JAMSHEDPUR":
                        val = "TATA STEEL LIMITED"
                    record[sf] = val

            clean_rows.append(record)

        except Exception as e:
            errors.append({"row": idx + 3, "error": str(e)})

    clean_df = pd.DataFrame(clean_rows)

    # Dedup within file
    dup_count = 0
    if len(clean_df) > 0 and "sap_delivery_no" in clean_df.columns:
        before = len(clean_df)
        clean_df = clean_df.drop_duplicates(subset=["sap_delivery_no"], keep="first")
        dup_count = before - len(clean_df)

    logger.info(f"Profit cleaner: {len(clean_df)} clean, {len(errors)} errors, {dup_count} dupes")
    return clean_df, errors[:100], dup_count
