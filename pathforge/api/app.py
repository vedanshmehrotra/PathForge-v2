"""FastAPI application — thin orchestration layer for PathForge engines."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathforge.api.routes.analyze import router as analyze_router
from pathforge.api.routes.prepare_problem import router as prepare_problem_router
from pathforge.api.routes.gaps import router as gaps_router
from pathforge.api.routes.elo_route import router as elo_router
from pathforge.api.routes.recommend import router as recommend_router
from pathforge.api.auth_routes import router as auth_router
from pathforge.db.db import init_db
import config


def create_api() -> FastAPI:
    app = FastAPI(
        title="PathForge API",
        description="Learning signal pipeline — AST, Matching, Gap, Elo, Recommendation",
        version="2.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    init_db(config.DATABASE_PATH)

    app.include_router(auth_router)
    app.include_router(analyze_router, tags=["Analysis"])
    app.include_router(prepare_problem_router, tags=["Problem Cache"])
    app.include_router(gaps_router, tags=["Gaps"])
    app.include_router(elo_router, tags=["Elo"])
    app.include_router(recommend_router, tags=["Recommendations"])

    @app.get("/health")
    def health():
        return {"status": "ok", "system": "PathForge API v2"}

    return app


app = create_api()

