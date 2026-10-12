"""Seed the database with the example dataset.

Relocated from the root seed.py. The important structural change is that the
schema is now created by an explicit call here rather than as a side effect of
importing the application.
"""
from datetime import timedelta

from flask_migrate import upgrade
from sqlalchemy import delete

from src.config.logging_config import get_logger
from src.extensions import db
from src.models.category_model import Category
from src.models.task_model import Task
from src.models.user_model import User
from src.utils.clock import utcnow

logger = get_logger(__name__)

USERS = (
    {"name": "João Silva", "email": "joao@email.com", "password": "1234", "role": "admin"},
    {"name": "Maria Santos", "email": "maria@email.com", "password": "abcd", "role": "user"},
    {"name": "Pedro Oliveira", "email": "pedro@email.com", "password": "pass", "role": "manager"},
)

CATEGORIES = (
    {"name": "Backend", "description": "Tarefas de backend", "color": "#3498db"},
    {"name": "Frontend", "description": "Tarefas de frontend", "color": "#2ecc71"},
    {"name": "DevOps", "description": "Tarefas de infraestrutura", "color": "#e74c3c"},
    {"name": "Bug", "description": "Correção de bugs", "color": "#e67e22"},
)


def _tasks(users, categories, now):
    """The example task set, expressed against the seeded users and categories."""
    backend, frontend, devops, bug = categories
    joao, maria, pedro = users
    return (
        {"title": "Implementar autenticação JWT", "description": "Adicionar autenticação real com JWT",
         "status": "pending", "priority": 1, "user": joao, "category": backend,
         "due_date": now - timedelta(days=3)},
        {"title": "Criar tela de login", "description": "Tela de login responsiva",
         "status": "in_progress", "priority": 2, "user": maria, "category": frontend,
         "due_date": now + timedelta(days=5)},
        {"title": "Configurar CI/CD", "description": "Pipeline com GitHub Actions",
         "status": "done", "priority": 2, "user": pedro, "category": devops,
         "tags": "devops,ci,github"},
        {"title": "Corrigir bug no filtro de busca", "description": "Filtro não funciona com caracteres especiais",
         "status": "pending", "priority": 1, "user": joao, "category": bug,
         "due_date": now - timedelta(days=1)},
        {"title": "Adicionar paginação na API", "description": "Endpoints retornam todos os registros",
         "status": "pending", "priority": 3, "user": joao, "category": backend,
         "due_date": now + timedelta(days=10)},
        {"title": "Escrever testes unitários", "description": "Cobertura mínima de 80%",
         "status": "pending", "priority": 2, "user": maria, "category": backend},
        {"title": "Documentar API com Swagger", "description": "Gerar documentação automática",
         "status": "cancelled", "priority": 4, "user": pedro, "category": backend},
        {"title": "Refatorar models", "description": "Melhorar organização dos models",
         "status": "in_progress", "priority": 3, "user": maria, "category": backend,
         "tags": "refactor,tech-debt"},
        {"title": "Configurar monitoramento", "description": "Prometheus + Grafana",
         "status": "pending", "priority": 4, "user": pedro, "category": devops,
         "due_date": now + timedelta(days=20)},
        {"title": "Melhorar validações de input", "description": "Usar marshmallow ou pydantic",
         "status": "pending", "priority": 3, "user": joao, "category": backend,
         "tags": "improvement,validation"},
    )


def seed_data(app, apply_migrations: bool = True) -> None:
    with app.app_context():
        if apply_migrations:
            # Bring the schema up to head through Alembic rather than
            # `db.create_all()`. create_all issues CREATE TABLE IF NOT EXISTS
            # and never alters an existing table, so a model change against an
            # existing tasks.db failed at query time with "no such column"
            # (DAT-X). This is the same work `flask db upgrade` does.
            upgrade()

        # Children first: these are bulk deletes, which bypass the ORM's
        # unit of work, so the ON DELETE clauses do not apply to them.
        db.session.execute(delete(Task))
        db.session.execute(delete(User))
        db.session.execute(delete(Category))
        db.session.commit()

        users = []
        for spec in USERS:
            user = User()
            user.name = spec["name"]
            user.email = spec["email"]
            user.set_password(spec["password"])
            user.role = spec["role"]
            db.session.add(user)
            users.append(user)

        categories = []
        for spec in CATEGORIES:
            category = Category()
            category.name = spec["name"]
            category.description = spec["description"]
            category.color = spec["color"]
            db.session.add(category)
            categories.append(category)

        db.session.commit()

        now = utcnow()
        for spec in _tasks(users, categories, now):
            task = Task()
            task.title = spec["title"]
            task.description = spec["description"]
            task.status = spec["status"]
            task.priority = spec["priority"]
            task.user_id = spec["user"].id
            task.category_id = spec["category"].id
            task.due_date = spec.get("due_date")
            task.tags = spec.get("tags")
            db.session.add(task)

        db.session.commit()

        logger.info(
            "seed complete: %d users, %d categories, %d tasks",
            User.count_all(), Category.count_all(), Task.count_all(),
        )
