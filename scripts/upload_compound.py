'''
This is a script for command line submission of small molecules
to the DrugQuery server for docking.
'''

import sys
sys.path.append("..")

# a setup script found in the __init__.py file of the drugquery_dev directory
# this will allow us to interface with the database
from drugquery_dev import setup
setup()

import os
from drugquery.models import Upload, Compound
from django.core.files import File
import argparse

# initialize argument parser
parser = argparse.ArgumentParser(description="Upload a compound to the drugquery server for docking.")
parser.add_argument("cpd_file", type=str, help="Compound structure file. Accepts any OpenBabel format.")
args = parser.parse_args()

# create a django File object from the cpd file
cpd_file = File(open(args.cpd_file))

# create the new Target object
upload = Upload()
upload.upload_file.save(os.path.basename(args.cpd_file), cpd_file, save=True)
upload.email = 'npabon15@gmail.com'
upload.save()

# make a new compound if this is a unique smiles
if upload.is_unique():
    print('Upload is unique.', end = ' ')
    cpd = Compound()
    cpd.smiles = upload.smiles
    cpd.save()
    cpd.initialize() # create the sdf + image files

    # create the job to dock the compound
    job = cpd.job_set.create(email=upload.email)
    print('Creating job: ', job)

else:
    print('Upload is NOT unique.', end=' ')
    cpd = Compound.objects.get(pk=upload.get_redundant_compound_pk())

    # create the job to perform any missing dockings
    job = cpd.job_set.create(email=upload.email)
    print('Creating job: ', job)