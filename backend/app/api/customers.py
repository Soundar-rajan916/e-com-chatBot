from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Customer
from app.schemas import DemoCustomerResponse

router = APIRouter()


@router.get("/customers/demo", response_model=list[DemoCustomerResponse])
async def get_demo_customers(
    session: AsyncSession = Depends(get_session),
) -> list[DemoCustomerResponse]:
    """
    Returns seeded demo customers for local development and testing.
    Only active when APP_ENV == 'dev'.
    """
    stmt = select(Customer).order_by(Customer.created_at.asc())
    result = await session.execute(stmt)
    customers = list(result.scalars().all())
    return [DemoCustomerResponse.model_validate(c) for c in customers]
