from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth.auth import authenticate_user, create_user, get_user_by_email
from auth.dependencies import get_current_admin, get_current_user
from auth.jwt_handler import JWT_ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token
from auth.roles import ROLE_ADMIN
from database import get_db
from models.user import User
from schemas.user import TokenResponse, UserLogin, UserRegister, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


def success_response(message: str, data: dict | None = None) -> dict:
    return {"success": True, "message": message, "data": data or {}}


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(payload: UserRegister, db: Session = Depends(get_db)):
    if get_user_by_email(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    if payload.role == ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin accounts must be created by an existing admin.",
        )

    user = create_user(
        db,
        full_name=payload.full_name,
        email=str(payload.email),
        password=payload.password,
        role=payload.role,
    )
    return success_response(
        "User registered successfully",
        {"user": UserResponse.model_validate(user).model_dump(mode="json")},
    )


@router.post("/login")
def login_user(payload: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, str(payload.email), payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    token = create_access_token(
        subject=user.email,
        claims={"role": user.role, "user_id": user.id},
    )
    token_payload = TokenResponse(
        access_token=token,
        expires_in_minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
        user=UserResponse.model_validate(user),
    )
    return success_response("Login successful", token_payload.model_dump(mode="json"))


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return success_response(
        "Authenticated user retrieved successfully",
        {"user": UserResponse.model_validate(current_user).model_dump(mode="json")},
    )


@router.post("/logout")
def logout_user(current_user: User = Depends(get_current_user)):
    return success_response(
        "Logout successful. Please remove the token on the client.",
        {"email": current_user.email},
    )


@router.get("/admin/check")
def admin_check(current_user: User = Depends(get_current_admin)):
    return success_response(
        "Admin access verified",
        {"email": current_user.email, "role": current_user.role},
    )
