# App/views/__init__.py
from .user import user_views
from .index import index_views
from .auth import auth_views
from .admin import setup_admin
from .staffView import staff_views
from .adminView import admin_view
from .schedulingView import scheduling_api  # Import the API

# Combine all blueprints
views = [user_views, index_views, auth_views, staff_views, admin_view, scheduling_api]
blueprints = views