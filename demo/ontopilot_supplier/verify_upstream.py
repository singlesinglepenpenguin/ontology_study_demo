"""Start the unmodified upstream FastAPI lifespan and verify native endpoints."""
import json
import os

from run import HERE, UPSTREAM, load_env


def main():
    load_env()
    settings = UPSTREAM / "config/settings.yaml"
    if not settings.exists():
        settings.write_text((HERE / "config/settings.example.yaml").read_text())
    os.chdir(UPSTREAM)
    from fastapi.testclient import TestClient
    from api.main import app

    with TestClient(app) as client:
        status = client.get("/api/ontology/status")
        assert status.status_code == 200
        assert set(status.json()["object_types"]) == {"Person", "City", "Company", "Book"}
        login = client.post("/api/login", json={"username": "admin", "password": "admin123"})
        assert login.status_code == 200
        people = app.state.runtime.query("upstream-check", "admin", "Person")
        assert people
        sessions = client.get("/api/sessions")
        assert sessions.status_code == 200
        result = {"startup": "passed", "ontology": status.json(),
                  "login": "passed", "sessions": "passed", "person_count": len(people)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    folder = HERE / "results"
    folder.mkdir(exist_ok=True)
    (folder / "upstream.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
