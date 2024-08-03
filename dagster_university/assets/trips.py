import requests
from . import constants
from dagster import asset, AssetExecutionContext
from dagster_duckdb import DuckDBResource
import duckdb
import os

from ..partitions import monthly_partition


@asset(
    partitions_def=monthly_partition
)
def taxi_trips_file(context: AssetExecutionContext) -> None:
    """
      The raw parquet files for the taxi trips dataset. Sourced from the NYC Open Data portal.
    """
    partition_date_str = context.partition_key
    month_to_fetch = partition_date_str[:-3]
    raw_trips = requests.get(
        f"https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_{month_to_fetch}.parquet"
    )

    with open(constants.TAXI_TRIPS_TEMPLATE_FILE_PATH.format(month_to_fetch), "wb") as output_file:
        output_file.write(raw_trips.content)


@asset
def taxi_zones_file() -> None:
    """
      The raw parquet files for the taxi trips dataset. Sourced from the NYC Open Data portal.
    """
    month_to_fetch = '2023-03'
    raw_zones = requests.get(
        f"https://data.cityofnewyork.us/api/views/755u-8jsi/rows.csv?accessType=DOWNLOAD"
    )

    with open(constants.TAXI_ZONES_FILE_PATH, "wb") as output_file:
        output_file.write(raw_zones.content)


@asset(
    deps=["taxi_trips_file"],
    partitions_def=monthly_partition
)
def taxi_trips(database: DuckDBResource, context: AssetExecutionContext) -> None:
    """
      The raw taxi trips dataset, loaded into a DuckDB database
    """
    partition_key = context.partition_key
    month_to_fetch = partition_key[:-3]
    sql_query = f"""
    /* create initial table with partition_date */
      create table if not exists trips (
        vendor_id integer, pickup_zone_id integer, dropoff_zone_id integer,
        rate_code_id double, payment_type integer, dropoff_datetime timestamp,
        pickup_datetime timestamp, trip_distance double, passenger_count double,
        total_amount double, partition_date varchar
      );
    /* delete any records already inserted as the table will already be created before the first partition materializes */
      delete from trips where partition_date = '{month_to_fetch}';
    /* Insert into table data from raw file + the partition date for tracking records */
      insert into trips
          select
            VendorID, PULocationID, DOLocationID, RatecodeID, payment_type, tpep_dropoff_datetime,
            tpep_pickup_datetime, trip_distance, passenger_count, total_amount, '{month_to_fetch}' as partition_date
          from '{constants.TAXI_TRIPS_TEMPLATE_FILE_PATH.format(month_to_fetch)}';
    """

    with database.get_connection() as conn:
        conn.execute(sql_query)


@asset(
    deps=["taxi_zones_file"]
)
def taxi_zones(database: DuckDBResource) -> None:
    """
      The raw taxi zones dataset, loaded into a DuckDB database
    """
    sql_query = f"""
        create or replace table zones as (
          select
            LocationID as zone_id,
            zone as zone,
            borough as borough,
            the_geom as geometry
          from '{constants.TAXI_ZONES_FILE_PATH}'
        );
    """

    with database.get_connection() as conn:
        conn.execute(sql_query)