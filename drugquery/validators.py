# import openbabel
import os
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.conf import settings


def validate_upload_format(infile_object):
    import pybel

    # determine format of the input file
    filename, file_extension = os.path.splitext(infile_object.name)
    file_format = file_extension.strip('.').lower()

    if file_format not in pybel.informats.keys():
        raise ValidationError(
            _('.%(informat)s is not a file format recognized by Open Babel'),
            params={'informat': file_format},
        )

    # try to read the input file with pybel
    else:
        infile_contents = infile_object._file.read().decode("utf-8")  # have to convert from byte string to string
        try:
            mol = pybel.readstring(file_format, infile_contents)
        except OSError:
            raise ValidationError(
                _('The contents of %(infile)s cannot be recognized by Open Babel. Please double-check your input.'),
                params={'infile': infile_object.name},
            )

def validate_upload_size(infile_object):
    """
    2.5 MB - 2621440
    5 MB - 5242880
    10 MB - 10485760
    20 MB - 20971520
    50 MB - 5242880
    100 MB - 104857600
    250 MB - 214958080
    500 MB - 429916160
    """
    max_size = 2621440
    upload_size = infile_object._file._size
    if upload_size > max_size:
        raise ValidationError(
            _('File exceeds the maximum upload size of 2.5 MB'),
            params={'infile': infile_object.name},
        )
