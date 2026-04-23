from django.urls import path

from .views import timers_api

app_name = "discordtimerboard"

urlpatterns = [
    path("api/timers/", timers_api, name="timers_api"),
    path("timers/", timers_api, name="timers_api_short"),
]
