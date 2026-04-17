from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models.userModel import User
from ..validators.userSchemas import CreateUserRequest, UserResponse


def create_user(db: Session, payload: CreateUserRequest) -> UserResponse:
    existing_email = db.query(User).filter(User.email == payload.email).first()
    if existing_email:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already exists")

    if payload.id is not None:
        existing_id = db.query(User).filter(User.id == payload.id).first()
        if existing_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="user id already exists",
            )

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        phone=payload.phone,
    )
    if payload.id is not None:
        user.id = payload.id

    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


def get_user(db: Session, user_id: int) -> UserResponse:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    return UserResponse.model_validate(user)


def list_users(db: Session) -> list[UserResponse]:
    users = db.query(User).order_by(User.id).all()
    return [UserResponse.model_validate(u) for u in users]
