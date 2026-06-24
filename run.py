import uvicorn
import argparse
import os


def main():
    parser = argparse.ArgumentParser(
        prog="pi-tv", description="Self-hosted IPTV relay and web player"
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to listen on (default: 8000)"
    )

    parser.add_argument("--dev", action="store_true", help="Development mode")
    args = parser.parse_args()

    if args.dev:
        os.environ["PI_TV_DEV"] = "true"

    print(f"Starting PI-TV on http://{args.host}:{args.port}")

    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        reload=args.dev,
    )


if __name__ == "__main__":
    main()
