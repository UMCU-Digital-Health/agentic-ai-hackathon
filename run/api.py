import random

import uvicorn

from no_show_agent.api.app import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=random.randint(8000, 9000), log_level="info")
