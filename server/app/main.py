from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import (
    admin,
    applications,
    auth,
    health,
    job_discovery,
    onboarding,
    profile,
    resume,
    tailor,
    waitlist,
)
from app.services.daily_scheduler import start_daily_scheduler, stop_daily_scheduler

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    start_daily_scheduler()
    try:
        yield
    finally:
        await stop_daily_scheduler()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    # Flutter web picks an ephemeral localhost port; keep explicit CORS_ORIGINS too.
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(waitlist.router)
app.include_router(admin.router)
app.include_router(onboarding.router)
app.include_router(profile.router)
app.include_router(resume.router)
app.include_router(tailor.router)
app.include_router(applications.router)
app.include_router(job_discovery.router)


def main() -> None:
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
    )


if __name__ == "__main__":
    main()
