from django.contrib import admin
from .models import Gene, Pdb, Target, Pocket, Compound, Docking, Upload, Job

# Register your models here.
admin.site.register(Gene)
admin.site.register(Pdb)
admin.site.register(Target)
admin.site.register(Pocket)
admin.site.register(Compound)
admin.site.register(Docking)
admin.site.register(Upload)
admin.site.register(Job)
