"""Tests for search functionality."""

import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import AsyncSessionLocal, engine, Base
from app.models.user import User
from app.models.job import Job
from app.models.tag import Tag
from app.utils.security import create_access_token, hash_password


@pytest.fixture
async def test_db():
    """Create test database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Create test user
        test_user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            hashed_password=hash_password("testpass123"),
        )
        session.add(test_user)
        await session.commit()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def auth_token():
    """Generate a valid JWT token for test user."""
    token = create_access_token({"user_id": 1, "username": "testuser"})
    return token


@pytest.fixture
def auth_headers(auth_token):
    """Generate authorization headers with valid token."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
async def search_test_data(test_db):
    """Create test data for search tests."""
    async with AsyncSessionLocal() as session:
        # Create tags
        tag1 = Tag(name="lecture", color="#2D6A4F")
        tag2 = Tag(name="interview", color="#40916C")
        tag3 = Tag(name="meeting", color="#52B788")
        session.add_all([tag1, tag2, tag3])
        await session.commit()
        await session.refresh(tag1)
        await session.refresh(tag2)
        await session.refresh(tag3)

        # Create jobs with different characteristics
        now = datetime.utcnow()

        # Job 1: Climate lecture with transcript
        job1 = Job(
            id="job-climate-1",
            user_id=1,
            original_filename="climate-change-lecture.mp4",
            saved_filename="climate_saved.mp4",
            file_path="/uploads/climate_saved.mp4",
            status="completed",
            created_at=now - timedelta(days=1),
        )
        job1.tags.append(tag1)

        # Job 2: Python interview with transcript
        job2 = Job(
            id="job-python-2",
            user_id=1,
            original_filename="python-developer-interview.mp3",
            saved_filename="python_saved.mp3",
            file_path="/uploads/python_saved.mp3",
            status="completed",
            created_at=now - timedelta(days=2),
        )
        job2.tags.append(tag2)

        # Job 3: Team meeting, no transcript
        job3 = Job(
            id="job-meeting-3",
            user_id=1,
            original_filename="team-standup-meeting.mp3",
            saved_filename="meeting_saved.mp3",
            file_path="/uploads/meeting_saved.mp3",
            status="queued",
            created_at=now - timedelta(days=3),
        )
        job3.tags.append(tag3)

        # Job 4: Climate documentary
        job4 = Job(
            id="job-climate-4",
            user_id=1,
            original_filename="climate-documentary.mp4",
            saved_filename="doc_saved.mp4",
            file_path="/uploads/doc_saved.mp4",
            status="completed",
            created_at=now - timedelta(days=5),
        )
        job4.tags.extend([tag1, tag3])

        session.add_all([job1, job2, job3, job4])
        await session.commit()

    return {
        "tag_ids": {"lecture": tag1.id, "interview": tag2.id, "meeting": tag3.id},
        "job_ids": {
            "climate1": "job-climate-1",
            "python2": "job-python-2",
            "meeting3": "job-meeting-3",
            "climate4": "job-climate-4",
        },
    }


class TestSearchBasics:
    """Test basic search functionality."""

    async def test_search_requires_query(self, test_db, auth_headers):
        """Test that search requires a query parameter."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/search", headers=auth_headers)
            assert response.status_code == 422

    async def test_search_requires_auth(self, test_db, search_test_data):
        """Test that search requires authentication."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/search?q=test")
            assert response.status_code == 403

    async def test_search_no_results(self, test_db, auth_headers, search_test_data):
        """Test search with no matching results."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/search?q=nonexistent", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "nonexistent"
            assert data["total"] == 0
            assert data["items"] == []


class TestFilenameSearch:
    """Test filename-based search."""

    async def test_search_by_filename(self, test_db, auth_headers, search_test_data):
        """Test searching by filename."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/search?q=climate", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "climate"
            assert data["total"] == 2
            assert len(data["items"]) == 2

            # Check that both climate jobs are returned
            job_ids = [item["job_id"] for item in data["items"]]
            assert search_test_data["job_ids"]["climate1"] in job_ids
            assert search_test_data["job_ids"]["climate4"] in job_ids

    async def test_search_case_insensitive(self, test_db, auth_headers, search_test_data):
        """Test that search is case-insensitive."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response1 = await client.get("/search?q=PYTHON", headers=auth_headers)
            response2 = await client.get("/search?q=python", headers=auth_headers)
            response3 = await client.get("/search?q=Python", headers=auth_headers)

            assert response1.status_code == 200
            assert response2.status_code == 200
            assert response3.status_code == 200

            data1 = response1.json()
            data2 = response2.json()
            data3 = response3.json()

            assert data1["total"] == data2["total"] == data3["total"]
            assert data1["total"] >= 1


class TestTagFiltering:
    """Test filtering by tags."""

    async def test_filter_by_single_tag(self, test_db, auth_headers, search_test_data):
        """Test filtering search results by a single tag."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            tag_id = search_test_data["tag_ids"]["lecture"]
            response = await client.get(f"/search?q=climate&tags={tag_id}", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2

            # Both climate jobs have the lecture tag
            for item in data["items"]:
                assert item["job_id"] in [
                    search_test_data["job_ids"]["climate1"],
                    search_test_data["job_ids"]["climate4"],
                ]

    async def test_filter_by_multiple_tags(self, test_db, auth_headers, search_test_data):
        """Test filtering by multiple tags (AND logic)."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            lecture_id = search_test_data["tag_ids"]["lecture"]
            meeting_id = search_test_data["tag_ids"]["meeting"]

            response = await client.get(
                f"/search?q=climate&tags={lecture_id},{meeting_id}",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1

            # Only job4 has both lecture and meeting tags
            assert data["items"][0]["job_id"] == search_test_data["job_ids"]["climate4"]

    async def test_search_all_with_tag_only(self, test_db, auth_headers, search_test_data):
        """Test searching with wildcard and tag filter."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            interview_id = search_test_data["tag_ids"]["interview"]

            # Search for anything with interview tag
            response = await client.get(f"/search?q=*&tags={interview_id}", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert data["items"][0]["job_id"] == search_test_data["job_ids"]["python2"]


class TestStatusFiltering:
    """Test filtering by job status."""

    async def test_filter_by_status(self, test_db, auth_headers, search_test_data):
        """Test filtering search results by status."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/search?q=*&status=completed", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 3

            # All returned jobs should be completed
            for item in data["items"]:
                assert item["status"] == "completed"

    async def test_filter_by_status_queued(self, test_db, auth_headers, search_test_data):
        """Test filtering for queued jobs."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/search?q=meeting&status=queued", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert data["items"][0]["job_id"] == search_test_data["job_ids"]["meeting3"]


class TestDateFiltering:
    """Test filtering by date range."""

    async def test_filter_by_date_from(self, test_db, auth_headers, search_test_data):
        """Test filtering by start date."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Get jobs from last 2 days (should get jobs created 1 day ago)
            cutoff = (datetime.utcnow() - timedelta(days=1, hours=1)).isoformat()
            response = await client.get(f"/search?q=*&date_from={cutoff}", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()

            # Should get job 1 (day 1), but not 2, 3, 4 (days 2, 3, and 5)
            assert data["total"] == 1

    async def test_filter_by_date_range(self, test_db, auth_headers, search_test_data):
        """Test filtering by date range."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Get jobs between 4 and 2 days ago
            date_from = (datetime.utcnow() - timedelta(days=4)).isoformat()
            date_to = (datetime.utcnow() - timedelta(days=2)).isoformat()

            response = await client.get(
                f"/search?q=*&date_from={date_from}&date_to={date_to}",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()

            # Should get jobs 2 and 3 (days 2 and 3)
            assert data["total"] == 2


class TestPagination:
    """Test search pagination."""

    async def test_pagination_limit(self, test_db, auth_headers, search_test_data):
        """Test limiting search results."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/search?q=*&limit=2", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 2
            assert data["total"] == 4  # Total matches, not returned count

    async def test_pagination_offset(self, test_db, auth_headers, search_test_data):
        """Test offsetting search results."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Get first 2
            response1 = await client.get("/search?q=*&limit=2&offset=0", headers=auth_headers)
            # Get next 2
            response2 = await client.get("/search?q=*&limit=2&offset=2", headers=auth_headers)

            assert response1.status_code == 200
            assert response2.status_code == 200

            data1 = response1.json()
            data2 = response2.json()

            # Should get different jobs
            ids1 = {item["job_id"] for item in data1["items"]}
            ids2 = {item["job_id"] for item in data2["items"]}
            assert len(ids1 & ids2) == 0  # No overlap


class TestSearchMatches:
    """Test search match highlighting."""

    async def test_match_information(self, test_db, auth_headers, search_test_data):
        """Test that search results include match information."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/search?q=climate", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["total"] >= 1

            # Check first result has matches
            first_result = data["items"][0]
            assert "matches" in first_result
            assert len(first_result["matches"]) > 0

            # Check match structure
            match = first_result["matches"][0]
            assert "type" in match
            assert match["type"] == "filename"
            assert "text" in match
            assert "highlight" in match

    async def test_highlight_contains_mark_tags(self, test_db, auth_headers, search_test_data):
        """Test that highlights wrap matches in <mark> tags."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/search?q=climate", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()

            # Find a result with matches
            for item in data["items"]:
                for match in item["matches"]:
                    if "climate" in match["text"].lower():
                        assert "<mark>" in match["highlight"]
                        assert "</mark>" in match["highlight"]
                        return

            # Should have found at least one match
            pytest.fail("No matches with highlight found")
