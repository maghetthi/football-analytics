with spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('1950-01-01' as date)",
        end_date="cast('2031-01-01' as date)"
    ) }}
)

select
    to_char(date_day, 'YYYYMMDD')::int       as date_key,
    date_day::date                           as date,
    extract(year from date_day)::int         as year,
    extract(quarter from date_day)::int      as quarter,
    extract(month from date_day)::int        as month,
    to_char(date_day, 'FMMonth')             as month_name,
    extract(isodow from date_day)::int       as iso_day_of_week,
    to_char(date_day, 'FMDay')               as day_name,
    extract(week from date_day)::int         as iso_week,
    extract(isodow from date_day) in (6, 7)  as is_weekend
from spine
