"""Quick script to exercise /jobs endpoint using TestClient."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def main():
    # Obtain token
    resp = client.post("/auth/login", json={"username": "admin", "password": "changeme"})
    print("Login status", resp.status_code)
    if resp.status_code != 200:
        print(resp.text)
        return
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    jobs_resp = client.get("/jobs", headers=headers)
    print("Jobs status", jobs_resp.status_code)
    print(jobs_resp.text[:500])


if __name__ == "__main__":
    main()
