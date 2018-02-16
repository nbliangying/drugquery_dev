import sys
import os
import subprocess as sp

# a setup script found in the __init__.py file of the drugquery_dev directory
# this will allow us to interface with the database
sys.path.append("..")
from drugquery_dev import setup
setup()
from drugquery.models import Job, Pocket
from django.conf import settings


def submit_smina_job(compound, pocket, log_dir):

    # FOR ACTUAL IMPLEMENTATION - USE THE UBUNTU QSUB SYSTEM
    template = '''#!/bin/bash
#PBS -N {}
#PBS -q batch
#PBS -l nodes=1:ppn=1
#PBS -l walltime=14:00:00:00
#PBS -o {}
#PBS -e {}

/usr/local/bin/smina --cpu 1 -r {} -l {} -o {} --autobox_ligand {} 

echo \"Code execution ended at: `date`\"
echo \"---------------------------------------------------------------------------------\"
echo \" \"
'''

    job_name = compound.get_name() + '_' + pocket.name
    outfile_name = job_name + '.sdf'
    outlog_name = job_name + '.out' # the PBS output file from job submission
    errlog_name = job_name + '.err' # the PBS error file from job submission
    outfile_path = os.path.join(settings.TMP_ROOT, outfile_name) # the output SDF file
    outlog_path = os.path.join(log_dir, outlog_name)
    errlog_path = os.path.join(log_dir, errlog_name)

    args = [job_name,
            outlog_path,
            errlog_path,
            pocket.target.target_file.path,
            compound.compound_sdf_file.path,
            outfile_path,
            pocket.pocket_file.path,
           ]

    job_script = template.format(*args)
    job_file = job_name + '.pbs'
    open(job_file, 'w').write(job_script)
    cmd = 'qsub ' + job_file
    try:
        sp.call(cmd, shell=True)
    finally:
        os.remove(job_file)
        return True

def run_smina_job(compound, pocket):
    # THIS SUCKS BC SMINA KEEPS CRASHING

    outfile_name = compound.get_name() + '_' + pocket.name + '.sdf'
    outfile_path = os.path.join(settings.TMP_ROOT, outfile_name)

    smina_cmd = '/Users/Nico/local/smina.osx -r ' \
                + pocket.target.target_file.path + ' -l ' + compound.compound_sdf_file.path \
                + ' -o ' + outfile_path + ' --autobox_ligand ' + pocket.pocket_file.path + '> foo.txt 2>&1'

    print('\nRUNNING: ' + smina_cmd + '\n')
    smina_out = sp.check_output(smina_cmd, shell=True)
    return True
