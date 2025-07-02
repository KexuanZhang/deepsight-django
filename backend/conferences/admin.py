from django.contrib import admin
from .models import Venue, Instance, Publication, Session

admin.site.register(Venue)
admin.site.register(Instance)
admin.site.register(Publication)
admin.site.register(Session)
