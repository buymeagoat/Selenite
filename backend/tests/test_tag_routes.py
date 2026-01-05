"""Tests for tag management routes."""

import pytest
from httpx import AsyncClient, ASGITransport

from fastapi import HTTPException
from app.main import app
from app.models.user import User
from app.models.job import Job
from app.models.tag import Tag
from app.utils.security import hash_password, create_access_token
from app.database import AsyncSessionLocal, engine, Base
from app.routes import tags as tags_module
from app.schemas.tag import TagCreate, TagUpdate, TagAssignment


@pytest.fixture
async def test_db():
    """Create test database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Create test user with explicit ID
        test_user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            hashed_password=hash_password("testpass123"),
            is_admin=True,
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
async def sample_tags(test_db):
    """Create sample tags."""
    async with AsyncSessionLocal() as session:
        tags = [
            Tag(name="interviews", color="#2D6A4F"),
            Tag(name="lectures", color="#40916C"),
            Tag(name="meetings", color="#52B788"),
        ]
        session.add_all(tags)
        await session.commit()
        for tag in tags:
            await session.refresh(tag)
        tag_ids = [tag.id for tag in tags]

    # Return fresh tags from DB
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        result = await session.execute(select(Tag).where(Tag.id.in_(tag_ids)))
        return result.scalars().all()


@pytest.fixture
async def sample_job(test_db):
    """Create a sample job."""
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        # Get the user
        result = await session.execute(select(User).where(User.username == "testuser"))
        user = result.scalar_one()

        job = Job(
            id="test-job-123",
            user_id=user.id,
            original_filename="test.mp3",
            saved_filename="test_saved.mp3",
            file_path="/uploads/test_saved.mp3",
            file_size=1024,
            mime_type="audio/mpeg",
            status="completed",
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        job_id = job.id

    # Return fresh job from DB
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one()


class TestTagCRUD:
    """Test tag CRUD operations."""

    async def test_list_tags_empty(self, test_db, auth_headers: dict):
        """Test listing tags when none exist."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/tags", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert data["items"] == []

    async def test_create_tag_minimal(self, test_db, auth_headers: dict):
        """Test creating a tag with minimal fields."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/tags", headers=auth_headers, json={"name": "important"})
            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "important"
            assert data["id"] > 0
            assert data["job_count"] == 0
            assert data["scope"] == "global"
            assert data["owner_user_id"] is None
            assert "created_at" in data
            # Color should be auto-assigned or null
            assert data["color"] is None or data["color"].startswith("#")

    async def test_create_tag_with_color(self, test_db, auth_headers: dict):
        """Test creating a tag with color."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/tags",
                headers=auth_headers,
                json={"name": "urgent", "color": "#FF5733"},
            )
            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "urgent"
            assert data["color"] == "#FF5733"
            assert data["scope"] == "global"
            assert data["owner_user_id"] is None

    async def test_create_tag_duplicate_name(
        self, test_db, auth_headers: dict, sample_tags: list[Tag]
    ):
        """Test creating a tag with duplicate name fails."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/tags", headers=auth_headers, json={"name": "interviews"})
            assert response.status_code == 400
            assert "already exists" in response.json()["detail"].lower()

    async def test_create_tag_invalid_color(self, test_db, auth_headers: dict):
        """Test creating a tag with invalid color fails."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/tags", headers=auth_headers, json={"name": "test", "color": "red"}
            )
            assert response.status_code == 422

    async def test_create_tag_empty_name(self, test_db, auth_headers: dict):
        """Test creating a tag with empty name fails."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/tags", headers=auth_headers, json={"name": ""})
            assert response.status_code == 422

    async def test_create_tag_long_name(self, test_db, auth_headers: dict):
        """Test creating a tag with name too long fails."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/tags", headers=auth_headers, json={"name": "x" * 51})
            assert response.status_code == 422

    async def test_create_personal_tag_for_non_admin(self, test_db):
        """Non-admin users should create personal tags."""
        async with AsyncSessionLocal() as session:
            user = User(
                id=2,
                username="regular",
                email="regular@example.com",
                hashed_password=hash_password("password123"),
                is_admin=False,
            )
            session.add(user)
            await session.commit()
        token = create_access_token({"user_id": 2, "username": "regular"})
        headers = {"Authorization": f"Bearer {token}"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/tags", headers=headers, json={"name": "personal"})
            assert response.status_code == 201
            data = response.json()
            assert data["scope"] == "personal"
            assert data["owner_user_id"] == 2

    async def test_list_tags_with_data(self, test_db, auth_headers: dict, sample_tags: list[Tag]):
        """Test listing tags returns all tags."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/tags", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 3
            assert len(data["items"]) == 3
            names = [tag["name"] for tag in data["items"]]
            assert "interviews" in names
            assert "lectures" in names
            assert "meetings" in names
            for tag in data["items"]:
                assert tag["scope"] == "global"

    async def test_update_tag_name(self, test_db, auth_headers: dict, sample_tags: list[Tag]):
        """Test updating tag name."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            tag_id = sample_tags[0].id
            response = await client.put(
                f"/tags/{tag_id}",
                headers=auth_headers,
                json={"name": "interviews-updated"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "interviews-updated"
            assert data["color"] == "#2D6A4F"
            assert data["id"] == tag_id

    async def test_update_tag_color(self, test_db, auth_headers: dict, sample_tags: list[Tag]):
        """Test updating tag color."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            tag_id = sample_tags[1].id
            response = await client.put(
                f"/tags/{tag_id}", headers=auth_headers, json={"color": "#123456"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["color"] == "#123456"
            assert data["name"] == "lectures"

    async def test_update_tag_both_fields(
        self, test_db, auth_headers: dict, sample_tags: list[Tag]
    ):
        """Test updating both name and color."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            tag_id = sample_tags[2].id
            response = await client.put(
                f"/tags/{tag_id}",
                headers=auth_headers,
                json={"name": "gatherings", "color": "#ABCDEF"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "gatherings"
            assert data["color"] == "#ABCDEF"

    async def test_update_tag_nonexistent(self, test_db, auth_headers: dict):
        """Test updating nonexistent tag fails."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.put("/tags/99999", headers=auth_headers, json={"name": "test"})
            assert response.status_code == 404

    async def test_update_tag_duplicate_name(
        self, test_db, auth_headers: dict, sample_tags: list[Tag]
    ):
        """Test updating tag to duplicate name fails."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            tag_id = sample_tags[0].id
            response = await client.put(
                f"/tags/{tag_id}", headers=auth_headers, json={"name": "lectures"}
            )
            assert response.status_code == 400
            assert "already exists" in response.json()["detail"].lower()

    async def test_delete_tag(self, test_db, auth_headers: dict, sample_tags: list[Tag]):
        """Test deleting a tag."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            tag_id = sample_tags[0].id
            response = await client.delete(f"/tags/{tag_id}", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Tag deleted successfully"
            assert data["id"] == tag_id
            assert data["jobs_affected"] == 0

            # Verify it's gone
            response = await client.get("/tags", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2

    async def test_delete_tag_nonexistent(self, test_db, auth_headers: dict):
        """Test deleting nonexistent tag fails."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.delete("/tags/99999", headers=auth_headers)
            assert response.status_code == 404

    async def test_unauthorized_access(self, test_db):
        """Test that all tag endpoints require authentication."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            endpoints = [
                ("GET", "/tags"),
                ("POST", "/tags"),
                ("PUT", "/tags/1"),
                ("DELETE", "/tags/1"),
            ]
            for method, url in endpoints:
                if method == "GET":
                    response = await client.get(url)
                elif method == "POST":
                    response = await client.post(url, json={"name": "test"})
                elif method == "PUT":
                    response = await client.put(url, json={"name": "test"})
                elif method == "DELETE":
                    response = await client.delete(url)
                assert response.status_code == 403


class TestJobTagAssociations:
    """Test job-tag association operations."""

    async def test_assign_tags_to_job(
        self,
        test_db,
        auth_headers: dict,
        sample_job: Job,
        sample_tags: list[Tag],
    ):
        """Test assigning multiple tags to a job."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            tag_ids = [sample_tags[0].id, sample_tags[2].id]
            response = await client.post(
                f"/jobs/{sample_job.id}/tags",
                headers=auth_headers,
                json={"tag_ids": tag_ids},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == sample_job.id
            assert len(data["tags"]) == 2
            returned_tag_ids = [tag["id"] for tag in data["tags"]]
            assert sample_tags[0].id in returned_tag_ids
            assert sample_tags[2].id in returned_tag_ids

    async def test_assign_tags_empty_list(self, test_db, auth_headers: dict, sample_job: Job):
        """Test assigning empty tag list clears tags."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/jobs/{sample_job.id}/tags", headers=auth_headers, json={"tag_ids": []}
            )
            assert response.status_code == 200
            assert response.json()["tags"] == []

    async def test_assign_tags_nonexistent_job(
        self, test_db, auth_headers: dict, sample_tags: list[Tag]
    ):
        """Test assigning tags to nonexistent job fails."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/jobs/nonexistent/tags",
                headers=auth_headers,
                json={"tag_ids": [sample_tags[0].id]},
            )
            assert response.status_code == 404

    async def test_assign_nonexistent_tag(self, test_db, auth_headers: dict, sample_job: Job):
        """Test assigning nonexistent tag fails."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/jobs/{sample_job.id}/tags",
                headers=auth_headers,
                json={"tag_ids": [99999]},
            )
            assert response.status_code == 404

    async def test_assign_tags_idempotent(
        self,
        test_db,
        auth_headers: dict,
        sample_job: Job,
        sample_tags: list[Tag],
    ):
        """Test assigning same tags multiple times is idempotent."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            tag_ids = [sample_tags[0].id]

            # First assignment
            response = await client.post(
                f"/jobs/{sample_job.id}/tags",
                headers=auth_headers,
                json={"tag_ids": tag_ids},
            )
            assert response.status_code == 200
            assert len(response.json()["tags"]) == 1

            # Second assignment - should not duplicate
            response = await client.post(
                f"/jobs/{sample_job.id}/tags",
                headers=auth_headers,
                json={"tag_ids": tag_ids},
            )
            assert response.status_code == 200
            assert len(response.json()["tags"]) == 1

    async def test_remove_tag_from_job(
        self,
        test_db,
        auth_headers: dict,
        sample_job: Job,
        sample_tags: list[Tag],
    ):
        """Test removing a tag from a job."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # First assign tags
            tag_ids = [sample_tags[0].id, sample_tags[1].id]
            await client.post(
                f"/jobs/{sample_job.id}/tags",
                headers=auth_headers,
                json={"tag_ids": tag_ids},
            )

            # Remove one tag
            response = await client.delete(
                f"/jobs/{sample_job.id}/tags/{sample_tags[0].id}", headers=auth_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Tag removed from job"
            assert data["job_id"] == sample_job.id
            assert data["tag_id"] == sample_tags[0].id

    async def test_remove_tag_not_assigned(
        self,
        test_db,
        auth_headers: dict,
        sample_job: Job,
        sample_tags: list[Tag],
    ):
        """Test removing a tag that isn't assigned fails."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.delete(
                f"/jobs/{sample_job.id}/tags/{sample_tags[0].id}", headers=auth_headers
            )
            assert response.status_code == 404

    async def test_remove_tag_nonexistent_job(
        self, test_db, auth_headers: dict, sample_tags: list[Tag]
    ):
        """Test removing tag from nonexistent job fails."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.delete(
                f"/jobs/nonexistent/tags/{sample_tags[0].id}", headers=auth_headers
            )
            assert response.status_code == 404

    async def test_delete_tag_removes_from_jobs(
        self,
        test_db,
        auth_headers: dict,
        sample_job: Job,
        sample_tags: list[Tag],
    ):
        """Test that deleting a tag removes it from all jobs."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Assign tag to job
            tag_id = sample_tags[0].id
            await client.post(
                f"/jobs/{sample_job.id}/tags",
                headers=auth_headers,
                json={"tag_ids": [tag_id]},
            )

            # Delete the tag
            response = await client.delete(f"/tags/{tag_id}", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["jobs_affected"] == 1

            # Verify job no longer has the tag by querying the job
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select
                from sqlalchemy.orm import selectinload

                result = await session.execute(
                    select(Job).where(Job.id == sample_job.id).options(selectinload(Job.tags))
                )
                job = result.scalar_one()
                assert len(job.tags) == 0

    async def test_job_count_in_tag_list(
        self,
        test_db,
        auth_headers: dict,
        sample_job: Job,
        sample_tags: list[Tag],
    ):
        """Test that tag list shows correct job_count."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Assign tags to job
            tag_ids = [sample_tags[0].id, sample_tags[1].id]
            await client.post(
                f"/jobs/{sample_job.id}/tags",
                headers=auth_headers,
                json={"tag_ids": tag_ids},
            )

            # List tags
            response = await client.get("/tags", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()

            # Find the assigned tags and check their counts
            for tag_data in data["items"]:
                if tag_data["id"] in tag_ids:
                    assert tag_data["job_count"] == 1
                else:
                    assert tag_data["job_count"] == 0


@pytest.mark.asyncio
class TestTagRouteDirect:
    """Directly invoke tag route functions to boost coverage of branches."""

    async def test_create_tag_direct(self, test_db):
        async with AsyncSessionLocal() as session:
            user = await session.get(User, 1)
            resp = await tags_module.create_tag(
                TagCreate(name="direct", color="#123456"),
                db=session,
                current_user=user,
            )
        assert resp.name == "direct"
        assert resp.job_count == 0

    async def test_create_tag_duplicate_direct(self, test_db):
        async with AsyncSessionLocal() as session:
            user = await session.get(User, 1)
            await tags_module.create_tag(TagCreate(name="dup"), db=session, current_user=user)
            with pytest.raises(HTTPException) as exc:
                await tags_module.create_tag(TagCreate(name="dup"), db=session, current_user=user)
            assert exc.value.status_code == 400

    async def test_update_tag_conflict_direct(self, test_db):
        async with AsyncSessionLocal() as session:
            user = await session.get(User, 1)
            first = await tags_module.create_tag(
                TagCreate(name="first"), db=session, current_user=user
            )
            await tags_module.create_tag(TagCreate(name="second"), db=session, current_user=user)
            with pytest.raises(HTTPException):
                await tags_module.update_tag(
                    first.id,
                    TagUpdate(name="second"),
                    db=session,
                    current_user=user,
                )

    async def test_delete_tag_not_found_direct(self, test_db):
        async with AsyncSessionLocal() as session:
            user = await session.get(User, 1)
            with pytest.raises(HTTPException) as exc:
                await tags_module.delete_tag(999, db=session, current_user=user)
            assert exc.value.status_code == 404

    async def test_assign_tags_to_job_direct(self, test_db, sample_job, sample_tags):
        assignment = TagAssignment(tag_ids=[sample_tags[0].id])
        async with AsyncSessionLocal() as session:
            user = await session.get(User, 1)
            resp = await tags_module.assign_tags_to_job(
                sample_job.id,
                assignment,
                db=session,
                current_user=user,
            )
        assert resp.job_id == sample_job.id
        assert resp.tags[0].id == sample_tags[0].id

    async def test_assign_tags_invalid_payload_direct(self, test_db, sample_job):
        async with AsyncSessionLocal() as session:
            user = await session.get(User, 1)
            resp = await tags_module.assign_tags_to_job(
                sample_job.id,
                TagAssignment(tag_ids=[]),
                db=session,
                current_user=user,
            )
            assert resp.tags == []

    async def test_remove_tag_from_job_direct(self, test_db, sample_job, sample_tags):
        async with AsyncSessionLocal() as session:
            user = await session.get(User, 1)
            await tags_module.assign_tags_to_job(
                sample_job.id,
                TagAssignment(tag_ids=[sample_tags[0].id]),
                db=session,
                current_user=user,
            )
            resp = await tags_module.remove_tag_from_job(
                sample_job.id, sample_tags[0].id, db=session, current_user=user
            )
        assert resp.tag_id == sample_tags[0].id

    async def test_remove_tag_missing_direct(self, test_db, sample_job):
        async with AsyncSessionLocal() as session:
            user = await session.get(User, 1)
            with pytest.raises(HTTPException):
                await tags_module.remove_tag_from_job(
                    sample_job.id, 999, db=session, current_user=user
                )
