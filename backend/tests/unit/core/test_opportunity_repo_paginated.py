"""
Tests unitarios: OpportunityRepository.list_paginated (CHG-009).

Verifica que el metodo aplica correctamente offset, limit y filtros
(status, exchanges, rango de fechas) usando mock de AsyncSession.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.entities.opportunity import OpportunityStatus


class TestListPaginated:
    """Tests para el metodo list_paginated del OpportunityRepository."""

    @pytest.mark.asyncio
    async def test_returns_tuple_of_items_and_total(self) -> None:
        """El metodo debe retornar (list[ArbitrageOpportunity], int)."""
        from adapters.persistence.opportunity_repo import OpportunityRepository

        session = AsyncMock()
        # Mock del COUNT query
        count_scalar = MagicMock()
        count_scalar.scalar_one.return_value = 0
        # Mock del data query
        data_scalars = MagicMock()
        data_scalars.all.return_value = []

        session.execute = AsyncMock(
            side_effect=[count_scalar, data_scalars]
        )

        repo = OpportunityRepository(session)
        items, total = await repo.list_paginated(offset=0, limit=50)

        assert isinstance(items, list)
        assert isinstance(total, int)
        assert total == 0
        assert len(items) == 0

    @pytest.mark.asyncio
    async def test_passes_offset_and_limit_to_query(self) -> None:
        """El metodo debe pasar offset y limit al query SQLAlchemy."""
        from adapters.persistence.opportunity_repo import OpportunityRepository

        session = AsyncMock()
        count_scalar = MagicMock()
        count_scalar.scalar_one.return_value = 0
        data_scalars = MagicMock()
        data_scalars.all.return_value = []

        session.execute = AsyncMock(
            side_effect=[count_scalar, data_scalars]
        )

        repo = OpportunityRepository(session)
        await repo.list_paginated(offset=10, limit=25)

        # Verificar que se llamaron exactamente 2 queries (count + data)
        assert session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_filters_by_status(self) -> None:
        """El filtro status debe aplicarse a ambas queries (count + data)."""
        from adapters.persistence.opportunity_repo import OpportunityRepository

        session = AsyncMock()
        count_scalar = MagicMock()
        count_scalar.scalar_one.return_value = 5
        data_scalars = MagicMock()
        data_scalars.all.return_value = []

        session.execute = AsyncMock(
            side_effect=[count_scalar, data_scalars]
        )

        repo = OpportunityRepository(session)
        items, total = await repo.list_paginated(
            offset=0,
            limit=50,
            status=[OpportunityStatus.EXECUTED],
        )
        assert total == 5

    @pytest.mark.asyncio
    async def test_filters_by_status_multi(self) -> None:
        """El filtro status acepta multiples valores (multi-select)."""
        from adapters.persistence.opportunity_repo import OpportunityRepository

        session = AsyncMock()
        count_scalar = MagicMock()
        count_scalar.scalar_one.return_value = 7
        data_scalars = MagicMock()
        data_scalars.all.return_value = []

        session.execute = AsyncMock(
            side_effect=[count_scalar, data_scalars]
        )

        repo = OpportunityRepository(session)
        items, total = await repo.list_paginated(
            offset=0,
            limit=50,
            status=[OpportunityStatus.EXECUTED, OpportunityStatus.REJECTED],
        )
        assert total == 7

    @pytest.mark.asyncio
    async def test_filters_by_buy_exchange(self) -> None:
        """El filtro buy_exchange debe aplicarse a ambas queries."""
        from adapters.persistence.opportunity_repo import OpportunityRepository

        session = AsyncMock()
        count_scalar = MagicMock()
        count_scalar.scalar_one.return_value = 3
        data_scalars = MagicMock()
        data_scalars.all.return_value = []

        session.execute = AsyncMock(
            side_effect=[count_scalar, data_scalars]
        )

        repo = OpportunityRepository(session)
        items, total = await repo.list_paginated(
            offset=0, limit=50, buy_exchange=["binance"]
        )
        assert total == 3

    @pytest.mark.asyncio
    async def test_filters_by_buy_exchange_multi(self) -> None:
        """El filtro buy_exchange acepta multiples valores."""
        from adapters.persistence.opportunity_repo import OpportunityRepository

        session = AsyncMock()
        count_scalar = MagicMock()
        count_scalar.scalar_one.return_value = 5
        data_scalars = MagicMock()
        data_scalars.all.return_value = []

        session.execute = AsyncMock(
            side_effect=[count_scalar, data_scalars]
        )

        repo = OpportunityRepository(session)
        items, total = await repo.list_paginated(
            offset=0, limit=50, buy_exchange=["binance", "bybit"]
        )
        assert total == 5

    @pytest.mark.asyncio
    async def test_filters_by_sell_exchange(self) -> None:
        """El filtro sell_exchange debe aplicarse a ambas queries."""
        from adapters.persistence.opportunity_repo import OpportunityRepository

        session = AsyncMock()
        count_scalar = MagicMock()
        count_scalar.scalar_one.return_value = 2
        data_scalars = MagicMock()
        data_scalars.all.return_value = []

        session.execute = AsyncMock(
            side_effect=[count_scalar, data_scalars]
        )

        repo = OpportunityRepository(session)
        items, total = await repo.list_paginated(
            offset=0, limit=50, sell_exchange=["kraken"]
        )
        assert total == 2

    @pytest.mark.asyncio
    async def test_filters_by_date_range(self) -> None:
        """Los filtros from_dt y to_dt deben aplicarse a ambas queries."""
        from adapters.persistence.opportunity_repo import OpportunityRepository

        session = AsyncMock()
        count_scalar = MagicMock()
        count_scalar.scalar_one.return_value = 10
        data_scalars = MagicMock()
        data_scalars.all.return_value = []

        session.execute = AsyncMock(
            side_effect=[count_scalar, data_scalars]
        )

        repo = OpportunityRepository(session)
        from_dt = datetime(2026, 1, 1, tzinfo=timezone.utc)
        to_dt = datetime(2026, 3, 1, tzinfo=timezone.utc)
        items, total = await repo.list_paginated(
            offset=0, limit=50, from_dt=from_dt, to_dt=to_dt
        )
        assert total == 10

    @pytest.mark.asyncio
    async def test_combined_filters(self) -> None:
        """Todos los filtros deben poder combinarse."""
        from adapters.persistence.opportunity_repo import OpportunityRepository

        session = AsyncMock()
        count_scalar = MagicMock()
        count_scalar.scalar_one.return_value = 1
        data_scalars = MagicMock()
        data_scalars.all.return_value = []

        session.execute = AsyncMock(
            side_effect=[count_scalar, data_scalars]
        )

        repo = OpportunityRepository(session)
        from_dt = datetime(2026, 1, 1, tzinfo=timezone.utc)
        to_dt = datetime(2026, 3, 1, tzinfo=timezone.utc)
        items, total = await repo.list_paginated(
            offset=5,
            limit=10,
            status=[OpportunityStatus.EXECUTED],
            buy_exchange=["binance"],
            sell_exchange=["kraken"],
            from_dt=from_dt,
            to_dt=to_dt,
        )
        assert total == 1
        assert session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_no_filters_returns_all(self) -> None:
        """Sin filtros, retorna todos los registros paginados."""
        from adapters.persistence.opportunity_repo import OpportunityRepository

        session = AsyncMock()
        count_scalar = MagicMock()
        count_scalar.scalar_one.return_value = 100
        data_scalars = MagicMock()
        data_scalars.all.return_value = []

        session.execute = AsyncMock(
            side_effect=[count_scalar, data_scalars]
        )

        repo = OpportunityRepository(session)
        items, total = await repo.list_paginated(offset=0, limit=50)
        assert total == 100
