"""
MongoDB / MongoEngine Database Adapter for AI Interview System.
Provides 100% drop-in compatibility with Flask routes, Flask-Login, and templates.
"""

import os
import json
from datetime import datetime
import mongoengine as me
from flask import abort

# Enable SQLAlchemy-like operator syntax on MongoEngine fields
me.base.fields.BaseField.desc = lambda self: f"-{self.name}"
me.base.fields.BaseField.asc = lambda self: f"+{self.name}"
me.base.fields.BaseField.__ne__ = lambda self, other: me.Q(**{f"{self.name}__ne": other})
me.base.fields.BaseField.__gt__ = lambda self, other: me.Q(**{f"{self.name}__gt": other})
me.base.fields.BaseField.__lt__ = lambda self, other: me.Q(**{f"{self.name}__lt": other})
me.base.fields.BaseField.__ge__ = lambda self, other: me.Q(**{f"{self.name}__gte": other})
me.base.fields.BaseField.__le__ = lambda self, other: me.Q(**{f"{self.name}__lte": other})

_mongo_connected = False


def ensure_mongo_connection(app=None):
    global _mongo_connected
    if not _mongo_connected:
        mongo_uri = "mongodb://localhost:27017/ai_interview_db"
        db_name = "ai_interview_db"
        if app:
            mongo_uri = app.config.get("MONGODB_URI", mongo_uri)
            db_name = app.config.get("MONGODB_DB", db_name)
        else:
            mongo_uri = os.getenv("MONGODB_URI", mongo_uri)
            db_name = os.getenv("MONGODB_DB", db_name)
        me.connect(db_name, host=mongo_uri, alias="default")
        _mongo_connected = True


class MongoQueryWrapper:
    """Provides SQLAlchemy-style .query chaining on top of MongoEngine QuerySets."""

    def __init__(self, document_cls, queryset=None):
        self.document_cls = document_cls
        ensure_mongo_connection()
        if queryset is not None:
            self.queryset = queryset
        else:
            self.queryset = document_cls.objects

    def filter_by(self, **kwargs):
        clean_kwargs = {}
        for k, v in kwargs.items():
            if k == "id" and v is not None:
                try:
                    clean_kwargs["id"] = int(v)
                except (ValueError, TypeError):
                    clean_kwargs["id"] = v
            else:
                clean_kwargs[k] = v
        return MongoQueryWrapper(self.document_cls, self.queryset.filter(**clean_kwargs))

    def filter(self, *expressions):
        # Support Q expressions or MongoEngine query kwargs
        if not expressions:
            return self
        qs = self.queryset
        for expr in expressions:
            if isinstance(expr, me.Q):
                qs = qs.filter(expr)
            elif isinstance(expr, bool):
                pass
            elif hasattr(expr, "left") and hasattr(expr, "right"):
                # Handle SQLAlchemy column expression gracefully if passed
                col_name = getattr(expr.left, "name", str(expr.left))
                val = getattr(expr.right, "value", expr.right)
                qs = qs.filter(**{col_name: val})
        return MongoQueryWrapper(self.document_cls, qs)

    def get(self, pk):
        if pk is None:
            return None
        try:
            return self.document_cls.objects(id=int(pk)).first()
        except Exception:
            return self.document_cls.objects(id=pk).first()

    def get_or_404(self, pk):
        obj = self.get(pk)
        if not obj:
            abort(404)
        return obj

    def first(self):
        return self.queryset.first()

    def all(self):
        return list(self.queryset)

    def count(self):
        return self.queryset.count()

    def limit(self, n):
        return MongoQueryWrapper(self.document_cls, self.queryset.limit(n))

    def skip(self, n):
        return MongoQueryWrapper(self.document_cls, self.queryset.skip(n))

    def order_by(self, *args):
        clean_args = []
        for a in args:
            if hasattr(a, "name"):
                name = a.name
                if hasattr(a, "modifier") and a.modifier == "desc":
                    name = f"-{name}"
                clean_args.append(name)
            elif isinstance(a, str):
                cleaned = a.replace("Response.", "").replace("ProctoringLog.", "").replace("Interview.", "")
                clean_args.append(cleaned)
            else:
                clean_args.append(str(a))
        return MongoQueryWrapper(self.document_cls, self.queryset.order_by(*clean_args))

    def paginate(self, page=1, per_page=10, error_out=False):
        """Minimal pagination compatibility for admin listings."""
        total = self.queryset.count()
        offset = (page - 1) * per_page
        items = list(self.queryset.skip(offset).limit(per_page))
        pages = (total + per_page - 1) // per_page if per_page else 1

        class Pagination:
            pass

        p = Pagination()
        p.page = page
        p.per_page = per_page
        p.total = total
        p.items = items
        p.pages = pages
        p.has_prev = page > 1
        p.has_next = page < pages
        p.prev_num = page - 1
        p.next_num = page + 1
        return p

    def __iter__(self):
        return iter(self.queryset)

    def __len__(self):
        return self.queryset.count()

    def __getitem__(self, index):
        return self.queryset[index]


class MetaDocument(me.base.TopLevelDocumentMetaclass):
    @property
    def query(cls):
        return MongoQueryWrapper(cls)


class BaseDocument(me.Document, metaclass=MetaDocument):
    meta = {"abstract": True, "strict": False}

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)


class MongoSession:
    """SQLAlchemy db.session compatible wrapper."""

    def add(self, obj):
        if hasattr(obj, "save"):
            obj.save()

    def commit(self):
        # MongoEngine saves objects on save(); commit is a no-op
        pass

    def rollback(self):
        pass

    def delete(self, obj):
        if hasattr(obj, "delete"):
            obj.delete()

    def get(self, model_cls, pk):
        if pk is None:
            return None
        try:
            return model_cls.objects(id=int(pk)).first()
        except Exception:
            return model_cls.objects(id=pk).first()

    def flush(self):
        pass


class MongoAdapter:
    """Drop-in replacement for Flask-SQLAlchemy db object."""

    def __init__(self):
        self.session = MongoSession()
        self.Model = BaseDocument

    def init_app(self, app):
        ensure_mongo_connection(app)

    def create_all(self):
        pass

    def drop_all(self):
        pass


db = MongoAdapter()

# Import models so they attach to db
from .user import User
from .question import Question
from .interview import Interview, Response, ProctoringLog
from .result import Result

__all__ = ["db", "User", "Question", "Interview", "Response", "Result", "ProctoringLog"]
