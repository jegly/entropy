import sys

from .app import EntropyApp


def main() -> int:
    app = EntropyApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
