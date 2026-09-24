from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List


async def calculate_monthly_revenue(
    property_id: str,
    tenant_id: str,
    month: int,
    year: int,
    db_session=None
) -> Decimal:
    """
    Calculates revenue for a specific month.
    """

    start_date = datetime(year, month, 1)

    if month < 12:
        end_date = datetime(year, month + 1, 1)
    else:
        end_date = datetime(year + 1, 1, 1)

    print(
        f"DEBUG: Querying revenue for {property_id} "
        f"from {start_date} to {end_date}"
    )

    from sqlalchemy import text

    query = text("""
        SELECT COALESCE(SUM(ROUND(r.total_amount, 2)), 0) as total
        FROM reservations r
        JOIN properties p
          ON p.id = r.property_id
         AND p.tenant_id = r.tenant_id
        WHERE r.property_id = :property_id
          AND r.tenant_id = :tenant_id
          AND (r.check_in_date AT TIME ZONE p.timezone) >= :start_date
          AND (r.check_in_date AT TIME ZONE p.timezone) < :end_date
    """)

    result = await db_session.execute(
        query,
        {
            "property_id": property_id,
            "tenant_id": tenant_id,
            "start_date": start_date,
            "end_date": end_date
        }
    )

    total = result.scalar()

    return Decimal(str(total or 0))


async def calculate_total_revenue(
    property_id: str,
    tenant_id: str
) -> Dict[str, Any]:
    """
    Aggregates revenue from database.
    """

    try:
        # Import database pool
        from app.core.database_pool import DatabasePool

        # Initialize pool if needed
        db_pool = DatabasePool()
        await db_pool.initialize()

        if db_pool.session_factory:
            session = await db_pool.get_session()

            async with session:
                from sqlalchemy import text

                total_revenue = await calculate_monthly_revenue(
                    property_id,
                    tenant_id,
                    3,
                    2024,
                    session
                )

                start_date = datetime(2024, 3, 1)
                end_date = datetime(2024, 4, 1)

                count_query = text("""
                    SELECT COUNT(*) as reservation_count
                    FROM reservations r
                    JOIN properties p
                      ON p.id = r.property_id
                     AND p.tenant_id = r.tenant_id
                    WHERE r.property_id = :property_id
                      AND r.tenant_id = :tenant_id
                      AND (r.check_in_date AT TIME ZONE p.timezone) >= :start_date
                      AND (r.check_in_date AT TIME ZONE p.timezone) < :end_date
                """)

                count_result = await session.execute(
                    count_query,
                    {
                        "property_id": property_id,
                        "tenant_id": tenant_id,
                        "start_date": start_date,
                        "end_date": end_date
                    }
                )

                reservation_count = count_result.scalar() or 0

                return {
                    "property_id": property_id,
                    "tenant_id": tenant_id,
                    "total": str(total_revenue),
                    "currency": "USD",
                    "count": reservation_count
                }

        else:
            raise Exception("Database pool not available")

    except Exception as e:
        print(
            f"Database error for {property_id} "
            f"(tenant: {tenant_id}): {e}"
        )
        raise