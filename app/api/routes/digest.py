from fastapi import APIRouter, Depends
from app.models.user import User
from app.api.deps import get_verified_user

router = APIRouter()


@router.get("/latest")
async def get_latest_digest(user: User = Depends(get_verified_user)):
    """
    TODO: Connect to your existing bot digest logic here.
    Return the latest digest for the current user based on their topics/plan.
    """
    return {
        "user": user.email,
        "plan": user.plan,
        "digest": "Connect your bot digest logic here",
    }


@router.get("/history")
async def get_digest_history(user: User = Depends(get_verified_user)):
    """Return digest history. Free plan: 7 days. Pro: unlimited."""
    days = 7 if user.plan == "free" else 365
    return {"days_available": days, "digests": []}
