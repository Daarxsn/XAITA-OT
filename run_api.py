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
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8080")),
        reload=False,
    )
