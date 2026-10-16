"""Run the account/workflow browser check against a disposable SQLite database."""
import tempfile
from pathlib import Path

import run
import runtime
import server

if __name__ == '__main__':
    run.load_env()
    import uvicorn
    with tempfile.TemporaryDirectory(prefix='supplier-account-check-') as tmp:
        runtime.DEFAULT_DB = Path(tmp) / 'test.db'
        server.DEFAULT_DB = runtime.DEFAULT_DB
        uvicorn.run(server.create_app(), host='127.0.0.1', port=8001)
