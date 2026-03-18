"""
Projects Module — Projects, Wiki.
"""
from app.modules import ModuleManifest


def register(registry):
    from app.api.endpoints import projects, wiki

    manifest = ModuleManifest(
        name="Proyectos",
        slug="projects",
        version="8.2.5",
        description="Gestión de proyectos con tablero Kanban y Wiki colaborativa",
        icon="FolderKanban",
        category="business",
        dependencies=["core"],
        routes=[
            (projects.router, "", ["projects"]),
            (wiki.router, "", ["wiki"]),
        ],
    )
    registry.register(manifest)
