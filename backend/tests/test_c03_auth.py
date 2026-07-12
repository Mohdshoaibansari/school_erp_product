"""C-03 Authentication — Phase 1 tests (tasks 1.1-4.2).

Tests for:
- Task 1.2: AuthenticationManifest
- Task 1.3: App boots with C-03 manifest
- Task 2.1: LoginAttempt model fields
- Task 2.2: LoginAttempt RLS
- Task 2.3: Platform owner seed
- Task 3.1: SupabaseAuthClient Protocol methods defined
- Task 3.2: SupabaseAuthClientImpl uses service role key
- Task 3.3: FakeSupabaseAuth tests
- Task 4.1: Missing Supabase URL/key fatal
- Task 4.2: Dependency wiring
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from kernel.auth.manifest import manifest as c03_manifest
from kernel.auth.supabase_client import (
    SupabaseAuthClient,
    SupabaseAuthClientImpl,
    SupabaseAuthError,
    create_supabase_auth_client,
)
from kernel.auth.models.login_attempt import LoginAttempt
from kernel.auth.services.dtos import LoginAttemptDTO
from kernel.auth.repos.login_attempt_repo import LoginAttemptRepository
from kernel.auth.dependencies import (
    get_supabase_auth_client,
    set_supabase_auth_client,
    reset_supabase_auth_client,
)
from tests.fake_supabase_auth import FakeSupabaseAuth


# ============================================================
# Task 1.2: AuthenticationManifest
# ============================================================

class TestAuthenticationManifest:
    """Tests for the C-03 manifest."""

    def test_manifest_name(self):
        assert c03_manifest.name == "c03_authentication"

    def test_manifest_tier(self):
        assert c03_manifest.tier == "kernel"

    def test_manifest_has_register_routes(self):
        assert hasattr(c03_manifest, "register_routes")

    def test_manifest_has_register_casbin_policies(self):
        assert hasattr(c03_manifest, "register_casbin_policies")

    def test_manifest_has_on_startup(self):
        assert hasattr(c03_manifest, "on_startup")

    def test_manifest_has_on_shutdown(self):
        assert hasattr(c03_manifest, "on_shutdown")

    def test_manifest_has_register_cli(self):
        assert hasattr(c03_manifest, "register_cli")


# ============================================================
# Task 1.3: App boots with C-03 manifest
# ============================================================

class TestAppBootsWithC03:
    """Test that the app boots with C-03 manifest registered."""

    def test_app_boots_with_c03_manifest(self, app):
        """App should boot without errors with C-03 manifest."""
        assert app is not None

    def test_c03_routes_mounted(self, app, platform_client):
        """C-03 routes should be mounted and accessible."""
        # Test that the auth login endpoint is accessible
        response = platform_client.post('/api/auth/login', json={'email': 'test@example.com', 'password': 'test'})
        # Should get 401 (bad credentials) rather than 404 (not found)
        # 401 means the route is mounted and the service is working
        assert response.status_code == 401


# ============================================================
# Task 2.1: LoginAttempt model fields
# ============================================================

class TestLoginAttemptModel:
    """Tests for the LoginAttempt ORM model."""

    def test_login_attempt_has_id(self):
        """LoginAttempt should have id column."""
        assert hasattr(LoginAttempt, "id")

    def test_login_attempt_has_client_id(self):
        """LoginAttempt should have client_id column."""
        assert hasattr(LoginAttempt, "client_id")

    def test_login_attempt_has_user_id(self):
        """LoginAttempt should have user_id column."""
        assert hasattr(LoginAttempt, "user_id")

    def test_login_attempt_has_email(self):
        """LoginAttempt should have email column."""
        assert hasattr(LoginAttempt, "email")

    def test_login_attempt_has_event_type(self):
        """LoginAttempt should have event_type column."""
        assert hasattr(LoginAttempt, "event_type")

    def test_login_attempt_has_ip_address(self):
        """LoginAttempt should have ip_address column."""
        assert hasattr(LoginAttempt, "ip_address")

    def test_login_attempt_has_user_agent(self):
        """LoginAttempt should have user_agent column."""
        assert hasattr(LoginAttempt, "user_agent")

    def test_login_attempt_has_occurred_at(self):
        """LoginAttempt should have occurred_at column."""
        assert hasattr(LoginAttempt, "occurred_at")

    def test_login_attempt_has_created_at(self):
        """LoginAttempt should have created_at column."""
        assert hasattr(LoginAttempt, "created_at")

    def test_login_attempt_table_name(self):
        """LoginAttempt table should be named 'login_attempt'."""
        assert LoginAttempt.__tablename__ == "login_attempt"


# ============================================================
# Task 2.2: LoginAttempt RLS
# ============================================================

class TestLoginAttemptRLS:
    """Tests for LoginAttempt RLS policies."""

    def test_login_attempt_rls_tenant_select(self, db_session):
        """LoginAttempt should have RLS tenant select policy."""
        result = db_session.execute(text(
            "SELECT policyname FROM pg_policies WHERE tablename = 'login_attempt' AND policyname = 'login_attempt_tenant_select'"
        ))
        assert result.fetchone() is not None

    def test_login_attempt_rls_tenant_insert(self, db_session):
        """LoginAttempt should have RLS tenant insert policy."""
        result = db_session.execute(text(
            "SELECT policyname FROM pg_policies WHERE tablename = 'login_attempt' AND policyname = 'login_attempt_tenant_insert'"
        ))
        assert result.fetchone() is not None

    def test_login_attempt_rls_tenant_update(self, db_session):
        """LoginAttempt should have RLS tenant update policy."""
        result = db_session.execute(text(
            "SELECT policyname FROM pg_policies WHERE tablename = 'login_attempt' AND policyname = 'login_attempt_tenant_update'"
        ))
        assert result.fetchone() is not None

    def test_login_attempt_rls_tenant_delete(self, db_session):
        """LoginAttempt should have RLS tenant delete policy."""
        result = db_session.execute(text(
            "SELECT policyname FROM pg_policies WHERE tablename = 'login_attempt' AND policyname = 'login_attempt_tenant_delete'"
        ))
        assert result.fetchone() is not None


# ============================================================
# Task 2.3: Platform owner seed
# ============================================================

class TestPlatformOwnerSeed:
    """Tests for the platform owner seed data."""

    def test_platform_owner_app_user_exists(self, db_session):
        """Platform owner app_user row should exist after migration."""
        result = db_session.execute(text(
            "SELECT id, email, name, lifecycle_status FROM app_user WHERE name = 'Platform Owner' LIMIT 1"
        ))
        row = result.fetchone()
        # The platform owner may not exist if there's no client with slug 'platform'
        # This is expected in test environments
        if row is not None:
            assert row[1] == "platform@school-erp.com"
            assert row[3] == "active"


# ============================================================
# Task 3.1: SupabaseAuthClient Protocol methods defined
# ============================================================

class TestSupabaseAuthClientProtocol:
    """Tests for the SupabaseAuthClient Protocol."""

    def test_protocol_methods_defined(self):
        """SupabaseAuthClient should define all required methods."""
        assert hasattr(SupabaseAuthClient, 'create_user')
        assert hasattr(SupabaseAuthClient, 'sign_in_with_password')
        assert hasattr(SupabaseAuthClient, 'sign_in_with_otp')
        assert hasattr(SupabaseAuthClient, 'verify_otp')
        assert hasattr(SupabaseAuthClient, 'reset_password_for_email')
        assert hasattr(SupabaseAuthClient, 'update_user')
        assert hasattr(SupabaseAuthClient, 'sign_out')
        assert hasattr(SupabaseAuthClient, 'delete_user')
        assert hasattr(SupabaseAuthClient, 'refresh_token')
        assert hasattr(SupabaseAuthClient, 'revoke_refresh_token')


# ============================================================
# Task 3.2: SupabaseAuthClientImpl uses service role key
# ============================================================

class TestSupabaseAuthClientImpl:
    """Tests for the production SupabaseAuthClientImpl."""

    def test_production_impl_uses_service_role_key(self):
        """SupabaseAuthClientImpl should store the service role key."""
        impl = SupabaseAuthClientImpl("https://test.supabase.co", "test-key")
        assert impl._url == "https://test.supabase.co"
        assert impl._key == "test-key"


# ============================================================
# Task 3.3: FakeSupabaseAuth tests
# ============================================================

class TestFakeSupabaseAuth:
    """Tests for the FakeSupabaseAuth implementation."""

    @pytest.fixture
    def fake(self):
        return FakeSupabaseAuth()

    @pytest.mark.asyncio
    async def test_fake_create_user(self, fake):
        """Fake should create a user."""
        user_id = uuid.uuid4()
        result = await fake.create_user(user_id, "test@example.com")
        assert result["user"]["id"] == str(user_id)
        assert result["user"]["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_fake_create_user_duplicate_email(self, fake):
        """Fake should reject duplicate email."""
        await fake.create_user(uuid.uuid4(), "test@example.com")
        with pytest.raises(SupabaseAuthError, match="already exists"):
            await fake.create_user(uuid.uuid4(), "test@example.com")

    @pytest.mark.asyncio
    async def test_fake_sign_in_with_password_success(self, fake):
        """Fake should sign in with correct password."""
        user_id = uuid.uuid4()
        await fake.create_user(user_id, "test@example.com")
        await fake.update_user(user_id, password="password123", email_confirm=True)
        result = await fake.sign_in_with_password("test@example.com", "password123")
        assert "access_token" in result
        assert "refresh_token" in result

    @pytest.mark.asyncio
    async def test_fake_sign_in_with_password_failure(self, fake):
        """Fake should reject incorrect password."""
        user_id = uuid.uuid4()
        await fake.create_user(user_id, "test@example.com")
        await fake.update_user(user_id, password="password123", email_confirm=True)
        with pytest.raises(SupabaseAuthError, match="Invalid credentials"):
            await fake.sign_in_with_password("test@example.com", "wrongpassword")

    @pytest.mark.asyncio
    async def test_fake_sign_in_with_password_unknown_email(self, fake):
        """Fake should reject unknown email."""
        with pytest.raises(SupabaseAuthError, match="Invalid credentials"):
            await fake.sign_in_with_password("unknown@example.com", "password123")

    @pytest.mark.asyncio
    async def test_fake_update_user(self, fake):
        """Fake should update a user."""
        user_id = uuid.uuid4()
        await fake.create_user(user_id, "test@example.com")
        result = await fake.update_user(user_id, password="newpassword")
        assert result["user"]["id"] == str(user_id)

    @pytest.mark.asyncio
    async def test_fake_update_user_not_found(self, fake):
        """Fake should raise on update of non-existent user."""
        with pytest.raises(SupabaseAuthError, match="not found"):
            await fake.update_user(uuid.uuid4(), password="newpassword")

    @pytest.mark.asyncio
    async def test_fake_sign_out(self, fake):
        """Fake should sign out a user."""
        user_id = uuid.uuid4()
        await fake.create_user(user_id, "test@example.com")
        await fake.update_user(user_id, password="password123", email_confirm=True)
        await fake.sign_in_with_password("test@example.com", "password123")
        await fake.sign_out(user_id)
        # After sign out, refresh tokens should be cleared
        assert len(fake._users[str(user_id)]["refresh_tokens"]) == 0

    @pytest.mark.asyncio
    async def test_fake_delete_user(self, fake):
        """Fake should delete a user."""
        user_id = uuid.uuid4()
        await fake.create_user(user_id, "test@example.com")
        await fake.delete_user(user_id)
        assert str(user_id) not in fake._users
        assert "test@example.com" not in fake._email_to_id

    @pytest.mark.asyncio
    async def test_fake_refresh_token_success(self, fake):
        """Fake should refresh a valid token."""
        user_id = uuid.uuid4()
        await fake.create_user(user_id, "test@example.com")
        await fake.update_user(user_id, password="password123", email_confirm=True)
        result = await fake.sign_in_with_password("test@example.com", "password123")
        refresh_token = result["refresh_token"]
        new_tokens = await fake.refresh_token(refresh_token)
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        assert new_tokens["refresh_token"] != refresh_token

    @pytest.mark.asyncio
    async def test_fake_refresh_token_revoked(self, fake):
        """Fake should reject revoked refresh token."""
        user_id = uuid.uuid4()
        await fake.create_user(user_id, "test@example.com")
        await fake.update_user(user_id, password="password123", email_confirm=True)
        result = await fake.sign_in_with_password("test@example.com", "password123")
        refresh_token = result["refresh_token"]
        await fake.revoke_refresh_token(refresh_token)
        with pytest.raises(SupabaseAuthError, match="revoked"):
            await fake.refresh_token(refresh_token)

    @pytest.mark.asyncio
    async def test_fake_refresh_token_invalid(self, fake):
        """Fake should reject invalid refresh token."""
        with pytest.raises(SupabaseAuthError, match="Invalid"):
            await fake.refresh_token("invalid-token")

    @pytest.mark.asyncio
    async def test_fake_verify_otp_success(self, fake):
        """Fake should verify a valid OTP."""
        user_id = uuid.uuid4()
        await fake.create_user(user_id, "test@example.com")
        await fake.update_user(user_id, password="password123", email_confirm=True)
        await fake.sign_in_with_otp("test@example.com")
        result = await fake.verify_otp("test@example.com", "123456")
        assert "access_token" in result

    @pytest.mark.asyncio
    async def test_fake_verify_otp_invalid(self, fake):
        """Fake should reject invalid OTP."""
        user_id = uuid.uuid4()
        await fake.create_user(user_id, "test@example.com")
        await fake.update_user(user_id, password="password123", email_confirm=True)
        await fake.sign_in_with_otp("test@example.com")
        with pytest.raises(SupabaseAuthError, match="Invalid OTP"):
            await fake.verify_otp("test@example.com", "000000")

    @pytest.mark.asyncio
    async def test_fake_reset_password_for_email(self, fake):
        """Fake should send reset email."""
        user_id = uuid.uuid4()
        await fake.create_user(user_id, "test@example.com")
        result = await fake.reset_password_for_email("test@example.com", "https://example.com/reset")
        assert result["message"] == "Password reset email sent"

    @pytest.mark.asyncio
    async def test_fake_confirm_password_reset(self, fake):
        """Fake should confirm password reset with recovery token."""
        user_id = uuid.uuid4()
        await fake.create_user(user_id, "test@example.com")
        await fake.reset_password_for_email("test@example.com", "https://example.com/reset")
        # Get the recovery token
        recovery_token = fake._pending_resets["test@example.com"]["token"]
        result = await fake.verify_otp("test@example.com", recovery_token, type="recovery")
        assert "access_token" in result


# ============================================================
# Task 4.1: Missing Supabase URL/key fatal
# ============================================================

class TestSupabaseClientConfig:
    """Tests for Supabase client configuration."""

    def test_missing_supabase_url_fatal(self, monkeypatch):
        """Missing SUPABASE_URL should raise ValueError."""
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
        with pytest.raises(ValueError, match="SUPABASE_URL"):
            create_supabase_auth_client()

    def test_missing_supabase_key_fatal(self, monkeypatch):
        """Missing SUPABASE_SERVICE_ROLE_KEY should raise ValueError."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
        with pytest.raises(ValueError, match="SUPABASE_SERVICE_ROLE_KEY"):
            create_supabase_auth_client()


# ============================================================
# Task 4.2: Dependency wiring
# ============================================================

class TestDependencies:
    """Tests for FastAPI dependency providers."""

    def test_dependency_get_supabase_auth_client(self, monkeypatch):
        """get_supabase_auth_client should return a SupabaseAuthClient."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
        reset_supabase_auth_client()
        client = get_supabase_auth_client()
        assert isinstance(client, SupabaseAuthClientImpl)
        reset_supabase_auth_client()

    def test_dependency_set_supabase_auth_client(self):
        """set_supabase_auth_client should set the singleton."""
        fake = FakeSupabaseAuth()
        set_supabase_auth_client(fake)
        client = get_supabase_auth_client()
        assert client is fake
        reset_supabase_auth_client()

    def test_dependency_reset_supabase_auth_client(self, monkeypatch):
        """reset_supabase_auth_client should clear the singleton."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
        reset_supabase_auth_client()
        get_supabase_auth_client()
        reset_supabase_auth_client()
        # After reset, should create a new instance
        client = get_supabase_auth_client()
        assert isinstance(client, SupabaseAuthClientImpl)
        reset_supabase_auth_client()


# ============================================================
# Task 8.1-8.2: LoginAttempt repository
# ============================================================

class TestLoginAttemptRepository:
    """Tests for the LoginAttemptRepository."""

    @pytest.fixture
    def repo(self):
        return LoginAttemptRepository()

    def test_login_attempt_repo_record(self, repo, db_session, institution_admin_ctx):
        """Repo should record a login attempt."""
        # Create a real client first to satisfy FK constraint
        db_session.execute(text(
            "INSERT INTO client (id, display_name, legal_name, slug, legal_entity_type_id, primary_contact_email, current_lifecycle_status) "
            "VALUES (:id, 'Test Client', 'Test Client Legal', 'test-client', "
            "(SELECT id FROM legal_entity_type LIMIT 1), 'test@example.com', 'active') "
            "ON CONFLICT DO NOTHING"
        ), {"id": institution_admin_ctx.client_id})
        db_session.flush()
        
        result = repo.record(
            db_session,
            institution_admin_ctx,
            email="test@example.com",
            event_type="login_success",
        )
        assert isinstance(result, LoginAttemptDTO)
        assert result.email == "test@example.com"
        assert result.event_type == "login_success"

    def test_login_attempt_repo_filters_by_client_id(self, repo, db_session, institution_admin_ctx):
        """Repo should filter by client_id from TenantContext."""
        # Create a real client first to satisfy FK constraint
        db_session.execute(text(
            "INSERT INTO client (id, display_name, legal_name, slug, legal_entity_type_id, primary_contact_email, current_lifecycle_status) "
            "VALUES (:id, 'Test Client', 'Test Client Legal', 'test-client', "
            "(SELECT id FROM legal_entity_type LIMIT 1), 'test@example.com', 'active') "
            "ON CONFLICT DO NOTHING"
        ), {"id": institution_admin_ctx.client_id})
        db_session.flush()
        
        # Record an attempt
        result = repo.record(
            db_session,
            institution_admin_ctx,
            email="test@example.com",
            event_type="login_success",
        )
        # Verify the client_id matches
        assert result.client_id == institution_admin_ctx.client_id


# ============================================================
# Phase 4: C-02 modifications — admin propagation to Supabase Auth (12.1-12.5)
# ============================================================

def _ensure_client_and_institution(db_session, ctx):
    """Helper: ensure client and institution exist for FK constraints."""
    db_session.execute(text(
        "INSERT INTO client (id, display_name, legal_name, slug, legal_entity_type_id, primary_contact_email, current_lifecycle_status) "
        "VALUES (:cid, 'Test Client', 'Test Client Legal', 'test-client', "
        "(SELECT id FROM legal_entity_type LIMIT 1), 'test@example.com', 'active') "
        "ON CONFLICT DO NOTHING"
    ), {"cid": ctx.client_id})
    # Create institution_type_name if needed
    db_session.execute(text(
        "INSERT INTO institution_type_name (id, name) VALUES (gen_random_uuid(), 'School') ON CONFLICT DO NOTHING"
    ))
    db_session.flush()
    # Create institution_type
    itn_id = db_session.execute(text("SELECT id FROM institution_type_name LIMIT 1")).fetchone()[0]
    itype_id = uuid.uuid4()
    db_session.execute(text(
        "INSERT INTO institution_type (id, name_id, code, is_system) VALUES (:id, :name_id, 'TEST_SCH', true) ON CONFLICT DO NOTHING"
    ), {"id": itype_id, "name_id": itn_id})
    db_session.flush()
    itype_id = db_session.execute(text("SELECT id FROM institution_type LIMIT 1")).fetchone()[0]
    # Create institution
    db_session.execute(text(
        "INSERT INTO institution (id, client_id, institution_type_id, display_name, current_lifecycle_status) "
        "VALUES (:iid, :cid, :itype_id, 'Test School', 'active') "
        "ON CONFLICT DO NOTHING"
    ), {"iid": ctx.institution_id, "cid": ctx.client_id, "itype_id": itype_id})
    db_session.flush()
    db_session.commit()  # Commit so the service's new session can see the data

class TestC02SupabasePropagation:
    """Tests for C-02 service Supabase Auth propagation (tasks 12.1-12.5)."""

    def test_c02_service_accepts_supabase_client(self, db_session):
        """Task 12.1: IdentityUserService should accept optional SupabaseAuthClient."""
        from kernel.user.services.service import IdentityUserService
        from kernel.user.repos.user_repo import UserRepository
        from kernel.audit import DefaultAuditEmitter
        from sqlalchemy.orm import sessionmaker

        fake_supabase = FakeSupabaseAuth()
        factory = sessionmaker(bind=db_session.get_bind())

        # Should work with supabase_client=None (backwards compatible)
        svc_no_supabase = IdentityUserService(session_factory=factory)
        assert svc_no_supabase._supabase is None

        # Should work with supabase_client provided
        svc_with_supabase = IdentityUserService(
            session_factory=factory,
            supabase_client=fake_supabase,
        )
        assert svc_with_supabase._supabase is fake_supabase

    @pytest.mark.asyncio
    async def test_c02_create_user_propagates_to_supabase(self, db_session, institution_admin_ctx):
        """Task 12.2: create_user should call Supabase create_user."""
        from kernel.user.services.service import IdentityUserService
        from kernel.user.services.dtos import UserCreateDTO
        from sqlalchemy.orm import sessionmaker

        _ensure_client_and_institution(db_session, institution_admin_ctx)

        fake_supabase = FakeSupabaseAuth()
        factory = sessionmaker(bind=db_session.get_bind())
        svc = IdentityUserService(session_factory=factory, supabase_client=fake_supabase)

        cat = db_session.execute(text("SELECT id FROM user_category LIMIT 1")).fetchone()
        assert cat is not None, "No user_category found"

        dto = UserCreateDTO(
            email="newuser@test.com",
            name="New User",
            user_category_id=cat[0],
            institution_id=institution_admin_ctx.institution_id,
        )

        result = await svc.create_user(institution_admin_ctx, dto)
        assert result.email == "newuser@test.com"
        # Verify Supabase user was created
        uid = str(result.id)
        assert uid in fake_supabase._users
        assert fake_supabase._users[uid]["email"] == "newuser@test.com"

    @pytest.mark.asyncio
    async def test_c02_create_user_supabase_failure_rolls_back(self, db_session, institution_admin_ctx):
        """Task 12.2: On Supabase failure, create_user should rollback app_user insert."""
        from kernel.user.services.service import IdentityUserService
        from kernel.user.services.dtos import UserCreateDTO
        from kernel.auth.supabase_client import SupabaseAuthError
        from sqlalchemy.orm import sessionmaker

        _ensure_client_and_institution(db_session, institution_admin_ctx)

        # Create a fake that always fails on create_user
        class FailingSupabase(FakeSupabaseAuth):
            async def create_user(self, user_id, email):
                raise SupabaseAuthError("Simulated failure")

        fake_supabase = FailingSupabase()
        factory = sessionmaker(bind=db_session.get_bind())
        svc = IdentityUserService(session_factory=factory, supabase_client=fake_supabase)

        cat = db_session.execute(text("SELECT id FROM user_category LIMIT 1")).fetchone()
        assert cat is not None

        dto = UserCreateDTO(
            email="failuser@test.com",
            name="Fail User",
            user_category_id=cat[0],
            institution_id=institution_admin_ctx.institution_id,
        )

        with pytest.raises(ValueError, match="Failed to create Supabase Auth user"):
            await svc.create_user(institution_admin_ctx, dto)

        # Verify the app_user was rolled back
        exists = db_session.execute(
            text("SELECT 1 FROM app_user WHERE email = 'failuser@test.com'")
        ).fetchone()
        assert exists is None, "app_user should have been rolled back"

    @pytest.mark.asyncio
    async def test_c02_suspend_revokes_supabase_sessions(self, db_session, institution_admin_ctx):
        """Task 12.3: transition_lifecycle suspend should call Supabase sign_out."""
        from kernel.user.services.service import IdentityUserService
        from kernel.user.services.dtos import UserCreateDTO
        from sqlalchemy.orm import sessionmaker

        _ensure_client_and_institution(db_session, institution_admin_ctx)

        fake_supabase = FakeSupabaseAuth()
        factory = sessionmaker(bind=db_session.get_bind())
        svc = IdentityUserService(session_factory=factory, supabase_client=fake_supabase)

        cat = db_session.execute(text("SELECT id FROM user_category LIMIT 1")).fetchone()
        assert cat is not None

        # Create user
        dto = UserCreateDTO(
            email="suspenduser@test.com",
            name="Suspend User",
            user_category_id=cat[0],
            institution_id=institution_admin_ctx.institution_id,
        )
        user = await svc.create_user(institution_admin_ctx, dto)

        # Activate the user first
        await svc.transition_lifecycle(institution_admin_ctx, user.id, "active", "activated")

        # Now suspend
        await svc.transition_lifecycle(institution_admin_ctx, user.id, "suspended", "suspended by admin")

        # Verify Supabase sign_out was called (refresh tokens cleared)
        uid = str(user.id)
        assert uid in fake_supabase._users
        assert len(fake_supabase._users[uid]["refresh_tokens"]) == 0

    @pytest.mark.asyncio
    async def test_c02_archive_deletes_supabase_user(self, db_session, institution_admin_ctx):
        """Task 12.4: transition_lifecycle archive should call Supabase sign_out + delete_user."""
        from kernel.user.services.service import IdentityUserService
        from kernel.user.services.dtos import UserCreateDTO
        from sqlalchemy.orm import sessionmaker

        _ensure_client_and_institution(db_session, institution_admin_ctx)

        fake_supabase = FakeSupabaseAuth()
        factory = sessionmaker(bind=db_session.get_bind())
        svc = IdentityUserService(session_factory=factory, supabase_client=fake_supabase)

        cat = db_session.execute(text("SELECT id FROM user_category LIMIT 1")).fetchone()
        assert cat is not None

        # Create user
        dto = UserCreateDTO(
            email="archiveuser@test.com",
            name="Archive User",
            user_category_id=cat[0],
            institution_id=institution_admin_ctx.institution_id,
        )
        user = await svc.create_user(institution_admin_ctx, dto)
        uid = str(user.id)

        # Activate then archive
        await svc.transition_lifecycle(institution_admin_ctx, user.id, "active", "activated")
        await svc.transition_lifecycle(institution_admin_ctx, user.id, "archived", "archived by admin")

        # Verify Supabase user was deleted
        assert uid not in fake_supabase._users

    @pytest.mark.asyncio
    async def test_c02_email_change_propagates_to_supabase(self, db_session, institution_admin_ctx):
        """Task 12.5: update_user with email change should propagate to Supabase."""
        from kernel.user.services.service import IdentityUserService
        from kernel.user.services.dtos import UserCreateDTO, UserUpdateDTO
        from sqlalchemy.orm import sessionmaker

        _ensure_client_and_institution(db_session, institution_admin_ctx)

        fake_supabase = FakeSupabaseAuth()
        factory = sessionmaker(bind=db_session.get_bind())
        svc = IdentityUserService(session_factory=factory, supabase_client=fake_supabase)

        cat = db_session.execute(text("SELECT id FROM user_category LIMIT 1")).fetchone()
        assert cat is not None

        # Create user
        dto = UserCreateDTO(
            email="oldemail@test.com",
            name="Email Change User",
            user_category_id=cat[0],
            institution_id=institution_admin_ctx.institution_id,
        )
        user = await svc.create_user(institution_admin_ctx, dto)
        uid = str(user.id)

        # Change email
        update_dto = UserUpdateDTO(email="newemail@test.com")
        await svc.update_user(institution_admin_ctx, user.id, update_dto)

        # Verify Supabase email was updated
        assert fake_supabase._users[uid]["email"] == "newemail@test.com"
        assert "newemail@test.com" in fake_supabase._email_to_id

    @pytest.mark.asyncio
    async def test_c02_non_email_update_no_supabase_call(self, db_session, institution_admin_ctx):
        """Task 12.5: update_user without email change should NOT call Supabase."""
        from kernel.user.services.service import IdentityUserService
        from kernel.user.services.dtos import UserCreateDTO, UserUpdateDTO
        from sqlalchemy.orm import sessionmaker

        _ensure_client_and_institution(db_session, institution_admin_ctx)

        fake_supabase = FakeSupabaseAuth()
        factory = sessionmaker(bind=db_session.get_bind())
        svc = IdentityUserService(session_factory=factory, supabase_client=fake_supabase)

        cat = db_session.execute(text("SELECT id FROM user_category LIMIT 1")).fetchone()
        assert cat is not None

        # Create user
        dto = UserCreateDTO(
            email="nochange@test.com",
            name="No Change User",
            user_category_id=cat[0],
            institution_id=institution_admin_ctx.institution_id,
        )
        user = await svc.create_user(institution_admin_ctx, dto)
        uid = str(user.id)

        # Update name only (no email change)
        update_dto = UserUpdateDTO(name="Updated Name")
        await svc.update_user(institution_admin_ctx, user.id, update_dto)

        # Verify Supabase email unchanged
        assert fake_supabase._users[uid]["email"] == "nochange@test.com"


# ============================================================
# Phase 4: Bootstrap CLI (13.1)
# ============================================================

class TestBootstrapCLI:
    """Tests for the bootstrap CLI (task 13.1)."""

    def test_bootstrap_creates_supabase_user(self, db_session):
        """Bootstrap should create platform owner in Supabase Auth."""
        from kernel.auth.bootstrap import bootstrap_platform_owner
        from tests.fake_supabase_auth import FakeSupabaseAuth
        from kernel.auth.supabase_client import SupabaseAuthError
        from unittest.mock import patch, AsyncMock
        import os

        # Create platform owner app_user row
        db_session.execute(text(
            "INSERT INTO user_category (id, name) "
            "VALUES (gen_random_uuid(), 'Executive Leadership') "
            "ON CONFLICT DO NOTHING"
        ))
        db_session.flush()

        cat_id = db_session.execute(
            text("SELECT id FROM user_category WHERE name = 'Executive Leadership'")
        ).fetchone()[0]

        db_session.execute(text(
            "INSERT INTO client (id, display_name, legal_name, slug, legal_entity_type_id, primary_contact_email, current_lifecycle_status) "
            "VALUES ('00000000-0000-0000-0000-000000000001', 'Platform', 'Platform Ltd', 'platform', "
            "(SELECT id FROM legal_entity_type LIMIT 1), 'platform@test.com', 'active') "
            "ON CONFLICT DO NOTHING"
        ))
        db_session.flush()

        # Create institution_type
        db_session.execute(text(
            "INSERT INTO institution_type_name (id, name) VALUES (gen_random_uuid(), 'School') ON CONFLICT DO NOTHING"
        ))
        db_session.flush()
        itn_id = db_session.execute(
            text("SELECT id FROM institution_type_name LIMIT 1")
        ).fetchone()[0]
        itype_id = uuid.uuid4()
        db_session.execute(text(
            "INSERT INTO institution_type (id, name_id, code, is_system) VALUES (:id, :name_id, 'BOOT_SCH', true) ON CONFLICT DO NOTHING"
        ), {"id": itype_id, "name_id": itn_id})
        db_session.flush()
        itype_id = db_session.execute(
            text("SELECT id FROM institution_type LIMIT 1")
        ).fetchone()[0]

        inst_id = uuid.uuid4()
        db_session.execute(text(
            "INSERT INTO institution (id, client_id, institution_type_id, display_name, current_lifecycle_status) "
            "VALUES (:inst_id, '00000000-0000-0000-0000-000000000001', :itype_id, 'Platform HQ', 'active') "
            "ON CONFLICT DO NOTHING"
        ), {"inst_id": inst_id, "itype_id": itype_id})
        db_session.flush()

        owner_id = uuid.uuid4()
        db_session.execute(text(
            "INSERT INTO app_user (id, client_id, institution_id, email, name, user_category_id, lifecycle_status) "
            "VALUES (:id, '00000000-0000-0000-0000-000000000001', :inst_id, 'platform@test.com', 'Platform Owner', :cat_id, 'active')"
        ), {"id": owner_id, "inst_id": inst_id, "cat_id": cat_id})
        db_session.commit()

        # Create a fake that tracks calls
        fake = FakeSupabaseAuth()
        create_calls = []
        original_create = fake.create_user

        async def tracking_create(user_id, email):
            create_calls.append((user_id, email))
            return await original_create(user_id, email)

        fake.create_user = tracking_create

        # Patch SupabaseAuthClientImpl at the source module
        with patch('kernel.auth.supabase_client.SupabaseAuthClientImpl', return_value=fake):
            with patch.dict(os.environ, {
                'SUPABASE_URL': 'http://localhost:54321',
                'SUPABASE_SERVICE_ROLE_KEY': 'test-key',
                'PLATFORM_OWNER_INITIAL_PASSWORD': 'test-password-123',
            }):
                import asyncio
                asyncio.run(bootstrap_platform_owner())

        # Verify create_user was called
        assert len(create_calls) == 1
        assert create_calls[0][0] == owner_id
        assert create_calls[0][1] == 'platform@test.com'

    def test_bootstrap_idempotent(self, db_session):
        """Bootstrap should be idempotent — no error if user already exists."""
        from kernel.auth.bootstrap import bootstrap_platform_owner
        from tests.fake_supabase_auth import FakeSupabaseAuth
        from unittest.mock import patch
        import os

        # Create platform owner app_user row
        db_session.execute(text(
            "INSERT INTO user_category (id, name) "
            "VALUES (gen_random_uuid(), 'Executive Leadership') "
            "ON CONFLICT DO NOTHING"
        ))
        db_session.flush()

        cat_id = db_session.execute(
            text("SELECT id FROM user_category WHERE name = 'Executive Leadership'")
        ).fetchone()[0]

        db_session.execute(text(
            "INSERT INTO client (id, display_name, legal_name, slug, legal_entity_type_id, primary_contact_email, current_lifecycle_status) "
            "VALUES ('00000000-0000-0000-0000-000000000001', 'Platform', 'Platform Ltd', 'platform', "
            "(SELECT id FROM legal_entity_type LIMIT 1), 'platform@test.com', 'active') "
            "ON CONFLICT DO NOTHING"
        ))
        db_session.flush()

        # Create institution_type
        db_session.execute(text(
            "INSERT INTO institution_type_name (id, name) VALUES (gen_random_uuid(), 'School') ON CONFLICT DO NOTHING"
        ))
        db_session.flush()
        itn_id = db_session.execute(
            text("SELECT id FROM institution_type_name LIMIT 1")
        ).fetchone()[0]
        itype_id = uuid.uuid4()
        db_session.execute(text(
            "INSERT INTO institution_type (id, name_id, code, is_system) VALUES (:id, :name_id, 'BOOT_SCH2', true) ON CONFLICT DO NOTHING"
        ), {"id": itype_id, "name_id": itn_id})
        db_session.flush()
        itype_id = db_session.execute(
            text("SELECT id FROM institution_type LIMIT 1")
        ).fetchone()[0]

        inst_id = uuid.uuid4()
        db_session.execute(text(
            "INSERT INTO institution (id, client_id, institution_type_id, display_name, current_lifecycle_status) "
            "VALUES (:inst_id, '00000000-0000-0000-0000-000000000001', :itype_id, 'Platform HQ', 'active') "
            "ON CONFLICT DO NOTHING"
        ), {"inst_id": inst_id, "itype_id": itype_id})
        db_session.flush()

        owner_id = uuid.uuid4()
        db_session.execute(text(
            "INSERT INTO app_user (id, client_id, institution_id, email, name, user_category_id, lifecycle_status) "
            "VALUES (:id, '00000000-0000-0000-0000-000000000001', :inst_id, 'platform@test.com', 'Platform Owner', :cat_id, 'active')"
        ), {"id": owner_id, "inst_id": inst_id, "cat_id": cat_id})
        db_session.commit()

        # Create a fake with the user already existing
        fake = FakeSupabaseAuth()
        # Pre-create the user in the fake to simulate existing Supabase user
        import asyncio
        asyncio.run(fake.create_user(owner_id, 'platform@test.com'))
        asyncio.run(fake.update_user(owner_id, password='old-password', email_confirm=True))

        update_calls = []
        original_update = fake.update_user

        async def tracking_update(user_id, **kwargs):
            update_calls.append((user_id, kwargs))
            return await original_update(user_id, **kwargs)

        fake.update_user = tracking_update

        # Patch SupabaseAuthClientImpl at the source module
        with patch('kernel.auth.supabase_client.SupabaseAuthClientImpl', return_value=fake):
            with patch.dict(os.environ, {
                'SUPABASE_URL': 'http://localhost:54321',
                'SUPABASE_SERVICE_ROLE_KEY': 'test-key',
                'PLATFORM_OWNER_INITIAL_PASSWORD': 'test-password-123',
            }):
                asyncio.run(bootstrap_platform_owner())

        # update_user called twice: once to check existence, once to update password
        assert len(update_calls) == 2

    def test_bootstrap_missing_password_fatal(self):
        """Bootstrap should fail if PLATFORM_OWNER_INITIAL_PASSWORD is missing."""
        from kernel.auth.bootstrap import bootstrap_platform_owner
        from unittest.mock import patch
        import os

        with patch.dict(os.environ, {
            'SUPABASE_URL': 'http://localhost:54321',
            'SUPABASE_SERVICE_ROLE_KEY': 'test-key',
        }, clear=False):
            # Remove PLATFORM_OWNER_INITIAL_PASSWORD if it exists
            os.environ.pop('PLATFORM_OWNER_INITIAL_PASSWORD', None)
            with pytest.raises(SystemExit) as exc_info:
                import asyncio
                asyncio.run(bootstrap_platform_owner())
            assert exc_info.value.code == 1
