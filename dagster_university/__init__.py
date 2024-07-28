# fmt: off
from dagster import Definitions, load_assets_from_modules

from .assets import metrics, trips
from .resources import database_resource
from .jobs import weekly_update_job, trip_update_job
from .schedules import weekly_update_schedule, trip_update_schedule

trip_assets = load_assets_from_modules([trips])
metric_assets = load_assets_from_modules([metrics])
all_jobs = [weekly_update_job, trip_update_job]
all_schedules = [weekly_update_schedule, trip_update_schedule]

defs = Definitions(
    assets=[*trip_assets, *metric_assets],
    resources={
        "database": database_resource
    },
    jobs=all_jobs,
    schedules=all_schedules
)
