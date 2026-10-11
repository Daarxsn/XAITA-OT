import os
from scripts.prepare_runtime_data import main as prepare_runtime_data
import uvicorn


def main() -> int:
    # Prepare mounted/private/local benchmark archives before importing the API.
    # Missing datasets are reported by the preparer but do not prevent demo/API startup.
    status = prepare_runtime_data()
    if status != 0:
        raise SystemExit(status)
    # Keep local development private to the workstation by default. Container and
    # reverse-proxy deployments must deliberately set XAITA_API_HOST as needed.
    uvicorn.run(
        "xaita_ot.api.app:app",
        host=os.environ.get("XAITA_API_HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8080")),
        reload=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
