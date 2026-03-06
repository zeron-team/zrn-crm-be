"""Projects module — CRUD for projects, members, sprints, tasks, versions."""
import os
from typing import Optional, List
from datetime import datetime, timezone, date
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File as FastFile
from pydantic import BaseModel
from sqlalchemy import desc, func, asc
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.project import Project, ProjectMember, Sprint, Task, ProjectVersion, TaskChecklistItem, TaskAttachment
from app.models.client import Client
from app.models.quote import Quote

router = APIRouter(prefix="/projects", tags=["projects"])


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

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    methodology: Optional[str] = None
    client_id: Optional[int] = None
    quote_id: Optional[int] = None

class MemberCreate(BaseModel):
    user_id: int
    role: str = "member"

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
        "story_points": t.story_points, "position": t.position,
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
def list_projects(status: Optional[str] = Query(None), client_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    q = db.query(Project)
    if status:
        q = q.filter(Project.status == status)
    if client_id:
        q = q.filter(Project.client_id == client_id)
    projects = q.order_by(desc(Project.updated_at)).all()
    result = []
    for p in projects:
        task_count = db.query(func.count(Task.id)).filter(Task.project_id == p.id).scalar()
        done_count = db.query(func.count(Task.id)).filter(Task.project_id == p.id, Task.status == "done").scalar()
        member_count = db.query(func.count(ProjectMember.id)).filter(ProjectMember.project_id == p.id).scalar()
        client_name = None
        if p.client_id:
            c = db.query(Client).get(p.client_id)
            client_name = c.company_name if c else None
        quote_number = None
        if p.quote_id:
            qt = db.query(Quote).get(p.quote_id)
            quote_number = qt.quote_number if qt else None
        result.append({
            "id": p.id, "name": p.name, "description": p.description, "key": p.key,
            "status": p.status, "methodology": p.methodology,
            "client_id": p.client_id, "client_name": client_name,
            "quote_id": p.quote_id, "quote_number": quote_number,
            "created_by": p.created_by, "created_at": p.created_at, "updated_at": p.updated_at,
            "task_count": task_count, "done_count": done_count, "member_count": member_count,
        })
    return result


@router.post("", status_code=201)
def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
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
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db)):
    p = db.query(Project).get(project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    return {
        "id": p.id, "name": p.name, "description": p.description, "key": p.key,
        "status": p.status, "methodology": p.methodology,
        "client_id": p.client_id, "quote_id": p.quote_id,
        "created_by": p.created_by, "created_at": p.created_at, "updated_at": p.updated_at,
    }


@router.put("/{project_id}")
def update_project(project_id: int, data: ProjectUpdate, db: Session = Depends(get_db)):
    p = db.query(Project).get(project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    p.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    p = db.query(Project).get(project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    db.delete(p)
    db.commit()
    return {"ok": True}


# ══════════════════════════════════════
#  Members
# ══════════════════════════════════════

@router.get("/{project_id}/members")
def list_members(project_id: int, db: Session = Depends(get_db)):
    return db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()


@router.post("/{project_id}/members", status_code=201)
def add_member(project_id: int, data: MemberCreate, db: Session = Depends(get_db)):
    existing = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id, ProjectMember.user_id == data.user_id
    ).first()
    if existing:
        existing.role = data.role
        db.commit()
        db.refresh(existing)
        return existing
    m = ProjectMember(project_id=project_id, **data.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


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
