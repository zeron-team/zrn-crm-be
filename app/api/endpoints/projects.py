"""Projects module — CRUD for projects, members, sprints, tasks, versions."""
import os
from typing import Optional, List
from datetime import datetime, timezone, date
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File as FastFile
from pydantic import BaseModel
from sqlalchemy import desc, func, asc
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.project import Project, ProjectMember, Sprint, Task, ProjectVersion, TaskChecklistItem, TaskAttachment, ProjectNote, ProjectWikiPage
from app.models.client import Client
from app.models.quote import Quote
from app.models.user import User
from app.api.endpoints.auth import get_current_user

router = APIRouter(prefix="/projects", tags=["projects"])


def check_project_access(project: Project, user, db: Session):
    """Raise 403 if non-admin user is not a member/PM/creator of the project."""
    is_admin = user.role and "admin" in user.role
    if is_admin:
        return
    is_member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project.id, ProjectMember.user_id == user.id
    ).first()
    if not is_member and project.pm_id != user.id and project.created_by != user.id:
        raise HTTPException(403, "No tenés acceso a este proyecto")


# ══════════════════════════════════════
#  Schemas
# ══════════════════════════════════════

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    key: str
    methodology: str = "kanban"
    client_id: Optional[int] = None
    quote_id: Optional[int] = None
    pm_id: Optional[int] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    methodology: Optional[str] = None
    client_id: Optional[int] = None
    quote_id: Optional[int] = None
    pm_id: Optional[int] = None

class MemberCreate(BaseModel):
    user_id: int
    role: str = "member"  # owner, admin, member, viewer

class VersionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    start_date: Optional[date] = None
    release_date: Optional[date] = None

class VersionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    release_date: Optional[date] = None
    status: Optional[str] = None

class SprintCreate(BaseModel):
    name: str
    goal: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    version_id: Optional[int] = None

class SprintUpdate(BaseModel):
    name: Optional[str] = None
    goal: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    version_id: Optional[int] = None

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    type: str = "task"
    priority: str = "medium"
    sprint_id: Optional[int] = None
    parent_id: Optional[int] = None
    assigned_to: Optional[int] = None
    story_points: Optional[int] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    labels: Optional[str] = None
    due_date: Optional[date] = None
    start_date: Optional[date] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    sprint_id: Optional[int] = None
    parent_id: Optional[int] = None
    assigned_to: Optional[int] = None
    story_points: Optional[int] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    labels: Optional[str] = None
    due_date: Optional[date] = None
    start_date: Optional[date] = None
    position: Optional[int] = None

class TaskMove(BaseModel):
    status: str
    position: int
    sprint_id: Optional[int] = None


# ══════════════════════════════════════
#  Helpers
# ══════════════════════════════════════

def task_to_dict(t: Task, db: Session, depth: int = 0) -> dict:
    """Convert task to dict with children count and checklist/attachment counts."""
    children_count = db.query(func.count(Task.id)).filter(Task.parent_id == t.id).scalar()
    checklist_count = db.query(func.count(TaskChecklistItem.id)).filter(TaskChecklistItem.task_id == t.id).scalar()
    checked_count = db.query(func.count(TaskChecklistItem.id)).filter(TaskChecklistItem.task_id == t.id, TaskChecklistItem.is_checked == True).scalar()
    attachments_count = db.query(func.count(TaskAttachment.id)).filter(TaskAttachment.task_id == t.id).scalar()
    return {
        "id": t.id, "key": t.key, "title": t.title, "description": t.description,
        "type": t.type, "status": t.status, "priority": t.priority,
        "assigned_to": t.assigned_to, "reporter": t.reporter,
        "story_points": t.story_points,
        "estimated_hours": t.estimated_hours, "actual_hours": t.actual_hours or 0,
        "position": t.position,
        "labels": t.labels, "due_date": str(t.due_date) if t.due_date else None,
        "start_date": str(t.start_date) if t.start_date else None,
        "sprint_id": t.sprint_id, "parent_id": t.parent_id,
        "project_id": t.project_id,
        "children_count": children_count,
        "checklist_count": checklist_count, "checked_count": checked_count,
        "attachments_count": attachments_count,
        "created_at": t.created_at, "updated_at": t.updated_at,
    }


# ══════════════════════════════════════
#  Projects CRUD
# ══════════════════════════════════════

@router.get("")
def list_projects(status: Optional[str] = Query(None), client_id: Optional[int] = Query(None),
                  db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    q = db.query(Project)
    if status:
        q = q.filter(Project.status == status)
    if client_id:
        q = q.filter(Project.client_id == client_id)
    # Non-admin users only see projects they're a member of (or PM/creator)
    is_admin = current_user.role and "admin" in current_user.role
    if not is_admin:
        member_project_ids = [m.project_id for m in
                              db.query(ProjectMember.project_id).filter(ProjectMember.user_id == current_user.id).all()]
        q = q.filter(
            (Project.id.in_(member_project_ids)) |
            (Project.pm_id == current_user.id) |
            (Project.created_by == current_user.id)
        )
    projects = q.order_by(desc(Project.updated_at)).all()
    result = []
    for p in projects:
        task_count = db.query(func.count(Task.id)).filter(Task.project_id == p.id).scalar()
        done_count = db.query(func.count(Task.id)).filter(Task.project_id == p.id, Task.status == "done").scalar()
        member_count = db.query(func.count(ProjectMember.id)).filter(ProjectMember.project_id == p.id).scalar()
        client_name = None
        if p.client_id:
            c = db.query(Client).get(p.client_id)
            client_name = c.name if c else None
        quote_number = None
        if p.quote_id:
            qt = db.query(Quote).get(p.quote_id)
            quote_number = qt.quote_number if qt else None
        created_by_name = None
        if p.created_by:
            u = db.query(User).get(p.created_by)
            created_by_name = u.full_name if u else None
        pm_name = None
        if p.pm_id:
            pm_user = db.query(User).get(p.pm_id)
            pm_name = pm_user.full_name if pm_user else None
        result.append({
            "id": p.id, "name": p.name, "description": p.description, "key": p.key,
            "status": p.status, "methodology": p.methodology,
            "client_id": p.client_id, "client_name": client_name,
            "quote_id": p.quote_id, "quote_number": quote_number,
            "created_by": p.created_by, "created_by_name": created_by_name,
            "pm_id": p.pm_id, "pm_name": pm_name,
            "created_at": p.created_at, "updated_at": p.updated_at,
            "task_count": task_count, "done_count": done_count, "member_count": member_count,
        })
    return result


@router.post("", status_code=201)
def create_project(data: ProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    existing = db.query(Project).filter(Project.key == data.key.upper()).first()
    if existing:
        raise HTTPException(400, f"Project key '{data.key}' already exists")
    dump = data.model_dump()
    if dump.get('quote_id') and not dump.get('client_id'):
        quote = db.query(Quote).get(dump['quote_id'])
        if quote and quote.client_id:
            dump['client_id'] = quote.client_id
    project = Project(**dump)
    project.key = data.key.upper()
    project.created_by = current_user.id
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    p = db.query(Project).get(project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    check_project_access(p, current_user, db)
    pm_name = None
    if p.pm_id:
        pm_user = db.query(User).get(p.pm_id)
        pm_name = pm_user.full_name if pm_user else None
    return {
        "id": p.id, "name": p.name, "description": p.description, "key": p.key,
        "status": p.status, "methodology": p.methodology,
        "client_id": p.client_id, "quote_id": p.quote_id,
        "created_by": p.created_by, "pm_id": p.pm_id, "pm_name": pm_name,
        "created_at": p.created_at, "updated_at": p.updated_at,
    }


@router.put("/{project_id}")
def update_project(project_id: int, data: ProjectUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    p = db.query(Project).get(project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    check_project_access(p, current_user, db)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    p.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    p = db.query(Project).get(project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    check_project_access(p, current_user, db)
    db.delete(p)
    db.commit()
    return {"ok": True}


# ══════════════════════════════════════
#  Members
# ══════════════════════════════════════

@router.get("/{project_id}/members")
def list_members(project_id: int, db: Session = Depends(get_db)):
    members = db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()
    result = []
    for m in members:
        u = db.query(User).get(m.user_id)
        result.append({
            "id": m.id,
            "user_id": m.user_id,
            "role": m.role,
            "full_name": u.full_name if u else "Usuario eliminado",
            "email": u.email if u else "",
            "is_active": u.is_active if u else False,
        })
    return result


@router.post("/{project_id}/members", status_code=201)
def add_member(project_id: int, data: MemberCreate, db: Session = Depends(get_db)):
    existing = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id, ProjectMember.user_id == data.user_id
    ).first()
    if existing:
        existing.role = data.role
        db.commit()
        db.refresh(existing)
        u = db.query(User).get(existing.user_id)
        return {"id": existing.id, "user_id": existing.user_id, "role": existing.role,
                "full_name": u.full_name if u else "", "email": u.email if u else "",
                "is_active": u.is_active if u else False}
    m = ProjectMember(project_id=project_id, **data.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    u = db.query(User).get(m.user_id)
    return {"id": m.id, "user_id": m.user_id, "role": m.role,
            "full_name": u.full_name if u else "", "email": u.email if u else "",
            "is_active": u.is_active if u else False}


@router.delete("/{project_id}/members/{member_id}")
def remove_member(project_id: int, member_id: int, db: Session = Depends(get_db)):
    m = db.query(ProjectMember).filter(ProjectMember.id == member_id, ProjectMember.project_id == project_id).first()
    if not m:
        raise HTTPException(404, "Member not found")
    db.delete(m)
    db.commit()
    return {"ok": True}


# ══════════════════════════════════════
#  Versions
# ══════════════════════════════════════

@router.get("/{project_id}/versions")
def list_versions(project_id: int, db: Session = Depends(get_db)):
    versions = db.query(ProjectVersion).filter(ProjectVersion.project_id == project_id).order_by(desc(ProjectVersion.created_at)).all()
    result = []
    for v in versions:
        sprint_count = db.query(func.count(Sprint.id)).filter(Sprint.version_id == v.id).scalar()
        result.append({
            "id": v.id, "name": v.name, "description": v.description,
            "start_date": str(v.start_date) if v.start_date else None,
            "release_date": str(v.release_date) if v.release_date else None,
            "status": v.status, "sprint_count": sprint_count,
            "created_at": v.created_at,
        })
    return result


@router.post("/{project_id}/versions", status_code=201)
def create_version(project_id: int, data: VersionCreate, db: Session = Depends(get_db)):
    v = ProjectVersion(project_id=project_id, **data.model_dump())
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


@router.put("/{project_id}/versions/{version_id}")
def update_version(project_id: int, version_id: int, data: VersionUpdate, db: Session = Depends(get_db)):
    v = db.query(ProjectVersion).filter(ProjectVersion.id == version_id, ProjectVersion.project_id == project_id).first()
    if not v:
        raise HTTPException(404, "Version not found")
    for k, val in data.model_dump(exclude_unset=True).items():
        setattr(v, k, val)
    db.commit()
    db.refresh(v)
    return v


@router.delete("/{project_id}/versions/{version_id}")
def delete_version(project_id: int, version_id: int, db: Session = Depends(get_db)):
    v = db.query(ProjectVersion).filter(ProjectVersion.id == version_id, ProjectVersion.project_id == project_id).first()
    if not v:
        raise HTTPException(404, "Version not found")
    db.delete(v)
    db.commit()
    return {"ok": True}


# ══════════════════════════════════════
#  Sprints
# ══════════════════════════════════════

@router.get("/{project_id}/sprints")
def list_sprints(project_id: int, version_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    q = db.query(Sprint).filter(Sprint.project_id == project_id)
    if version_id is not None:
        q = q.filter(Sprint.version_id == version_id)
    sprints = q.order_by(desc(Sprint.created_at)).all()
    result = []
    for s in sprints:
        result.append({
            "id": s.id, "name": s.name, "goal": s.goal,
            "start_date": str(s.start_date) if s.start_date else None,
            "end_date": str(s.end_date) if s.end_date else None,
            "status": s.status, "version_id": s.version_id,
            "created_at": s.created_at,
        })
    return result


@router.post("/{project_id}/sprints", status_code=201)
def create_sprint(project_id: int, data: SprintCreate, db: Session = Depends(get_db)):
    s = Sprint(project_id=project_id, **data.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.put("/{project_id}/sprints/{sprint_id}")
def update_sprint(project_id: int, sprint_id: int, data: SprintUpdate, db: Session = Depends(get_db)):
    s = db.query(Sprint).filter(Sprint.id == sprint_id, Sprint.project_id == project_id).first()
    if not s:
        raise HTTPException(404, "Sprint not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return s

@router.delete("/{project_id}/sprints/{sprint_id}")
def delete_sprint(project_id: int, sprint_id: int, db: Session = Depends(get_db)):
    s = db.query(Sprint).filter(Sprint.id == sprint_id, Sprint.project_id == project_id).first()
    if not s:
        raise HTTPException(404, "Sprint not found")
    # Move tasks to backlog
    db.query(Task).filter(Task.sprint_id == sprint_id).update({"sprint_id": None})
    db.delete(s)
    db.commit()
    return {"ok": True}


# ══════════════════════════════════════
#  Tasks
# ══════════════════════════════════════

@router.get("/{project_id}/tasks")
def list_tasks(
    project_id: int,
    sprint_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    assigned_to: Optional[int] = Query(None),
    parent_id: Optional[int] = Query(None),
    backlog: Optional[bool] = Query(None),
    root_only: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Task).filter(Task.project_id == project_id)
    if sprint_id is not None:
        q = q.filter(Task.sprint_id == sprint_id)
    if status:
        q = q.filter(Task.status == status)
    if type:
        q = q.filter(Task.type == type)
    if assigned_to is not None:
        q = q.filter(Task.assigned_to == assigned_to)
    if parent_id is not None:
        q = q.filter(Task.parent_id == parent_id)
    if backlog:
        q = q.filter(Task.sprint_id == None)
    if root_only:
        q = q.filter(Task.parent_id == None)
    tasks = q.order_by(Task.position, Task.created_at).all()
    return [task_to_dict(t, db) for t in tasks]


@router.post("/{project_id}/tasks", status_code=201)
def create_task(project_id: int, data: TaskCreate, db: Session = Depends(get_db)):
    project = db.query(Project).get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    # Auto-generate key
    max_num = db.query(func.count(Task.id)).filter(Task.project_id == project_id).scalar()
    task_key = f"{project.key}-{max_num + 1}"
    # Get max position
    max_pos = db.query(func.coalesce(func.max(Task.position), 0)).filter(
        Task.project_id == project_id, Task.status == "todo"
    ).scalar()
    task = Task(project_id=project_id, key=task_key, position=max_pos + 1, **data.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task_to_dict(task, db)


@router.get("/{project_id}/tasks/{task_id}")
def get_task(project_id: int, task_id: int, db: Session = Depends(get_db)):
    t = db.query(Task).filter(Task.id == task_id, Task.project_id == project_id).first()
    if not t:
        raise HTTPException(404, "Task not found")
    # Include children, checklist, attachments
    children = db.query(Task).filter(Task.parent_id == task_id).order_by(Task.position).all()
    checklist = db.query(TaskChecklistItem).filter(TaskChecklistItem.task_id == task_id).order_by(TaskChecklistItem.position).all()
    atts = db.query(TaskAttachment).filter(TaskAttachment.task_id == task_id).order_by(desc(TaskAttachment.created_at)).all()
    result = task_to_dict(t, db)
    result["children"] = [task_to_dict(c, db) for c in children]
    result["checklist"] = [{"id": ci.id, "text": ci.text, "is_checked": ci.is_checked, "position": ci.position} for ci in checklist]
    result["attachments"] = [{"id": a.id, "filename": a.filename, "file_url": a.file_url, "file_size": a.file_size, "created_at": str(a.created_at)} for a in atts]
    return result


@router.get("/{project_id}/tasks/{task_id}/subtasks")
def list_subtasks(project_id: int, task_id: int, db: Session = Depends(get_db)):
    children = db.query(Task).filter(Task.parent_id == task_id, Task.project_id == project_id).order_by(Task.position).all()
    return [task_to_dict(c, db) for c in children]


@router.put("/{project_id}/tasks/{task_id}")
def update_task(project_id: int, task_id: int, data: TaskUpdate, db: Session = Depends(get_db)):
    t = db.query(Task).filter(Task.id == task_id, Task.project_id == project_id).first()
    if not t:
        raise HTTPException(404, "Task not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    t.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(t)
    return task_to_dict(t, db)


@router.patch("/{project_id}/tasks/{task_id}/move")
def move_task(project_id: int, task_id: int, data: TaskMove, db: Session = Depends(get_db)):
    t = db.query(Task).filter(Task.id == task_id, Task.project_id == project_id).first()
    if not t:
        raise HTTPException(404, "Task not found")
    t.status = data.status
    t.position = data.position
    if data.sprint_id is not None:
        t.sprint_id = data.sprint_id
    t.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


@router.delete("/{project_id}/tasks/{task_id}")
def delete_task(project_id: int, task_id: int, db: Session = Depends(get_db)):
    t = db.query(Task).filter(Task.id == task_id, Task.project_id == project_id).first()
    if not t:
        raise HTTPException(404, "Task not found")
    db.delete(t)
    db.commit()
    return {"ok": True}


# ══════════════════════════════════════
#  Gantt Data
# ══════════════════════════════════════

@router.get("/{project_id}/gantt")
def gantt_data(project_id: int, db: Session = Depends(get_db)):
    """Return all tasks with dates for Gantt rendering."""
    tasks = db.query(Task).filter(Task.project_id == project_id).order_by(Task.type.desc(), Task.position).all()
    result = []
    for t in tasks:
        result.append({
            "id": t.id, "key": t.key, "title": t.title,
            "type": t.type, "status": t.status, "priority": t.priority,
            "parent_id": t.parent_id,
            "start_date": str(t.start_date) if t.start_date else str(t.created_at.date()),
            "end_date": str(t.due_date) if t.due_date else None,
            "progress": 100 if t.status == "done" else (50 if t.status in ("in_progress", "in_review") else 0),
            "assigned_to": t.assigned_to,
        })
    return result


# ══════════════════════════════════════
#  Checklist Items
# ══════════════════════════════════════

class ChecklistItemCreate(BaseModel):
    text: str

class ChecklistItemUpdate(BaseModel):
    text: Optional[str] = None
    is_checked: Optional[bool] = None
    position: Optional[int] = None

@router.get("/{project_id}/tasks/{task_id}/checklist")
def list_checklist(project_id: int, task_id: int, db: Session = Depends(get_db)):
    items = db.query(TaskChecklistItem).filter(TaskChecklistItem.task_id == task_id).order_by(TaskChecklistItem.position).all()
    return [{"id": ci.id, "text": ci.text, "is_checked": ci.is_checked, "position": ci.position} for ci in items]

@router.post("/{project_id}/tasks/{task_id}/checklist", status_code=201)
def add_checklist_item(project_id: int, task_id: int, data: ChecklistItemCreate, db: Session = Depends(get_db)):
    max_pos = db.query(func.coalesce(func.max(TaskChecklistItem.position), 0)).filter(TaskChecklistItem.task_id == task_id).scalar()
    item = TaskChecklistItem(task_id=task_id, text=data.text, position=max_pos + 1)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "text": item.text, "is_checked": item.is_checked, "position": item.position}

@router.put("/{project_id}/tasks/{task_id}/checklist/{item_id}")
def update_checklist_item(project_id: int, task_id: int, item_id: int, data: ChecklistItemUpdate, db: Session = Depends(get_db)):
    ci = db.query(TaskChecklistItem).filter(TaskChecklistItem.id == item_id, TaskChecklistItem.task_id == task_id).first()
    if not ci:
        raise HTTPException(404, "Checklist item not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(ci, k, v)
    db.commit()
    db.refresh(ci)
    return {"id": ci.id, "text": ci.text, "is_checked": ci.is_checked, "position": ci.position}

@router.delete("/{project_id}/tasks/{task_id}/checklist/{item_id}")
def delete_checklist_item(project_id: int, task_id: int, item_id: int, db: Session = Depends(get_db)):
    ci = db.query(TaskChecklistItem).filter(TaskChecklistItem.id == item_id, TaskChecklistItem.task_id == task_id).first()
    if not ci:
        raise HTTPException(404, "Checklist item not found")
    db.delete(ci)
    db.commit()
    return {"ok": True}


# ══════════════════════════════════════
#  Task Attachments
# ══════════════════════════════════════

UPLOAD_DIR = "uploads/task_attachments"

@router.get("/{project_id}/tasks/{task_id}/attachments")
def list_attachments(project_id: int, task_id: int, db: Session = Depends(get_db)):
    atts = db.query(TaskAttachment).filter(TaskAttachment.task_id == task_id).order_by(desc(TaskAttachment.created_at)).all()
    return [{"id": a.id, "filename": a.filename, "file_url": a.file_url, "file_size": a.file_size, "created_at": str(a.created_at)} for a in atts]

@router.post("/{project_id}/tasks/{task_id}/attachments", status_code=201)
def upload_attachment(project_id: int, task_id: int, file: UploadFile = FastFile(...), db: Session = Depends(get_db)):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_name = f"{task_id}_{int(datetime.now().timestamp())}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)
    content = file.file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    file_url = f"/{UPLOAD_DIR}/{safe_name}"
    att = TaskAttachment(task_id=task_id, filename=file.filename, file_url=file_url, file_size=len(content))
    db.add(att)
    db.commit()
    db.refresh(att)
    return {"id": att.id, "filename": att.filename, "file_url": att.file_url, "file_size": att.file_size, "created_at": str(att.created_at)}

@router.delete("/{project_id}/tasks/{task_id}/attachments/{att_id}")
def delete_attachment(project_id: int, task_id: int, att_id: int, db: Session = Depends(get_db)):
    att = db.query(TaskAttachment).filter(TaskAttachment.id == att_id, TaskAttachment.task_id == task_id).first()
    if not att:
        raise HTTPException(404, "Attachment not found")
    # Remove file
    local_path = att.file_url.lstrip("/")
    if os.path.exists(local_path):
        os.remove(local_path)
    db.delete(att)
    db.commit()
    return {"ok": True}


# ══════════════════════════════════════
#  Project Summary / Overview
# ══════════════════════════════════════

@router.get("/{project_id}/summary")
def project_summary(project_id: int, db: Session = Depends(get_db)):
    """Aggregated project dashboard data."""
    p = db.query(Project).get(project_id)
    if not p:
        raise HTTPException(404, "Project not found")

    all_tasks = db.query(Task).filter(Task.project_id == project_id).all()
    all_sprints = db.query(Sprint).filter(Sprint.project_id == project_id).order_by(Sprint.created_at).all()
    all_versions = db.query(ProjectVersion).filter(ProjectVersion.project_id == project_id).order_by(ProjectVersion.created_at).all()
    members = db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()

    # Client + PM names
    client_name = None
    if p.client_id:
        c = db.query(Client).get(p.client_id)
        client_name = c.name if c else None
    pm_name = None
    if p.pm_id:
        pm_user = db.query(User).get(p.pm_id)
        pm_name = pm_user.full_name if pm_user else None
    created_by_name = None
    if p.created_by:
        u = db.query(User).get(p.created_by)
        created_by_name = u.full_name if u else None

    # Task counts by status
    status_counts = {}
    type_counts = {}
    total_sp = 0
    total_est = 0.0
    total_act = 0.0
    for t in all_tasks:
        status_counts[t.status] = status_counts.get(t.status, 0) + 1
        type_counts[t.type] = type_counts.get(t.type, 0) + 1
        total_sp += t.story_points or 0
        total_est += t.estimated_hours or 0
        total_act += t.actual_hours or 0

    # Sprint breakdown — weighted progress for intermediate statuses
    status_weight = {'todo': 0, 'in_progress': 0.5, 'in_review': 0.75, 'review': 0.75, 'done': 1.0}
    sprint_breakdown = []
    for s in all_sprints:
        s_tasks = [t for t in all_tasks if t.sprint_id == s.id]
        s_done = sum(1 for t in s_tasks if t.status == 'done')
        s_progress = sum(status_weight.get(t.status, 0.25) for t in s_tasks)
        s_sp = sum(t.story_points or 0 for t in s_tasks)
        s_est = sum(t.estimated_hours or 0 for t in s_tasks)
        s_act = sum(t.actual_hours or 0 for t in s_tasks)
        sprint_breakdown.append({
            "id": s.id, "name": s.name, "status": s.status,
            "version_id": s.version_id,
            "start_date": str(s.start_date) if s.start_date else None,
            "end_date": str(s.end_date) if s.end_date else None,
            "task_count": len(s_tasks), "done_count": s_done,
            "story_points": s_sp, "estimated_hours": round(s_est, 1),
            "actual_hours": round(s_act, 1),
            "completion": round(s_progress / len(s_tasks) * 100) if s_tasks else 0,
        })

    # Backlog (tasks without sprint)
    backlog_tasks = [t for t in all_tasks if t.sprint_id is None]
    backlog_sp = sum(t.story_points or 0 for t in backlog_tasks)

    # Version roadmap
    version_info = []
    for v in all_versions:
        v_sprints = [s for s in sprint_breakdown if s["version_id"] == v.id]
        v_tasks = sum(s["task_count"] for s in v_sprints)
        v_done = sum(s["done_count"] for s in v_sprints)
        version_info.append({
            "id": v.id, "name": v.name, "status": v.status,
            "description": v.description,
            "start_date": str(v.start_date) if v.start_date else None,
            "release_date": str(v.release_date) if v.release_date else None,
            "sprint_count": len(v_sprints), "sprints": [s["name"] for s in v_sprints],
            "task_count": v_tasks, "done_count": v_done,
            "completion": round(v_done / v_tasks * 100) if v_tasks else 0,
        })

    # Resource allocation
    user_ids = set(t.assigned_to for t in all_tasks if t.assigned_to)
    resource_alloc = []
    for uid in user_ids:
        u = db.query(User).get(uid)
        u_tasks = [t for t in all_tasks if t.assigned_to == uid]
        u_done = sum(1 for t in u_tasks if t.status == 'done')
        u_sp = sum(t.story_points or 0 for t in u_tasks)
        u_est = sum(t.estimated_hours or 0 for t in u_tasks)
        u_act = sum(t.actual_hours or 0 for t in u_tasks)
        resource_alloc.append({
            "user_id": uid, "name": u.full_name if u else "Unknown",
            "task_count": len(u_tasks), "done_count": u_done,
            "story_points": u_sp,
            "estimated_hours": round(u_est, 1), "actual_hours": round(u_act, 1),
        })

    return {
        "project": {
            "id": p.id, "name": p.name, "key": p.key, "status": p.status,
            "methodology": p.methodology, "description": p.description,
            "client_name": client_name, "pm_name": pm_name,
            "created_by_name": created_by_name,
            "created_at": p.created_at, "updated_at": p.updated_at,
        },
        "totals": {
            "tasks": len(all_tasks), "done": status_counts.get("done", 0),
            "in_progress": status_counts.get("in_progress", 0),
            "todo": status_counts.get("todo", 0),
            "story_points": total_sp,
            "estimated_hours": round(total_est, 1),
            "actual_hours": round(total_act, 1),
            "members": len(members),
            "sprints": len(all_sprints),
            "versions": len(all_versions),
        },
        "status_counts": status_counts,
        "type_counts": type_counts,
        "sprint_breakdown": sprint_breakdown,
        "backlog": {"task_count": len(backlog_tasks), "story_points": backlog_sp},
        "versions": version_info,
        "resources": resource_alloc,
    }


# ══════════════════════════════════════
#  Project Notes
# ══════════════════════════════════════

class NoteCreate(BaseModel):
    title: str
    content: Optional[str] = None
    color: str = "yellow"
    visibility: str = "team"
    shared_with: Optional[list] = None

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    color: Optional[str] = None
    visibility: Optional[str] = None
    shared_with: Optional[list] = None

class NoteReorder(BaseModel):
    order: list

def _note_dict(n, db):
    return {
        "id": n.id, "title": n.title, "content": n.content, "color": n.color,
        "sort_order": n.sort_order or 0,
        "visibility": n.visibility or "team",
        "shared_with": n.shared_with or [],
        "created_by": n.created_by,
        "created_by_name": db.query(User).get(n.created_by).full_name if n.created_by else None,
        "created_at": n.created_at, "updated_at": n.updated_at,
    }

@router.get("/{project_id}/notes")
def list_notes(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    uid = current_user.id
    notes = db.query(ProjectNote).filter(ProjectNote.project_id == project_id)\
        .order_by(ProjectNote.sort_order.asc(), desc(ProjectNote.updated_at)).all()
    result = []
    for n in notes:
        if n.visibility == "private" and n.created_by != uid:
            continue
        if n.visibility == "shared" and n.created_by != uid:
            if not n.shared_with or uid not in n.shared_with:
                continue
        result.append(_note_dict(n, db))
    return result

@router.post("/{project_id}/notes", status_code=201)
def create_note(project_id: int, data: NoteCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    max_order = db.query(ProjectNote).filter(ProjectNote.project_id == project_id).count()
    n = ProjectNote(
        project_id=project_id, title=data.title, content=data.content,
        color=data.color, created_by=current_user.id, sort_order=max_order,
        visibility=data.visibility,
        shared_with=data.shared_with if data.visibility == "shared" else None,
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    return _note_dict(n, db)

@router.put("/{project_id}/notes/reorder")
def reorder_notes(project_id: int, data: NoteReorder, db: Session = Depends(get_db)):
    for idx, nid in enumerate(data.order):
        n = db.query(ProjectNote).filter(ProjectNote.id == nid, ProjectNote.project_id == project_id).first()
        if n:
            n.sort_order = idx
    db.commit()
    return {"ok": True}

@router.put("/{project_id}/notes/{note_id}")
def update_note(project_id: int, note_id: int, data: NoteUpdate, db: Session = Depends(get_db)):
    n = db.query(ProjectNote).filter(ProjectNote.id == note_id, ProjectNote.project_id == project_id).first()
    if not n:
        raise HTTPException(404, "Note not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(n, k, v)
    db.commit()
    db.refresh(n)
    return _note_dict(n, db)

@router.delete("/{project_id}/notes/{note_id}")
def delete_note(project_id: int, note_id: int, db: Session = Depends(get_db)):
    n = db.query(ProjectNote).filter(ProjectNote.id == note_id, ProjectNote.project_id == project_id).first()
    if not n:
        raise HTTPException(404, "Note not found")
    db.delete(n)
    db.commit()
    return {"ok": True}


# ══════════════════════════════════════
#  Project Wiki
# ══════════════════════════════════════

class WikiCreate(BaseModel):
    title: str
    content: Optional[str] = None
    parent_id: Optional[int] = None

class WikiUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    parent_id: Optional[int] = None

@router.get("/{project_id}/wiki")
def list_wiki(project_id: int, db: Session = Depends(get_db)):
    pages = db.query(ProjectWikiPage).filter(ProjectWikiPage.project_id == project_id).order_by(ProjectWikiPage.created_at).all()
    return [{
        "id": pg.id, "title": pg.title, "content": pg.content,
        "slug": pg.slug, "parent_id": pg.parent_id,
        "created_by": pg.created_by,
        "created_by_name": db.query(User).get(pg.created_by).full_name if pg.created_by else None,
        "created_at": pg.created_at, "updated_at": pg.updated_at,
    } for pg in pages]

@router.post("/{project_id}/wiki", status_code=201)
def create_wiki_page(project_id: int, data: WikiCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    import re
    slug = re.sub(r'[^a-z0-9]+', '-', data.title.lower()).strip('-')
    pg = ProjectWikiPage(project_id=project_id, title=data.title, content=data.content, slug=slug,
                         parent_id=data.parent_id, created_by=current_user.id)
    db.add(pg)
    db.commit()
    db.refresh(pg)
    return {"id": pg.id, "title": pg.title, "content": pg.content, "slug": pg.slug, "parent_id": pg.parent_id, "created_at": pg.created_at}

@router.put("/{project_id}/wiki/{page_id}")
def update_wiki_page(project_id: int, page_id: int, data: WikiUpdate, db: Session = Depends(get_db)):
    pg = db.query(ProjectWikiPage).filter(ProjectWikiPage.id == page_id, ProjectWikiPage.project_id == project_id).first()
    if not pg:
        raise HTTPException(404, "Wiki page not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(pg, k, v)
    if data.title:
        import re
        pg.slug = re.sub(r'[^a-z0-9]+', '-', data.title.lower()).strip('-')
    db.commit()
    db.refresh(pg)
    return {"id": pg.id, "title": pg.title, "content": pg.content, "slug": pg.slug, "parent_id": pg.parent_id, "updated_at": pg.updated_at}

@router.delete("/{project_id}/wiki/{page_id}")
def delete_wiki_page(project_id: int, page_id: int, db: Session = Depends(get_db)):
    pg = db.query(ProjectWikiPage).filter(ProjectWikiPage.id == page_id, ProjectWikiPage.project_id == project_id).first()
    if not pg:
        raise HTTPException(404, "Wiki page not found")
    db.delete(pg)
    db.commit()
    return {"ok": True}

