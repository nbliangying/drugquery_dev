'''
This script creates and saves database objects corresponding the
protein targets that DrugQuery will dock to. Input will be the a directory
containing all the targets you wish to upload, stored using the standard
DrugQuery target organization architecture:

Targets/
    ABL1/
        representative_gene_models/
            ABL1_1BBZ_A_iso/
                ABL1_1BBZ_A_iso.pdb
                ABL1_1BBZ_A_iso_cluster_0.pdb
                ...
            ...
        ...
    BRAF/
        ...
    FKBP1A/
        ...
    ...
'''

import sys
sys.path.append("..")

# a setup script found in the __init__.py file of the drugquery_dev directory
# this will allow us to interface with the database
from drugquery_dev import setup
setup()

import os
import glob
from drugquery.models import Gene, Pdb, Target, Pocket
from django.core.files import File
import argparse

# initialize argument parser
parser = argparse.ArgumentParser(description="Load DrugQuery target and pocket PDB files into the server database")
input_format_specifications = '''Path to the directory containing the genes you would like to populate the database with.
                              Expects that this directory is structured like: genes_dir/gene/representative_gene_models/
                              model/model.pdb, model_cluster_0.pdb, ...'''
parser.add_argument("genes_dir", type=str, help=input_format_specifications)
args = parser.parse_args()

# loop through all the representative structures
for target_dir in glob.glob(args.genes_dir + '/*/representative_gene_models/*'):
    if os.path.isdir(target_dir):

        # here expecting a target_dir named like: <gene>_<pdb>_<chain>_iso
        [target_gene, target_pdb, target_chain] = target_dir.split('/')[-1].split('_')[:3]
        target_name = target_gene + '_' + target_pdb + '_chain_' + target_chain

        # check if the gene is in the database. if not, create it
        try:
            gene = Gene.objects.get(name=target_gene)
        except Gene.DoesNotExist:
            print('Creating database entry for Gene: ', target_gene)
            gene = Gene(name=target_gene)
            gene.save()

        # check if the pdb is in the database. if not, create it
        try:
            pdb = gene.pdb_set.get(pdb_id=target_pdb)
        except Pdb.DoesNotExist:
            print('Creating database entry for Pdb: ', target_gene + '_' + target_pdb)
            pdb = gene.pdb_set.create(pdb_id=target_pdb)

        # check if the target is in the database. if not, create it
        try:
            target = pdb.target_set.get(chain=target_chain)
        except Target.DoesNotExist:
            print('Creating database entry for Target: ', target_name)

            # create a django File object from the actual target pdb file
            target_path = target_dir + '/' + target_dir.split('/')[-1] + '.pdb'
            target_pdb_file = File(open(target_path))

            # create the new Target object
            target = Target()
            target.pdb = pdb
            target.chain = target_chain
            # define the relative path to store the target file on the server inside MEDIA_ROOT
            new_target_file_path = target_name + '.pdb'
            target.target_file.save(new_target_file_path, target_pdb_file, save=True)
            target.save()


        ###             INDENT THIS    ?             ###

        # now we have to load in the docking sites associated with this target
        target_pocket_file_paths = glob.glob(target_dir + '/*cluster*')
        for target_pocket_file_path in target_pocket_file_paths:
            # extract the pocket number from the filename
            # assumes a naming convention like: NR3C1_4HN5_B_iso_cluster_3.pdb
            pocket_num = os.path.basename(os.path.splitext(target_pocket_file_path)[0]).split('_')[-1]

            # check if the pocket is in the database. if not, create it
            try:
                pocket = target.pocket_set.get(pocket_number=pocket_num)
            except Pocket.DoesNotExist:
                pocket_name = target_name + "_pocket_" + pocket_num
                print('Creating database entry for Pocket: ', pocket_name)

                # create a django File object for the actual Pocket pdb file
                pocket_pdb_file = File(open(target_pocket_file_path))

                # create a new Pocket object
                pocket = Pocket()
                pocket.target = target
                pocket.pocket_number = pocket_num
                # define the relative path to store the pocket file on the server inside MEDIA_ROOT
                new_pocket_file_path = pocket_name + '.pdb'
                pocket.pocket_file.save(new_pocket_file_path, pocket_pdb_file, save=True)
                pocket.save()













