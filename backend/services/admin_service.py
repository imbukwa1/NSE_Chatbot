from fastapi import HTTPException, status
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from auth.roles import ROLE_ADMIN
from models.knowledge_base import KnowledgeBaseEntry
from models.user import User
from schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate
from services.logging_service import log_admin_action


def list_users(db: Session) -> list[User]:
    return db.query(User).order_by(User.created_at.desc()).all()


def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user


def update_user_status(db: Session, admin: User, user_id: int, is_active: bool) -> User:
    user = get_user_or_404(db, user_id)
    if user.id == admin.id and not is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot deactivate their own account.",
        )
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    log_admin_action(db, admin.id, "Changed user status", f"user:{user.id}")
    return user


def update_user_role(db: Session, admin: User, user_id: int, role: str) -> User:
    user = get_user_or_404(db, user_id)
    if user.id == admin.id and role != ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot remove their own admin role.",
        )
    user.role = role
    db.commit()
    db.refresh(user)
    log_admin_action(db, admin.id, "Changed user role", f"user:{user.id}")
    return user


def delete_user(db: Session, admin: User, user_id: int) -> None:
    user = get_user_or_404(db, user_id)
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot delete their own account.",
        )
    db.delete(user)
    db.commit()
    log_admin_action(db, admin.id, "Deleted user", f"user:{user_id}")


def list_knowledge_base(db: Session) -> list[KnowledgeBaseEntry]:
    return db.query(KnowledgeBaseEntry).order_by(KnowledgeBaseEntry.updated_at.desc()).all()


def search_knowledge_base(db: Session, query: str | None = None) -> list[KnowledgeBaseEntry]:
    base_query = db.query(KnowledgeBaseEntry)
    if query:
        pattern = f"%{query.strip().lower()}%"
        base_query = base_query.filter(
            func.lower(KnowledgeBaseEntry.question).like(pattern)
            | func.lower(KnowledgeBaseEntry.aliases).like(pattern)
            | func.lower(KnowledgeBaseEntry.keywords).like(pattern)
            | func.lower(KnowledgeBaseEntry.related_questions).like(pattern)
            | func.lower(KnowledgeBaseEntry.slug).like(pattern)
        )
    return base_query.order_by(KnowledgeBaseEntry.updated_at.desc()).limit(100).all()


def get_knowledge_base_stats(db: Session) -> dict:
    categories = (
        db.query(KnowledgeBaseEntry.category, func.count(KnowledgeBaseEntry.id))
        .group_by(KnowledgeBaseEntry.category)
        .order_by(KnowledgeBaseEntry.category)
        .all()
    )
    last_import = db.execute(
        text(
            """
            SELECT imported_at, files_scanned, rows_seen, imported_count, skipped_count, status
            FROM knowledge_base_imports
            ORDER BY imported_at DESC
            LIMIT 1
            """
        )
    ).mappings().first()
    return {
        "total_articles": db.query(func.count(KnowledgeBaseEntry.id)).scalar() or 0,
        "categories": [category for category, _ in categories if category],
        "articles_per_category": [
            {"category": category or "Uncategorized", "count": count}
            for category, count in categories
        ],
        "last_import": dict(last_import) if last_import else None,
    }


def reimport_knowledge_base(db: Session) -> dict:
    from scripts.import_knowledgebase import import_knowledgebase

    return import_knowledgebase(db=db)


def create_knowledge_base_entry(
    db: Session,
    admin: User,
    payload: KnowledgeBaseCreate,
) -> KnowledgeBaseEntry:
    entry = KnowledgeBaseEntry(
        category=payload.category.strip(),
        question=payload.question.strip(),
        answer=payload.answer.strip(),
        answer_markdown=payload.answer.strip(),
        source=payload.source.strip() if payload.source else None,
        created_by=admin.id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    log_admin_action(db, admin.id, "Created knowledge base entry", f"kb:{entry.id}")
    return entry


def get_kb_or_404(db: Session, entry_id: int) -> KnowledgeBaseEntry:
    entry = db.query(KnowledgeBaseEntry).filter(KnowledgeBaseEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base entry not found.",
        )
    return entry


def update_knowledge_base_entry(
    db: Session,
    admin: User,
    entry_id: int,
    payload: KnowledgeBaseUpdate,
) -> KnowledgeBaseEntry:
    entry = get_kb_or_404(db, entry_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(entry, field, value.strip() if isinstance(value, str) else value)
        if field == "answer" and isinstance(value, str):
            entry.answer_markdown = value.strip()
    db.commit()
    db.refresh(entry)
    log_admin_action(db, admin.id, "Updated knowledge base entry", f"kb:{entry.id}")
    return entry


def delete_knowledge_base_entry(db: Session, admin: User, entry_id: int) -> None:
    entry = get_kb_or_404(db, entry_id)
    db.delete(entry)
    db.commit()
    log_admin_action(db, admin.id, "Deleted knowledge base entry", f"kb:{entry_id}")
