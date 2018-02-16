from django import forms

class UploadFileForm(forms.Form):
    title = forms.CharField(max_length=50)
    file = forms.FileField()

    # determine if the file is in a form recognizable by rdkit
    def is_valid_format(self):
        from rdkit import Chem
        import os
        #print(self.title)
        print(self.file)
        return True







