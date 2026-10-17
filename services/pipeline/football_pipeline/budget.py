"""Daily request budget for rate-limited APIs, persisted so it survives restarts and CI runs."""

import json

from sqlalchemy import Engine, text


class BudgetExceededError(RuntimeError):
    pass


class RequestBudget:
    def __init__(self, engine: Engine, source: str, daily_limit: int) -> None:
        self._engine = engine
        self.source = source
        self.daily_limit = daily_limit

    def used_today(self) -> int:
        """Requests since 00:00 UTC (the provider's quota resets on a UTC day)."""
        with self._engine.connect() as conn:
            return conn.execute(
                text(
                    """
                    select count(*) from raw.api_request_log
                    where source = :s
                      and requested_at >= date_trunc('day', now() at time zone 'utc')
                                          at time zone 'utc'
                    """
                ),
                {"s": self.source},
            ).scalar_one()

    def remaining(self) -> int:
        return max(self.daily_limit - self.used_today(), 0)

    def check(self) -> None:
        if self.remaining() <= 0:
            raise BudgetExceededError(
                f"{self.source}: daily budget of {self.daily_limit} requests is used up"
            )

    def record(
        self, endpoint: str, params: dict, status_code: int | None, quota_remaining: int | None
    ) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    insert into raw.api_request_log
                        (source, endpoint, params, status_code, quota_remaining)
                    values (:s, :e, cast(:p as jsonb), :c, :q)
                    """
                ),
                {
                    "s": self.source,
                    "e": endpoint,
                    "p": json.dumps(params),
                    "c": status_code,
                    "q": quota_remaining,
                },
            )
