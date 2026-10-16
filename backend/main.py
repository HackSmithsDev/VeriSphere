from app import create_app
from app.core.config import DEBUG, HOST, PORT, WORKERS_COUNT


app = create_app()


def run_server() -> None:
    import uvicorn

    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
        workers=1 if DEBUG else WORKERS_COUNT,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    run_server()