from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('sync/', views.sync_tags, name='sync_tags'),
    path('start/', views.start_collector, name='start_collector'),
    path('stop/', views.stop_collector, name='stop_collector'),
    path('log/', views.view_log, name='view_log'),
    
    # API for AJAX
    path('api/snapshots/', views.api_get_snapshots, name='api_snapshots'),
    
    # Tag Configuration Files
    path('config/', views.tag_config_list, name='tag_config_list'),
    path('config/create/', views.create_tag_file, name='create_tag_file'),
    path('config/upload/', views.upload_tag_file, name='upload_tag_file'),
    path('config/edit/<str:filename>/', views.edit_tag_file, name='edit_tag_file'),
    path('config/delete/<str:filename>/', views.delete_tag_file, name='delete_tag_file'),
]
