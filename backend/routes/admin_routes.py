from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from auth.dependencies import get_current_admin
from database import get_db
from models.user import User
from schemas.admin import AdminUserResponse, UserRoleUpdate, UserStatusUpdate
from schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
)
from services.admin_service import (
    create_knowledge_base_entry,
    delete_knowledge_base_entry,
    delete_user,
    list_knowledge_base,
    list_users,
    update_knowledge_base_entry,
    update_user_role,
    update_user_status,
)
from services.chat_service import api_success

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/knowledge-base")
def get_knowledge_base(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    entries = list_knowledge_base(db)
    return api_success(
        "Knowledge base entries retrieved successfully",
        {
            "entries": [
                KnowledgeBaseResponse.model_validate(entry).model_dump(mode="json")
                for entry in entries
            ]
        },
    )


@router.post("/knowledge-base", status_code=status.HTTP_201_CREATED)
def create_kb_entry(
    payload: KnowledgeBaseCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    entry = create_knowledge_base_entry(db, admin, payload)
    return api_success(
        "Knowledge base entry created successfully",
        {"entry": KnowledgeBaseResponse.model_validate(entry).model_dump(mode="json")},
    )


@router.put("/knowledge-base/{entry_id}")
def update_kb_entry(
    entry_id: int,
    payload: KnowledgeBaseUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    entry = update_knowledge_base_entry(db, admin, entry_id, payload)
    return api_success(
        "Knowledge base updated successfully",
        {"entry": KnowledgeBaseResponse.model_validate(entry).model_dump(mode="json")},
    )


@router.delete("/knowledge-base/{entry_id}")
def delete_kb_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    delete_knowledge_base_entry(db, admin, entry_id)
    return api_success("Knowledge base entry deleted successfully", {"id": entry_id})


@router.get("/users")
def get_users(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    users = list_users(db)
    return api_success(
        "Users retrieved successfully",
        {
            "users": [
                AdminUserResponse.model_validate(user).model_dump(mode="json")
                for user in users
            ]
        },
    )


@router.patch("/users/{user_id}/status")
def patch_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    user = update_user_status(db, admin, user_id, payload.is_active)
    return api_success(
        "User status updated successfully",
        {"user": AdminUserResponse.model_validate(user).model_dump(mode="json")},
    )


@router.patch("/users/{user_id}/role")
def patch_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    user = update_user_role(db, admin, user_id, payload.role)
    return api_success(
        "User role updated successfully",
        {"user": AdminUserResponse.model_validate(user).model_dump(mode="json")},
    )


@router.delete("/users/{user_id}")
def remove_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    delete_user(db, admin, user_id)
    return api_success("User deleted successfully", {"id": user_id})

