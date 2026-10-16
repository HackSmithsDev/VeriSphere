import sys
from types import ModuleType

from fastapi import FastAPI

import main


def test_v1_endpoints_are_mounted_under_api_prefix(app: FastAPI) -> None:
    paths = set(app.openapi()["paths"])
    expected_paths = {
        "/health",
        "/api/v1/auth/login",
        "/api/v1/auth/me",
        "/api/v1/courses",
        "/api/v1/student/dashboard",
        "/api/v1/teacher/submissions",
        "/api/v1/admin/overview",
        "/api/v1/assistant/chat",
    }

    assert expected_paths.issubset(paths)


def test_main_entrypoint_uses_environment_server_settings(
    monkeypatch,
) -> None:
    called = {}
    uvicorn = ModuleType("uvicorn")
    uvicorn.run = lambda *args, **kwargs: called.update(args=args, kwargs=kwargs)
    monkeypatch.setitem(sys.modules, "uvicorn", uvicorn)
    monkeypatch.setattr(main, "HOST", "127.0.0.1")
    monkeypatch.setattr(main, "PORT", 8099)
    monkeypatch.setattr(main, "DEBUG", True)
    monkeypatch.setattr(main, "WORKERS_COUNT", 4)

    main.run_server()

    assert called == {
        "args": ("main:app",),
        "kwargs": {
            "host": "127.0.0.1",
            "port": 8099,
            "reload": True,
            "workers": 1,
            "proxy_headers": True,
            "forwarded_allow_ips": "*",
        },
    }
