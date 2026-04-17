import uvicorn

from .config.settings import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run("src.app:app", host="0.0.0.0", port=settings.PORT, reload=False)


if __name__ == "__main__":
    main()
