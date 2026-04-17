from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config.database import get_db
from ..controllers import userController
from ..validators.userSchemas import CreateUserRequest, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=201)
def create_user(payload: CreateUserRequest, db: Session = Depends(get_db)) -> UserResponse:
    return userController.create_user(db, payload)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)) -> UserResponse:
    return userController.get_user(db, user_id)


@router.get("", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db)) -> list[UserResponse]:
    return userController.list_users(db)
