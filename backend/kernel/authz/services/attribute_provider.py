"""C-04 Authorization — attribute provider contract + registry (D3, D4, D5, D10).

Defines the Kernel-owned abstract contract that business modules implement,
plus the ``ProviderRegistry`` that maps required attributes to providers and
resolves them with request-scoped caching and fail-closed semantics.

Also ships the built-in ``IsSelfAttributeProvider`` (D10) — a Kernel-owned
provider that resolves ``is_self`` from ``ResourceContext.data["owner_id"]``.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from kernel.authz.models.authorization_types import (
    AuthorizationAttributes,
    AuthorizationRequest,
)

logger = logging.getLogger(__name__)


class AuthorizationAttributeProvider(ABC):
    """Kernel-owned abstract contract for domain attribute providers (D3, REQ-AUTHZ-ABAC-02).

    Business modules implement this interface. Providers:
    - Expose an async ``resolve()`` that returns only facts (attribute values).
    - Never make the final authorization decision — Casbin remains the sole decision-maker.
    - Are stateless with injected dependencies (no request-scoped state on the instance).
    - Register at application startup via the ``ProviderRegistry``.
    """

    name: str
    """Stable provider identifier (e.g. 'teacher.assignments')."""

    resource_types: frozenset[str]
    """Resource types this provider can resolve attributes for. ``"*"`` = any."""

    attributes: frozenset[str]
    """Attribute names this provider can resolve (e.g. ``{"is_subject_teacher"}``)."""

    @abstractmethod
    async def resolve(self, request: AuthorizationRequest) -> dict[str, Any]:
        """Return ONLY the facts this provider owns. Never an allow/deny decision.

        Args:
            request: The full authorization request (subject + resource + action).

        Returns:
            A dict of attribute name → value. May be a subset of ``self.attributes``
            if some attributes don't apply to the specific request.
        """


class ProviderRegistry:
    """Registry mapping (resource_type, attribute) → provider (D4, REQ-AUTHZ-ABAC-02).

    - Registration is idempotent per provider instance.
    - Duplicate ``(resource_type, attribute)`` claims raise at startup (fail-fast).
    - Deterministic execution order: registration order, then ``provider.name``.
    - Providers are held for the app lifetime and remain stateless.
    """

    def __init__(self) -> None:
        # (resource_type, attribute_name) → provider
        self._providers: dict[tuple[str, str], AuthorizationAttributeProvider] = {}
        # provider_name → provider (for dedup)
        self._registered_names: set[str] = set()

    def register(self, provider: AuthorizationAttributeProvider) -> None:
        """Register a provider. Rejects duplicate (resource_type, attribute) claims.

        Args:
            provider: The provider to register.

        Raises:
            ValueError: If a provider already claims a (resource_type, attribute) pair.
        """
        if provider.name in self._registered_names:
            # Idempotent: same provider name, skip re-registration
            return

        for rt in provider.resource_types:
            for attr in provider.attributes:
                key = (rt, attr)
                if key in self._providers:
                    existing = self._providers[key]
                    raise ValueError(
                        f"Duplicate attribute claim: ({rt!r}, {attr!r}) already "
                        f"registered by provider {existing.name!r}; "
                        f"cannot register {provider.name!r}"
                    )
                self._providers[key] = provider

        self._registered_names.add(provider.name)
        logger.debug("Registered attribute provider %r for resources=%s attrs=%s",
                      provider.name, provider.resource_types, provider.attributes)

    def providers_for(
        self, resource_type: str, attribute: str
    ) -> AuthorizationAttributeProvider | None:
        """Return the provider for (resource_type, attribute), or None.

        Checks exact resource_type first, then wildcard ``"*"``.
        """
        return self._providers.get(
            (resource_type, attribute)
        ) or self._providers.get(("*", attribute))

    async def resolve_attributes(
        self,
        request: AuthorizationRequest,
        required: set[str],
    ) -> AuthorizationAttributes:
        """Resolve required attributes with request-scoped caching + fail-closed (D5).

        - For each required attribute, resolve via the registered provider.
        - Cache resolved values for the lifetime of this call (request-scoped).
        - If an attribute has no registered provider, or a provider raises,
          record it in ``unresolved`` (fail-closed).
        - When ``required`` is empty, return an empty ``AuthorizationAttributes``
          without invoking any provider (pure-RBAC fallback).

        Args:
            request: The authorization request.
            required: Set of required attribute names.

        Returns:
            Populated ``AuthorizationAttributes`` with values, provenance, and
            any unresolved attributes.
        """
        attrs = AuthorizationAttributes()

        if not required:
            return attrs

        # Request-scoped cache: (resource_type, attribute) → resolved value
        cache: dict[tuple[str, str], Any] = {}

        for attr_name in sorted(required):  # sorted for determinism
            rt = request.resource.resource_type
            cache_key = (rt, attr_name)

            if cache_key in cache:
                # Cache hit within this request
                attrs.values[attr_name] = cache[cache_key]
                continue

            provider = self.providers_for(rt, attr_name)
            if provider is None:
                logger.warning(
                    "[AUTHZ] No provider registered for attribute %r on resource_type %r — fail-closed",
                    attr_name, rt,
                )
                attrs.unresolved.add(attr_name)
                continue

            try:
                result = await provider.resolve(request)
                if attr_name in result:
                    value = result[attr_name]
                    cache[cache_key] = value
                    attrs.values[attr_name] = value
                    attrs.resolved_by[attr_name] = provider.name
                else:
                    # Provider didn't return the requested attribute
                    logger.warning(
                        "[AUTHZ] Provider %r did not return attribute %r — fail-closed",
                        provider.name, attr_name,
                    )
                    attrs.unresolved.add(attr_name)
            except Exception:
                logger.exception(
                    "[AUTHZ] Provider %r raised while resolving %r — fail-closed",
                    provider.name, attr_name,
                )
                attrs.unresolved.add(attr_name)

        return attrs


class IsSelfAttributeProvider(AuthorizationAttributeProvider):
    """Built-in Kernel-owned provider that resolves ``is_self`` (D10, REQ-AUTHZ-ABAC-05).

    Evaluates whether the authenticated user is the owner of the resource by
    comparing ``request.subject.user_id`` with ``ResourceContext.data["owner_id"]``
    or ``ResourceContext.data["user_id"]``.

    This replaces the hardcoded ``owner_id`` self-access bypass in ``_check_impl()``
    with a first-class ABAC attribute evaluated by Casbin.
    """

    name = "authz.is_self"
    resource_types = frozenset({"*"})
    attributes = frozenset({"is_self"})

    async def resolve(self, request: AuthorizationRequest) -> dict[str, Any]:
        owner_id = (
            request.resource.data.get("owner_id")
            or request.resource.data.get("user_id")
        )
        subject_id = request.subject.user_id
        return {
            "is_self": bool(
                owner_id and subject_id and str(subject_id) == str(owner_id)
            )
        }
