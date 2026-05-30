from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.auth.dependencies import get_current_customer
from app.database.session import get_db
from app.models.customer import Customer
from app.schemas.user import UserProfileResponse, UserProfileUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/profile", response_model=UserProfileResponse)
def get_profile(
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    try:
        profile = UserService(db).get_profile(customer.id)
        return UserProfileResponse.from_customer(profile)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/profile", response_model=UserProfileResponse)
def update_profile(
    data: UserProfileUpdate,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    try:
        profile = UserService(db).update_profile(customer.id, data)
        return UserProfileResponse.from_customer(profile)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/profile", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> None:
    try:
        UserService(db).delete_account(customer.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
