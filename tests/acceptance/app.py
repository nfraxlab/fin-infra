from __future__ import annotations

from fastapi import FastAPI


def make_app() -> FastAPI:
    app = FastAPI()

    @app.get("/ping")
    def ping() -> dict[str, str]:
        return {"pong": "ok"}

    return app
