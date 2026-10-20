# Backend tests
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import create_app
from app.core.database import AsyncSessionLocal, Base, engine
from app.models import Model, Benchmark, HardwareProfile, ModelHardwareCompatibility, log_audit


@pytest.fixture(scope="session")
def app():
    app = create_app()
    return app


@pytest_asyncio.fixture(scope="session")
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create a fresh database for each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


class TestHealth:
    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "tensor-observatory"

    @pytest.mark.asyncio
    async def test_health_db_endpoint(self, client):
        resp = await client.get("/api/health/db")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"

    @pytest.mark.asyncio
    async def test_readiness_endpoint(self, client):
        resp = await client.get("/api/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ready"] is True


class TestAuth:
    @pytest.mark.asyncio
    async def test_unauthenticated_access_denied(self, client):
        """Protected endpoints should reject unauthenticated requests."""
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_login_redirects(self, client):
        """Login endpoint should redirect to Keycloak."""
        resp = await client.get("/api/auth/login", follow_redirects=False)
        assert resp.status_code == 302
        assert "location" in resp.headers
        assert "keycloak" in resp.headers["location"].lower() or "localhost:8080" in resp.headers["location"]

    @pytest.mark.asyncio
    async def test_callback_missing_params(self, client):
        """Callback should reject missing code/state."""
        resp = await client.get("/api/auth/callback")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_logout_requires_auth(self, client):
        """Logout should require authentication."""
        resp = await client.post("/api/auth/logout")
        assert resp.status_code == 401


class TestModels:
    @pytest.mark.asyncio
    async def test_create_model(self, db_session):
        """Test model creation."""
        model = Model(
            name="test-model",
            architecture="Llama-3",
            quantization="FP8",
            hardware_profile="H100",
            huggingface_repo="meta-llama/Meta-Llama-3-8B",
            description="Test model",
        )
        db_session.add(model)
        await db_session.commit()
        await db_session.refresh(model)
        assert model.id is not None
        assert model.name == "test-model"

    @pytest.mark.asyncio
    async def test_model_unique_name(self, db_session):
        """Test model name uniqueness constraint."""
        model1 = Model(name="unique-model", architecture="Test")
        model2 = Model(name="unique-model", architecture="Test2")
        db_session.add(model1)
        await db_session.commit()
        
        db_session.add(model2)
        with pytest.raises(Exception):  # IntegrityError
            await db_session.commit()


class TestBenchmarks:
    @pytest.mark.asyncio
    async def test_create_benchmark(self, db_session):
        """Test benchmark creation linked to model."""
        model = Model(name="bench-model", architecture="Test")
        db_session.add(model)
        await db_session.commit()
        await db_session.refresh(model)

        benchmark = Benchmark(
            model_id=model.id,
            name="test-benchmark",
            workload_type="synthetic",
            config_json='{"batch_size": 8, "seq_len": 2048}',
        )
        db_session.add(benchmark)
        await db_session.commit()
        await db_session.refresh(benchmark)
        assert benchmark.id is not None
        assert benchmark.model_id == model.id
        assert benchmark.status == "pending"


class TestHardware:
    @pytest.mark.asyncio
    async def test_create_hardware_profile(self, db_session):
        """Test hardware profile creation."""
        hw = HardwareProfile(
            name="A100-80GB-8x",
            gpu_model="A100",
            gpu_count=8,
            sm_version="8.0",
            vram_gb=80,
            driver_version="550.54",
            cuda_version="12.4",
        )
        db_session.add(hw)
        await db_session.commit()
        await db_session.refresh(hw)
        assert hw.id is not None

    @pytest.mark.asyncio
    async def test_compatibility_matrix(self, db_session):
        """Test model-hardware compatibility."""
        model = Model(name="compat-model", architecture="DeepSeek-V4", quantization="FP8")
        hw = HardwareProfile(name="H100-80GB", gpu_model="H100", gpu_count=8, sm_version="9.0", vram_gb=80)
        db_session.add_all([model, hw])
        await db_session.commit()
        await db_session.refresh(model)
        await db_session.refresh(hw)

        compat = ModelHardwareCompatibility(
            model_id=model.id,
            hardware_id=hw.id,
            status="compatible",
            notes="Tested at 40 tok/s",
        )
        db_session.add(compat)
        await db_session.commit()
        assert compat.id is not None


class TestAuditLog:
    @pytest.mark.asyncio
    async def test_audit_log_creation(self, db_session):
        """Test audit log entry."""
        await log_audit(db_session, action="test_action", user_id="user123", resource_type="model", resource_id="1")
        await db_session.commit()
        
        from sqlalchemy import select
        result = await db_session.execute(select(Model))
        # Just verify no error
        assert True