"""
Glue Database Tool
Creates YAML config for Glue databases
(PR creation moved to api.py for multi-resource support)
"""

import os
from pydantic import BaseModel, Field, validator


class GlueDBPRInput(BaseModel):
    """
    Input schema for Glue Database configuration
    """
    intake_id: str = Field(
        ...,
        description="Unique identifier for this intake request"
    )
    database_name: str = Field(
        ...,
        description="Name of the Glue database"
    )
    database_s3_location: str = Field(
        ...,
        description="S3 path where database data is stored"
    )
    database_description: str = Field(
        ...,
        description="Brief description of the database purpose"
    )
    aws_account_id: str = Field(
        ...,
        description="AWS account ID (12 digits)"
    )
    source_name: str = Field(
        ...,
        description="Source system name"
    )
    enterprise_or_func_name: str = Field(
        ...,
        description="Enterprise or functional area name"
    )
    enterprise_or_func_subgrp_name: str = Field(
        ...,
        description="Sub-group within the enterprise/functional area"
    )
    region: str = Field(
        ...,
        description="AWS region (e.g., us-east-1, us-west-2)"
    )
    data_construct: str = Field(
        ...,
        description="Data construct type"
    )
    data_env: str = Field(
        ...,
        description="Environment (e.g., dev, staging, prod)"
    )
    data_layer: str = Field(
        ...,
        description="Data layer (e.g., raw, curated, analytics)"
    )
    data_leader: str = Field(
        ...,
        description="Name of the data leader/owner"
    )
    data_owner_email: str = Field(
        ...,
        description="Email address of the data owner"
    )
    data_owner_github_uname: str = Field(
        ...,
        description="GitHub username of the data owner"
    )

    @validator("database_s3_location")
    def s3_must_start(cls, v):
        if not v.startswith("s3://"):
            raise ValueError("S3 path must start with s3://")
        return v

    @validator("aws_account_id")
    def aws_account_valid(cls, v):
        if not v.isdigit() or len(v) != 12:
            raise ValueError("AWS account ID must be 12 digits")
        return v

    @validator("data_owner_email")
    def email_valid(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v


def create_glue_db_yaml(input: GlueDBPRInput) -> dict:
    """
    Create Glue Database configuration dictionary
    This will be saved ONLY in the glue_databases folder

    Args:
        input: GlueDBPRInput with validated fields

    Returns:
        Dictionary ready for YAML conversion with resource_type specified
    """
    return {
        "resource_type": "glue_database",  # Explicitly mark resource type
        "intake_id": input.intake_id,
        "database_name": input.database_name,
        "database_s3_location": input.database_s3_location,
        "database_description": input.database_description,
        "aws_account_id": input.aws_account_id,
        "source_name": input.source_name,
        "enterprise_or_func_name": input.enterprise_or_func_name,
        "enterprise_or_func_subgrp_name": input.enterprise_or_func_subgrp_name,
        "region": input.region,
        "data_construct": input.data_construct,
        "data_env": input.data_env,
        "data_layer": input.data_layer,
        "data_leader": input.data_leader,
        "data_owner_email": input.data_owner_email,
        "data_owner_github_uname": input.data_owner_github_uname,
    }


def get_glue_db_file_path(database_name: str, base_path: str = "intake_configs") -> str:
    """
    Generate the correct file path for Glue database YAML
    Ensures file goes into glue_databases folder ONLY

    Args:
        database_name: Name of the database
        base_path: Base directory for configs

    Returns:
        Full path where the YAML should be saved
    """
    glue_db_folder = os.path.join(base_path, "glue_databases")
    os.makedirs(glue_db_folder, exist_ok=True)

    filename = f"{database_name}.yaml"
    return os.path.join(glue_db_folder, filename)