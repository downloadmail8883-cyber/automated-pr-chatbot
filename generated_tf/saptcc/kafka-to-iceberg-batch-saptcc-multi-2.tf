locals {
  kafka_bootstrap_endpoint = {
    dev = "8080"
    prod = "8081"
  }

  schema_registry_endpoint = {
    dev = "asdhajshd"
    prod = "iadhdfhsjhlsf"
  }

  miw_account_id = {
    dev = "123456789012"
    prod = "210987654321"
  }

  glue_jobs = {
    "kafka-to-iceberg-batch-saptcc-multi-2" = {
      job_type          = "unified"
      job_version       = "0.3.0"
      glue_version      = "5.1"

      number_of_workers = 1
      worker_type       = "G.1X"
      stop_before_start = true

      glue_job_arguments = {
        "--source"                                 = "kafka"
        "--source_kafka_endpoint"                  = local.kafka_bootstrap_endpoint[local.env]
        "--source_kafka_secret_name"               = "123456"
        "--source_kafka_topic"                     = "dev.saptcc.multi-2.raw"

        "--transformer1"                      = "timestamp"
        "--transformer1_column"               = "processing_timestamp"
        "--transformer1_value_format"         = "json"

        "--transformer2"                      = "kafka_unpack"
        "--transformer2_metadata_column"      = "__metadata__"

        "--sink_transformer1"                      = "kafka_split"
        "--sink_transformer1_schema_registry_endpoint" = local.schema_registry_endpoint[local.env]
        "--sink_transformer1_secret_name"          = "123456"

        "--sink"                                   = "iceberg"
        "--sink_iceberg_catalog_type"              = "glue"
        "--sink_iceberg_catalog_id"                = local.miw_account_id[local.env]
        "--sink_iceberg_database"                  = "lh_saptcc_raw_prd"
        "--sink_iceberg_warehouse"                 = "s3://warehouse/path/"
        "--sink_iceberg_checkpoint_dir"            = "s3://checkpoints/path/"
        "--sink_iceberg_assume_role_arn"           = "arn:aws:iam::123456789012:role/mif-glue-iceberg-writer"
        "--sink_iceberg_assume_session_name"       = "mif-glue-iceberg"

        "--sink_trigger"                           = "availableNow"
      }
    }
  }
}