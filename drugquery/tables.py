from django_tables2 import tables
from .models import Gene, Pdb, Target, Pocket, Compound, Docking , Upload, Job

class CompoundTable(tables.Table):
    class Meta:
        model = Compound

class DockingTable(tables.Table):
    class Meta:
        model = Docking
        attrs = {'class' : 'table'}