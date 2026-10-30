from datetime import date

from pydantic import BaseModel


class SleepRecord(BaseModel):
    id: str
    date: date
    hours: float
    quality: int  # 1-10


class HealthMetrics(BaseModel):
    id: str
    date: date
    energy: int
    focus: int


class DailyMetrics(BaseModel):
    date: date
    sleep_hours: float
    tasks_completed: int
    study_minutes: int
