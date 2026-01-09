"""
Handles intake question flow and validation.
"""
MANDATORY_FIELDS = [
    'intake_id', 'database_name', 'database_s3_location', 'database_description',
    'aws_account_id', 'region', 'data_construct', 'data_env', 'data_layer',
    'source_name', 'enterprise_or_func_name', 'enterprise_or_func_subgrp_name',
    'data_owner_email', 'data_owner_github_uname', 'data_leader'
]

def collect_intake():
    """Collect required intake fields from the user via CLI."""
    collected_data = {}
    for field in MANDATORY_FIELDS:
        while True:
            value = input(f"**Required Field:** `{field}`\n> ").strip()
            if value:
                collected_data[field] = value
                break
            else:
                print(f"{field} is mandatory. Please enter a value.")
    return collected_data
