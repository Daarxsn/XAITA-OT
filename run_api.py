import os
from scripts.prepare_runtime_data import main as prepare_runtime_data
import uvicorn


if __name__ == "__main__":
    # Prepare mounted/private/local benchmark archives before importing the API.
    # Missing datasets are reported by the preparer but do not prevent demo/API startup.
    status = prepare_runtime_data()
    if status != 0:
        raise SystemExit(status)
    uvicorn.run(
        "xaita_ot.api.app:app",
        # Keep local developer runs on loopback unless deployment explicitly opts in.
        host=os.environ.get("XAITA_HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8080")),
        reload=False,
    )
