from __future__ import unicode_literals
from django.db import models
from django.core.urlresolvers import reverse
from .validators import validate_upload_format, validate_upload_size
from django.core.files import File
from django.core.files.base import ContentFile
from django.conf import settings
import os
from operator import attrgetter
import pybel
from .extra import get_similar_cpds

# flatten a 2d list into a 1d list
def flatten(l_2d):
    l_1d = []
    for sublist in l_2d:
        for item in sublist:
            l_1d.append(item)
    return l_1d


class Gene(models.Model):
    name = models.CharField(max_length=20)
    num_pdbs = models.IntegerField(default=0)
    num_targets = models.IntegerField(default=0)
    num_pockets = models.IntegerField(default=0)
    num_dockings = models.IntegerField(default=0)
    num_compounds = models.IntegerField(default=0)

    def __str__(self):
        return self.name

    # # functions to return all the Pdb/Target/Pocket/Docking objects associated with this Gene
    def get_pdbs(self):
        return self.pdb_set.all()
    #
    def get_targets(self):
        return flatten([ pdb.target_set.all() for pdb in self.get_pdbs() ])
    #
    # def get_pockets(self):
    #     return flatten([ target.pocket_set.all() for target in self.get_targets() ])
    #
    # def get_dockings(self):
    #     return flatten([ pocket.docking_set.all() for pocket in self.get_pockets() ])
    #
    # def get_compounds(self):
    #     all_compounds = [ docking.compound for docking in self.get_dockings() ]
    #     unique_compounds = list(set(all_compounds))
    #     return unique_compounds
    #
    # # functions to return the number of Pdb/Target/Pocket/Docking/Compound objects associated with this gene
    # def num_pdbs(self):
    #     return len(self.get_pdbs())
    #
    # def num_targets(self):
    #     return len(self.get_targets())
    #
    # def num_pockets(self):
    #     return len(self.get_pockets())
    #
    # def num_dockings(self):
    #     return len(self.get_dockings())
    #
    # def num_compounds(self):
    #     return len(self.get_compounds())


class Pdb(models.Model):
    gene = models.ForeignKey(Gene, on_delete=models.CASCADE)
    pdb_id = models.CharField(max_length=10)
    name = models.CharField(max_length=31)
    num_targets = models.IntegerField(default=0)
    num_pockets = models.IntegerField(default=0)
    num_dockings = models.IntegerField(default=0)
    num_compounds = models.IntegerField(default=0)

    # define the name upon save
    def save(self, *args, **kwargs):
        if not self.name:
            self.name = self.gene.name + '_' + self.pdb_id
        super(Pdb, self).save(*args, **kwargs)

    def __str__(self):
        return self.name


class Target(models.Model):
    pdb = models.ForeignKey(Pdb, on_delete=models.CASCADE)
    chain = models.CharField(max_length=4)
    target_file = models.FileField(upload_to='targets')
    name = models.CharField(max_length=42)
    num_pockets = models.IntegerField(default=0)
    num_dockings = models.IntegerField(default=0)
    num_compounds = models.IntegerField(default=0)

    # define the name upon save
    def save(self, *args, **kwargs):
        if not self.name:
            self.name = self.pdb.name + '_chain_' + self.chain
        super(Target, self).save(*args, **kwargs)

    def __str__(self):
        return self.name


class Pocket(models.Model):
    target = models.ForeignKey(Target, on_delete=models.CASCADE)
    pocket_number = models.IntegerField()
    pocket_file = models.FileField(upload_to='pockets')
    name = models.CharField(max_length=52)
    num_dockings = models.IntegerField(default=0)
    num_compounds = models.IntegerField(default=0)

    # define the name upon save
    def save(self, *args, **kwargs):
        if not self.name:
            self.name = self.target.name + '_pocket_' + str(self.pocket_number)
        super(Pocket, self).save(*args, **kwargs)

    def __str__(self):
        return self.name


class Upload(models.Model):
    # actual file is stored in MEDIA_ROOT/uploads
    upload_file = models.FileField(validators=[validate_upload_size, validate_upload_format], upload_to='uploads')
    email = models.EmailField()
    smiles = models.CharField(max_length=500)

    # where to go when we create the model
    def get_absolute_url(self):
        return reverse('drugquery:validate_upload', kwargs={'upload_id': self.pk})

    def get_name(self):
        return 'upload_' + str(self.pk) + ' : ' + self.smiles

    def __str__(self):
        return self.get_name()

    # generate the canonical smiles representation (without Hydrogen)
    def get_smiles(self):
        filename, file_extension = os.path.splitext(self.upload_file.name)
        file_format = file_extension.strip('.').lower()
        self.upload_file.seek(0)
        upload_file_contents = self.upload_file.read().decode("utf-8")
        mol = pybel.readstring(file_format, upload_file_contents)
        mol.removeh()
        canonical_smi = mol.write(format="can").split()[0]
        return canonical_smi

    ## DEPRECATED since we switched from rdkit to pybel (Oct 2, 2017)
    # def get_smiles_rdkit(self):
    #     import os
    #     from rdkit import Chem
    #
    #     filename, file_extension = os.path.splitext(self.upload_file.name)
    #     informat = file_extension[1:]
    #
    #     # the model has not been saved to the database yet, which means the file has not
    #     # actually been saved on the server filesystem. As part of saving this object, we
    #     # need to access the file using RDKIT, but before the object is saved the upload_file
    #     # is not an actual file, which is a problem for RDKIT. To workaround this we have to
    #     # manually save the file to the server before RDKIT can access it and
    #     # the database save can occur
    #     self.upload_file.seek(0)
    #     upload_contents = self.upload_file.read().decode("utf-8")
    #     content = ContentFile(upload_contents)
    #     self.upload_file.save(self.upload_file.name, content, save=False)
    #
    #
    #     if informat.lower() == "smi":
    #         mol = Chem.MolFromSmiles(upload_contents)
    #     elif informat.lower() == "mol":
    #         mol = Chem.MolFromMolFile(self.upload_file.path)
    #     elif informat.lower() == "mol2":
    #         mol = Chem.MolFromMol2File(self.upload_file.path)
    #     else:
    #         mol = Chem.MolFromPDBFile(self.upload_file.path)
    #
    #     return Chem.MolToSmiles(mol, isomericSmiles=True)


    # redefine save function so we can save the smiles as an attribute instead
    # of having to call the smiles() function every time
    def save(self, *args, **kwargs):
        if not self.smiles:
            self.smiles = self.get_smiles()
        super(Upload, self).save(*args, **kwargs)


    # returns true if the upload represents a compound not currently in our database
    def is_unique(self):
        all_cpds = Compound.objects.all()
        cpd_smiles = [ cpd.smiles for cpd in all_cpds ]
        if self.smiles in cpd_smiles:
            return False
        else:
            return True

    # returns the pk of redundant compound in the list
    def get_redundant_compound_pk(self):
        all_cpds = Compound.objects.all()
        for cpd in all_cpds:
            if cpd.smiles == self.smiles:
                return cpd.pk



class Compound(models.Model):
    smiles = models.CharField(max_length=500)
    compound_sdf_file = models.FileField(upload_to='compounds')
    compound_img_file = models.FileField(upload_to='images')
    score_file = models.FileField(upload_to='scores')

    num_docked_genes = models.IntegerField(default=0)
    num_docked_pdbs = models.IntegerField(default=0)
    num_docked_targets = models.IntegerField(default=0)
    num_docked_pockets = models.IntegerField(default=0)

    best_gene = models.ForeignKey(Gene, null=True, on_delete=models.SET_NULL)
    best_pdb = models.ForeignKey(Pdb, null=True, on_delete=models.SET_NULL)
    best_target = models.ForeignKey(Target, null=True, on_delete=models.SET_NULL)
    best_pocket = models.ForeignKey(Pocket, null=True, on_delete=models.SET_NULL)
    best_docking = models.ForeignKey('Docking', related_name='+', null=True, on_delete=models.SET_NULL)


    # where to go when we create the model
    def get_absolute_url(self):
        return reverse('drugquery:compound_detail', kwargs={'pk': self.pk})

    def get_name(self):
        return 'compound_' + str(self.pk)

    def __str__(self):
        return self.get_name()

    # create the directories/files to store the compound information on the server
    def initialize(self):

        # make sure tmp directory exists to so we can store files before saving them to database
        if not os.path.exists(settings.TMP_ROOT): os.makedirs(settings.TMP_ROOT)

        mol = pybel.readstring("can", self.smiles)

        # generate a 2d image of the compound
        cpd_img_filename = self.get_name() + ".svg"
        img_file_contents = mol.write(format="svg", opt={"P": 200, "C": True, "d": True})
        cpd_img_file = ContentFile(img_file_contents)
        self.compound_img_file.save(cpd_img_filename, cpd_img_file)

        # generate a 3d sdf file
        cpd_sdf_filename = self.get_name() + ".sdf"
        mol.make3D()
        mol.localopt() # optimize coords
        mol.removeh()
        sdf_file_contents = mol.write(format="sdf")
        cpd_sdf_file = ContentFile(sdf_file_contents)
        self.compound_sdf_file.save(cpd_sdf_filename, cpd_sdf_file)

        self.save()

    # compiles a list of scores from all this compound's Dockings
    def compile_scores(self):

        # make sure tmp directory exists to so we can store files before saving them to database
        if not os.path.exists(settings.TMP_ROOT): os.makedirs(settings.TMP_ROOT)
        score_file_name = self.get_name() + '_scores.txt'
        tmp_score_file_path = os.path.join(settings.TMP_ROOT, score_file_name)
        tmp_score_file = open(tmp_score_file_path, 'w')

        # gene | pdb | chain | pocket | score
        template_line = "{0: <10}{1: <10}{2: <10}{3: <10}{4: <10}\n"
        header = template_line.format('Gene', 'PDB', 'Chain', 'Pocket', 'Score') + '\n'
        tmp_score_file.write(header)

        # write the docking scores to the tmp file
        sorted_dockings = sorted(self.docking_set.all(), key=lambda x: x.top_score)
        for d in sorted_dockings:
            line = template_line.format(
                d.pocket.target.pdb.gene.name,
                d.pocket.target.pdb.pdb_id,
                d.pocket.target.chain,
                d.pocket.pocket_number,
                d.top_score
            )
            tmp_score_file.write(line)
        tmp_score_file.close()

        # now save the file to the database
        score_file = File(open(tmp_score_file_path))
        self.score_file.save(score_file_name, score_file)
        # delete temporary file and save
        os.remove(tmp_score_file_path)
        self.save()



    # functions to tell you which / how many targets this cpd has been docked to
    def get_docked_pockets(self):
        cpd_dockings = self.docking_set.all()
        return [docking.pocket for docking in cpd_dockings]

    # returns a list of Pockets that have NOT been docked against
    def get_undocked_pockets(self):
        docked_pockets = self.get_docked_pockets()
        undocked_pockets = [ pocket for pocket in Pocket.objects.all() if pocket not in docked_pockets ]
        return undocked_pockets

    def get_num_undocked_pockets(self):
        return len(self.get_undocked_pockets())

    def get_docked_targets(self):
        docked_targets = [ pocket.target for pocket in self.get_docked_pockets() ]
        return list(set(docked_targets))

    def get_docked_pdbs(self):
        docked_pdbs = [ target.pdb for target in self.get_docked_targets() ]
        return list(set(docked_pdbs))

    def get_docked_genes(self):
        docked_genes = [ pdb.gene for pdb in self.get_docked_pdbs() ]
        return list(set(docked_genes))

    def get_num_docked_pockets(self):
        return len(self.get_docked_pockets())

    def get_num_docked_targets(self):
        return len(self.get_docked_targets())

    def get_num_docked_pdbs(self):
        return len(self.get_docked_pdbs())

    def get_num_docked_genes(self):
        return len(self.get_docked_genes())


    # functions return the docking/pocket/target/pdb/gene that produced the best docking score
    def get_best_docking(self):
        all_dockings = self.docking_set.all()
        try:
            best_docking = min(all_dockings, key=attrgetter('top_score'))
        except ValueError:
            best_docking = None
        return best_docking

    def get_best_pocket(self):
        try:
            best_pocket = self.get_best_docking().pocket
        except AttributeError:
            best_pocket = None
        return best_pocket

    def get_best_target(self):
        try:
            best_target  = self.get_best_pocket().target
        except AttributeError:
            best_target = None
        return best_target

    def get_best_pdb(self):
        try:
            best_pdb = self.get_best_target().pdb
        except AttributeError:
            best_pdb = None
        return best_pdb

    def get_best_gene(self):
        try:
            best_gene = self.get_best_pdb().gene
        except AttributeError:
            best_gene = None
        return best_gene

    # return the pybel molecule for a compound
    def get_pybel_mol(self):
        return pybel.readstring("can", self.smiles)

    # return a list of similar cpds
    def get_similar_compounds(self):
        return get_similar_cpds(self.get_pybel_mol(), Compound.objects.all())

    # return docking status of the compound
    def get_docking_status(self):
        jobs = self.job_set.all()
        job_statuses = [ j.status for j in jobs ]
        if 'R' in job_statuses:
            current_status = 'Running'
        elif 'Q' in job_statuses:
            current_status = 'Queued'
        elif 'E' in job_statuses:
            current_status = 'Error'
        else:
            current_status = 'Idle'
        return current_status


class Job(models.Model):
    datetime = models.DateTimeField(auto_now_add=True)
    compound = models.ForeignKey(Compound, on_delete=models.CASCADE)
    email = models.EmailField()

    # job status options
    QUEUED = 'Q'
    RUNNING = 'R'
    COMPLETE = 'C'
    ERROR = 'E'
    STATUS_CHOICES = (
        (QUEUED, 'Queued'),
        (RUNNING, 'Running'),
        (COMPLETE, 'Complete'),
        (ERROR, 'Error'),
    )
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default=QUEUED)

    def __str__(self):
        return self.status + ' : ' + self.compound.get_name() + ' - ' + str(self.datetime) + ' - ' + self.email


class Docking(models.Model):
    compound = models.ForeignKey(Compound, on_delete=models.CASCADE)
    pocket = models.ForeignKey(Pocket, on_delete=models.CASCADE)
    top_score = models.DecimalField(max_digits=8, decimal_places=5)
    docking_file = models.FileField(upload_to='dockings')

    def get_name(self):
        return self.compound.get_name() + self.pocket.name

    def __str__(self):
        return self.get_name() + ' : ' + str(self.top_score)

# Receive the pre_delete signal and delete the files associated with the model instance
from django.db.models.signals import pre_delete
from django.dispatch.dispatcher import receiver

@receiver(pre_delete, sender=Upload)
def upload_delete(sender, instance, **kwargs):
    # Pass false so FileField doesn't save the model.
    instance.upload_file.delete(False)

@receiver(pre_delete, sender=Compound)
def compound_delete(sender, instance, **kwargs):
    # Pass false so FileField doesn't save the model.
    instance.compound_sdf_file.delete(False)
    instance.compound_img_file.delete(False)

@receiver(pre_delete, sender=Target)
def target_delete(sender, instance, **kwargs):
    # Pass false so FileField doesn't save the model.
    instance.target_file.delete(False)

@receiver(pre_delete, sender=Pocket)
def pocket_delete(sender, instance, **kwargs):
    # Pass false so FileField doesn't save the model.
    instance.pocket_file.delete(False)

@receiver(pre_delete, sender=Docking)
def docking_delete(sender, instance, **kwargs):
    # Pass false so FileField doesn't save the model.
    instance.docking_file.delete(False)










