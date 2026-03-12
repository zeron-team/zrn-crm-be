from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, Boolean, Float, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    key = Column(String(10), unique=True, nullable=False)  # e.g. "ZRN"
    status = Column(String(20), default="active")  # active, completed, archived
    methodology = Column(String(10), default="kanban")  # kanban, scrum
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    quote_id = Column(Integer, ForeignKey("quotes.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    pm_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Project Manager
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    client = relationship("Client", backref="projects")
    quote = relationship("Quote", backref="projects")
    creator = relationship("User", foreign_keys=[created_by], backref="created_projects")
    pm = relationship("User", foreign_keys=[pm_id], backref="managed_projects")
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    sprints = relationship("Sprint", back_populates="project", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    versions = relationship("ProjectVersion", back_populates="project", cascade="all, delete-orphan")


class ProjectMember(Base):
    __tablename__ = "project_members"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(20), default="member")  # owner, admin, member

    project = relationship("Project", back_populates="members")
    user = relationship("User", backref="project_memberships")


class ProjectVersion(Base):
    __tablename__ = "project_versions"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)  # e.g. "v1.0", "v2.0"
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=True)
    release_date = Column(Date, nullable=True)
    status = Column(String(20), default="planned")  # planned, in_progress, released
    repository_url = Column(String(500), nullable=True)  # Git repo URL for this version
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="versions")
    sprints = relationship("Sprint", back_populates="version")


class Sprint(Base):
    __tablename__ = "sprints"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    version_id = Column(Integer, ForeignKey("project_versions.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(100), nullable=False)
    goal = Column(Text, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    status = Column(String(20), default="planning")  # planning, active, completed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="sprints")
    version = relationship("ProjectVersion", back_populates="sprints")
    tasks = relationship("Task", back_populates="sprint")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    sprint_id = Column(Integer, ForeignKey("sprints.id", ondelete="SET NULL"), nullable=True)
    parent_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)
    key = Column(String(20), nullable=False, index=True)  # e.g. "ZRN-1"
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(20), default="task")  # epic, feature, story, task, bug, subtask
    status = Column(String(20), default="todo")  # todo, in_progress, in_review, done
    priority = Column(String(20), default="medium")  # low, medium, high, critical
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    reporter = Column(Integer, ForeignKey("users.id"), nullable=True)
    story_points = Column(Integer, nullable=True)
    estimated_hours = Column(Float, nullable=True)  # Horas estimadas
    actual_hours = Column(Float, default=0)  # Horas dedicadas
    position = Column(Integer, default=0)  # order within column
    labels = Column(String(500), nullable=True)  # comma-separated
    due_date = Column(Date, nullable=True)
    start_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="tasks")
    sprint = relationship("Sprint", back_populates="tasks")
    parent = relationship("Task", remote_side=[id], backref="children")
    assignee = relationship("User", foreign_keys=[assigned_to], backref="assigned_tasks")
    reporter_user = relationship("User", foreign_keys=[reporter], backref="reported_tasks")
    checklist_items = relationship("TaskChecklistItem", back_populates="task", cascade="all, delete-orphan", order_by="TaskChecklistItem.position")
    attachments = relationship("TaskAttachment", back_populates="task", cascade="all, delete-orphan")


class TaskChecklistItem(Base):
    __tablename__ = "task_checklist_items"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    text = Column(String(500), nullable=False)
    is_checked = Column(Boolean, default=False)
    position = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    task = relationship("Task", back_populates="checklist_items")


class TaskAttachment(Base):
    __tablename__ = "task_attachments"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_url = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)  # bytes
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    task = relationship("Task", back_populates="attachments")
    uploader = relationship("User", backref="task_uploads")


class ProjectNote(Base):
    __tablename__ = "project_notes"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)
    color = Column(String(20), default="yellow")
    sort_order = Column(Integer, default=0)
    visibility = Column(String(20), default="team")        # private, team, shared
    shared_with = Column(JSON, nullable=True)               # list of user IDs
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("Project", backref="notes")
    creator = relationship("User", backref="project_notes_created")


class ProjectWikiPage(Base):
    __tablename__ = "project_wiki_pages"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)
    slug = Column(String(255), nullable=True)
    parent_id = Column(Integer, ForeignKey("project_wiki_pages.id", ondelete="SET NULL"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("Project", backref="wiki_pages")
    parent = relationship("ProjectWikiPage", remote_side=[id], backref="children")
    creator = relationship("User", backref="wiki_pages_created")
