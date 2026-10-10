from django.urls import path
from . import views
urlpatterns = [
    path('learn/', views.learning_guide, name='learning_guide'),
    path('account/settings/', views.account_settings, name='account_settings'),
    path('api/account/preferences/', views.save_preferences),
    path('', views.home, name='home'), path('problems/<slug:slug>/', views.problem_page, name='problem'),
    path('api/questions/', views.question_list), path('api/questions/<slug:slug>/', views.question_detail),
    path('api/progress/', views.progress), path('api/progress/delete/', views.delete_progress),
    path('api/questions/<slug:slug>/draft/', views.save_draft), path('api/questions/<slug:slug>/run/', views.run_query),
    path('api/questions/<slug:slug>/solution/', views.reveal_solution),
]
