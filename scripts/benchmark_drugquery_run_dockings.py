#!/home/drugq/anaconda3/bin/python

# Python script running continually on the DrugQuery backend that performs the docking.
# Runs one job at a time. When a job is complete, checks the database for
# the most recent queued job and runs it

IN_DEVELOPMENT = False
DEBUG = True

import sys
import os
import time
from operator import attrgetter
import glob
from submit_smina import submit_smina_job, run_smina_job

# a setup script found in the __init__.py file of the drugquery_dev directory
# this will allow us to interface with the database
sys.path.append("..")
from drugquery_dev import setup

setup()
from drugquery.models import Job, Pocket, Compound, Docking
from django.conf import settings
from django.core.files import File
from django.core.mail import send_mail
from django.core.urlresolvers import reverse


# log file to record when new job are submitted
log_dir = os.path.join(settings.BASE_DIR, 'logs')
queue_log_file = os.path.join(log_dir, 'drugquery_queue_log.txt')

# a Timer class to profile our code
import time

class Timer:
    def __enter__(self):
        self.start = time.clock()
        return self

    def __exit__(self, *args):
        self.end = time.clock()
        self.interval = self.end - self.start


# returns the job currently running
def get_current_job(all_jobs):
    try:
        job = Job.objects.get(status='R')
    except Job.DoesNotExist:
        job = None
    return job


# returns the queued Job object that was submitted first
def get_new_job_to_run(all_jobs):
    return min(all_jobs, key=attrgetter('datetime'))


# submits one docking to the server queue
def submit_docking(compound, pocket):
    if IN_DEVELOPMENT:
        run_smina_job(compound, pocket)
    else:
        submit_smina_job(compound, pocket, log_dir)


# runs a DrugQuery multi-target docking job
def run_job(job):
    for pocket in job.compound.get_undocked_pockets():  # for pocket in Pocket.objects.all():
        submit_docking(job.compound, pocket)
    job.status = 'R'
    job.save()


# looks in the tmp directory for new smina output that has been generated
def collect_smina_output(current_job):
    cpd_name = current_job.compound.get_name()
    # if DEBUG: print('checking for: ', settings.TMP_ROOT + '/' + cpd_name + '*.sdf')
    new_output = glob.glob(settings.TMP_ROOT + '/' + cpd_name + '*.sdf')
    return new_output


# parses an output smina SDF file and returns the top docking score
def get_top_docking_score(docking_file):
    docking_info = open(docking_file)
    lines = docking_info.readlines()
    docking_info.close()
    top_score_index = lines.index('> <minimizedAffinity>\n') + 1
    top_score = float(lines[top_score_index])
    return top_score


# updates the docking / compound counters on all database models
# when the docking job is complete
def updatedb(compound):
    all_docked_pockets = compound.get_docked_pockets()
    all_docked_targets = { pocket.target for pocket in all_docked_pockets }
    all_docked_pdbs = { target.pdb for target in all_docked_targets }
    all_docked_genes = { pdb.gene for pdb in all_docked_pdbs }

    for pocket in all_docked_pockets:
        # we increment the compound when we create the docking object
        # compound.num_docked_pockets += 1
        pocket.num_compounds += 1
        pocket.num_dockings += 1
        pocket.save()

    for target in all_docked_targets:
        compound.num_docked_targets += 1
        target.num_compounds += 1
        target.num_dockings += target.num_pockets
        target.save()

    for pdb in all_docked_pdbs:
        compound.num_docked_pdbs += 1
        pdb.num_compounds += 1
        pdb.num_dockings += pdb.num_pockets
        pdb.save()

    for gene in all_docked_genes:
        compound.num_docked_genes += 1
        gene.num_compounds += 1
        gene.num_dockings += gene.num_pockets
        gene.save

    compound.save(recount=False)


# function to update database models' docking records when a new docking is created
def update_targets(pocket):
    target = pocket.target
    pdb = target.pdb
    gene = pdb.gene

    pocket.num_dockings += 1
    target.num_dockings += 1
    pdb.num_dockings += 1
    gene.num_dockings += 1

    pocket.save()
    target.save()
    pdb.save()
    gene.save()

# function to update parent compound's docking records when a new docking is created
# also updates the unique compound records of the database models
def update_compound(compound, pocket):
    target = pocket.target
    pdb = target.pdb
    gene = pdb.gene

    compound.num_docked_pockets += 1
    pocket.num_compounds += 1
    pocket.save()

    cpd_targets = set(compound.get_docked_targets())
    if target not in cpd_targets:
        compound.num_docked_targets += 1
        target.num_compounds += 1
        target.save()

        cpd_pdbs = set([t.pdb for t in cpd_targets])
        if pdb not in cpd_pdbs:
            compound.num_docked_pdbs += 1
            pdb.num_compounds += 1
            pdb.save()

            cpd_genes = set([p.gene for p in cpd_pdbs])
            if gene not in cpd_genes:
                compound.num_docked_genes += 1
                gene.num_compounds += 1
                gene.save()

    compound.save(recount=False)


# check if newly created docking object set a new top score
# for the compound
def check_new_top_score(docking):
    compound = docking.compound
    top_score = docking.top_score
    new_top_score = False

    if not compound.best_docking:
        new_top_score = True
    else:
        if top_score < compound.best_docking.top_score:  # more negative is better
            new_top_score = True

    # if we set a new record, save it
    if new_top_score:
        compound.best_docking = docking
        compound.best_pocket = docking.pocket
        compound.best_target = docking.pocket.target
        compound.best_pdb = docking.pocket.target.pdb
        compound.best_gene = docking.pocket.target.pdb.gene
        compound.save(recount=False)



# create a Docking object from smina output file and save it to the database,
# then delete the smina output file
def create_docking_object(outfile):
    # determine the relevant Docking object info from the filename
    # IMPORTANT: expects a basename like: compound_1_ABL1_1BBZ_chain_A_pocket_2
    basename = os.path.splitext(os.path.basename(outfile))[0]
    [cpd, cpdID, gene, pdb, chain, chainID, pocket, pocketID] = basename.split('_')

    print('Creating new docking from {}'.format(os.path.basename(outfile)))

    # identify the corresponding Compound and Pocket objects and the top score of the docking
    with Timer() as t:
        compound = Compound.objects.get(id=cpdID)
        pocket_name = gene + '_' + pdb + '_chain_' + chainID + '_pocket_' + pocketID
        pocket = Pocket.objects.get(name=pocket_name)
        top_score = get_top_docking_score(outfile)
    print('identifying Compound, Pocket, and top_score took {:.3f} sec.'.format(t.interval))


    # # update genes / pdbs / targets / pockets docking records
    # with Timer() as t:
    #     update_targets(pocket)
    # print('update_targets(pocket) took {:.3f} sec.'.format(t.interval))


    # # update the parent compound's docking records
    # with Timer() as t:
    #     update_compound(compound, pocket)
    # print('update_compound(compound, pocket) took {:.3f} sec.'.format(t.interval))


    # create the new Docking object
    with Timer() as t:
        docking = Docking()
        docking.compound = compound
        docking.pocket = pocket
        docking.top_score = top_score
        new_docking_file_path = os.path.basename(outfile)
        new_docking_file = File(open(outfile))
        docking.docking_file.save(new_docking_file_path, new_docking_file, save=True)
        docking.save()
    print('creating and saving new docking object took {:.3f} sec.'.format(t.interval))

    # increment the compound docking counter
    compound.num_docked_pockets += 1
    compound.save(recount=False)


    # check to see if we set a new top docking score for this cpd
    with Timer() as t:
        check_new_top_score(docking)
    print('check_new_top_score(docking) took {:.3f} sec.'.format(t.interval))


    # remove the file from TMP_ROOT so we do not double count it
    with Timer() as t:
        os.remove(outfile)
    print('removing original smina outfile took {:.3f} sec.'.format(t.interval))



####        MAIN            ####

# check for new jobs to run and update the status of completed jobs

# count pockets outside loop, so we don't have to do it each time.
# THIS MEANS WE HAVE TO RESTART THIS SCRIPT WHENEVER WE ADD NEW POCKETS
# TO THE DATABASE
total_num_pockets = len(Pocket.objects.all())


while True:
    all_jobs = Job.objects.all()
    current_job = get_current_job(all_jobs)

    # if no job is running, run a queued job FIFO style
    if not current_job:
        queued_jobs = all_jobs.filter(status='Q')

        if not queued_jobs:  # no jobs in the queue
            if DEBUG: print('PASSING')
            pass

        else:
            new_job = get_new_job_to_run(queued_jobs)
            run_job(new_job)

            # record the time of the job submission in the queue_log
            queue_log = open(queue_log_file, 'a')
            queue_log.write(time.strftime("%a, %d %b %Y %H:%M:%S") + '\t--\tsubmitted ' + str(new_job) + '\n')
            queue_log.close()

    # if a job is running, check if it is complete
    else:
        if DEBUG:
            print('\nThere is a job running now: ', current_job)
            print('Checking if this job is finished...\n')

        # if the job is not finished (i.e. if there are more targets for
        # this Job's Compound to dock against), then see if there are new
        # smina output files to process

        with Timer() as t:
            docked_pockets = current_job.compound.get_docked_pockets()
        print('current_job.compound.get_docked_pockets() took %.03f sec.' % t.interval)

        with Timer() as t:
            num_docked_pockets = current_job.compound.num_docked_pockets
        print('current_job.compound.num_docked_pockets took %.03f sec.' % t.interval)

        if len(docked_pockets) == num_docked_pockets:
            print('The two pocket counts are equal: {}\t{}'.format(len(docked_pockets), num_docked_pockets))
        else:
            print('The two pocket counts are NOT equal: {}\t{}'.format(len(docked_pockets), num_docked_pockets))


        if not len(docked_pockets) == total_num_pockets:
            if DEBUG:
                print('Job is not finished... creating docking objects from smina output files')
                # print(str(current_job.compound) + ' has already been docked against:')
                # for pocket in docked_pockets:
                #     print(pocket)
                # print('\n')

            with Timer() as t:
                new_smina_output = collect_smina_output(current_job)
            print('collect_smina_output(current_job) took %.03f sec.' % t.interval)


            if DEBUG:
                # print('Checking the tmp directory for new smina output')
                print('Found: {} new smina output files'.format(len(new_smina_output)))

            # create docking objects from the outfiles
            with Timer() as t2:
                nd = 0

                for outfile in new_smina_output:
                    if os.path.getsize(outfile) > 0:  # make sure file isn't empty

                        # trackers
                        nd += 1

                        with Timer() as t:
                            create_docking_object(outfile)
                        print('create_docking_object(outfile) took %.03f sec.' % t.interval)

                        # delete the PBS output and error files
                        with Timer() as t:
                            job_name = os.path.splitext(os.path.basename(outfile))[0]
                            pbs_files = glob.glob(log_dir + '/' + job_name + '*')
                            for f in pbs_files:
                                os.remove(f)
                        print('removing PBS output and error files took %.03f sec.' % t.interval)


            print('\nTotal time to create {} dockings:\t\t{} sec.'.format(nd, t2.interval))




        # if the job is finished
        else:
            # compile the compound docking scores
            if DEBUG: print('Job is complete! Compiling docking scores...\n')

            with Timer() as t:
                updatedb(current_job.compound)
            print('updatedb took %.03f sec.' % t.interval)


            with Timer() as t:
                current_job.compound.compile_scores()
            print('current_job.compound.compile_scores() took %.03f sec.' % t.interval)


            with Timer() as t:
                # send an email to whoever submitted the job
                if DEBUG: print('Sending results via email...\n')
                subject = 'DrugQuery job complete'
                domain = 'http://drugquery.csb.pitt.edu'
                result_url = domain + reverse('drugquery:compound_detail', kwargs={'pk': current_job.compound.pk})
                message = 'The results of your DrugQuery docking job can be found here: ' + result_url
                from_email = 'noreply@drugquery.pitt.edu'
                to_email = current_job.email

                send_mail(
                    subject,
                    message,
                    from_email,
                    [to_email],
                    fail_silently=False
                )
            print('Sending job completion email took %.03f sec.' % t.interval)


            with Timer() as t:
                # change the job status in the queue
                if DEBUG: print('Changing job status to \'C\'\n')
                current_job.status = 'C'
                current_job.save()
            print('Changing job status in queue took %.03f sec.' % t.interval)

    time.sleep(3)
