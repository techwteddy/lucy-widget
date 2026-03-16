import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from api.billing.kb_quota import check_knowledge_base_quota, KB_LIMITS, KBQuotaResult


@pytest.fixture
def mock_db():
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one.return_value = 0
    session.execute.return_value = result
    return session


async def test_free_plan_under_limit(mock_db):
    mock_db.execute.return_value.scalar_one.return_value = 5 * 1024 * 1024  # 5MB
    result = await check_knowledge_base_quota(uuid.uuid4(), mock_db, "free")
    assert result.allowed is True
    assert result.current_bytes == 5 * 1024 * 1024
    assert result.limit_bytes == 10 * 1024 * 1024


async def test_free_plan_at_limit(mock_db):
    mock_db.execute.return_value.scalar_one.return_value = 10 * 1024 * 1024  # 10MB
    result = await check_knowledge_base_quota(uuid.uuid4(), mock_db, "free")
    assert result.allowed is False
    assert result.current_bytes == 10 * 1024 * 1024


async def test_free_plan_over_limit(mock_db):
    mock_db.execute.return_value.scalar_one.return_value = 15 * 1024 * 1024  # 15MB
    result = await check_knowledge_base_quota(uuid.uuid4(), mock_db, "free")
    assert result.allowed is False


async def test_pro_plan_under_limit(mock_db):
    mock_db.execute.return_value.scalar_one.return_value = 100 * 1024 * 1024  # 100MB
    result = await check_knowledge_base_quota(uuid.uuid4(), mock_db, "pro")
    assert result.allowed is True
    assert result.limit_bytes == 500 * 1024 * 1024


async def test_pro_plan_at_limit(mock_db):
    mock_db.execute.return_value.scalar_one.return_value = 500 * 1024 * 1024  # 500MB
    result = await check_knowledge_base_quota(uuid.uuid4(), mock_db, "pro")
    assert result.allowed is False


async def test_business_plan_unlimited(mock_db):
    result = await check_knowledge_base_quota(uuid.uuid4(), mock_db, "business")
    assert result.allowed is True
    assert result.limit_bytes == -1
    # DB should not be queried for unlimited plans
    mock_db.execute.assert_not_called()


async def test_unknown_plan_defaults_to_free_limit(mock_db):
    mock_db.execute.return_value.scalar_one.return_value = 11 * 1024 * 1024  # 11MB
    result = await check_knowledge_base_quota(uuid.uuid4(), mock_db, "nonexistent")
    assert result.allowed is False
    assert result.limit_bytes == KB_LIMITS["free"]


async def test_empty_knowledge_base(mock_db):
    mock_db.execute.return_value.scalar_one.return_value = 0
    result = await check_knowledge_base_quota(uuid.uuid4(), mock_db, "free")
    assert result.allowed is True
    assert result.current_bytes == 0
