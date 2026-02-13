from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    path('api/tab/calls/', views.tab_calls, name='tab_calls'),
    path('api/tab/settings/', views.tab_settings, name='tab_settings'),
    path('api/tab/schedule/', views.tab_schedule, name='tab_schedule'),
    path('api/tab/notes/', views.tab_notes, name='tab_notes'),
    path('api/tab/tracking/', views.tab_tracking, name='tab_tracking'),

    path('api/calls/', views.get_calls, name='get_calls'),
    path('api/calls/add/', views.add_call, name='add_call'),
    path('api/calls/update/', views.update_call_time, name='update_call_time'),
    path('api/calls/adjust/', views.adjust_call_time, name='adjust_call_time'),
    path('api/calls/delete/', views.delete_calls, name='delete_calls'),
    path('api/calls/clear_all/', views.clear_all_records, name='clear_all_records'),
    path('api/calls/postpone/', views.postpone_call, name='postpone_call'),
    path('api/calls/complete/', views.complete_call, name='complete_call'),  # новый маршрут
    path('api/calls/update_comment/', views.update_call_comment, name='update_call_comment'),
    path('api/calls/update_phone/', views.update_call_phone, name='update_call_phone'),

    path('api/tracking/', views.get_tracking, name='get_tracking'),
    path('api/tracking/add/', views.add_tracking, name='add_tracking'),
    path('api/tracking/delete/', views.delete_tracking, name='delete_tracking'),

    path('api/schedule/', views.get_schedule_data, name='get_schedule'),
    path('api/tasks/add/', views.add_task, name='add_task'),
    path('api/tasks/toggle/', views.toggle_task, name='toggle_task'),
    path('api/tasks/delete/', views.delete_task, name='delete_task'),

    path('api/note/', views.get_note, name='get_note'),
    path('api/note/save/', views.save_note, name='save_note'),

    path('api/settings/', views.get_settings, name='get_settings'),
    path('api/settings/save/', views.save_settings, name='save_settings'),
    path('api/settings/reset/', views.reset_settings, name='reset_settings'),

    path('api/notifications/', views.get_notifications, name='get_notifications'),

    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('admin-panel/add-user/', views.admin_add_user, name='admin_add_user'),
    path('admin-panel/delete-user/', views.admin_delete_user, name='admin_delete_user'),

    path('help/', views.help_index, name='help_index'),
    path('help-admin/', views.admin_help_topics, name='admin_help_topics'),
    path('help-admin/add_topic/', views.admin_add_topic, name='admin_add_topic'),
    path('help-admin/edit_topic/', views.admin_edit_topic, name='admin_edit_topic'),
    path('help-admin/delete_topic/', views.admin_delete_topic, name='admin_delete_topic'),
    path('help-admin/add_tab/', views.admin_add_tab, name='admin_add_tab'),
    path('help-admin/edit_tab/', views.admin_edit_tab, name='admin_edit_tab'),
    path('help-admin/delete_tab/', views.admin_delete_tab, name='admin_delete_tab'),
]