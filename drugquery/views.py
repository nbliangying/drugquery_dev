from django.http import HttpResponse, HttpResponseRedirect # this is the most basic type of response
from django.shortcuts import render, get_object_or_404, redirect
from .models import Gene, Pdb, Target, Pocket, Compound, Docking , Upload, Job
from django.views import generic
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.core.urlresolvers import reverse
from itertools import groupby
from django.conf import settings
import os
import datetime
import shutil
from django.core.files import File
import pybel
from .extra import get_similar_cpds


# the main landing page
def index(request):
    num_genes = len(Gene.objects.all())
    num_structs = len(Target.objects.all())
    num_pockets = len(Pocket.objects.all())
    num_cpds = len(Compound.objects.all())
    context = {'num_genes': num_genes,
               'num_structs': num_structs,
               'num_pockets': num_pockets,
               'num_cpds': num_cpds,
               }
    print(num_genes)
    return render(request, 'drugquery/index.html', context)

class UploadCompound(CreateView):
    model = Upload
    fields = ['upload_file', 'email']
    # passes these fields to a new html template called BY DEFAULT upload_form.html


# Once we create a new upload object, we get redirected here
# It's the "absolute_url" of the Upload class
# this view creates a compound object from the upload or redirects to an existing upload
def validateUpload(request, upload_id):
    upload = get_object_or_404(Upload, pk=upload_id)

    # make a new compound if this is a unique smiles
    if upload.is_unique():
        cpd = Compound()
        cpd.smiles = upload.smiles
        cpd.save()
        cpd.initialize() # create the sdf + image files

        # create the job to dock the compound
        job = cpd.job_set.create(email=upload.email)

        return redirect(reverse('drugquery:compound_detail', kwargs={'pk': cpd.pk}))
    else:
        cpd = Compound.objects.get(pk=upload.get_redundant_compound_pk())

        # create the job to perform any missing dockings
        job = cpd.job_set.create(email=upload.email)

        return redirect(reverse('drugquery:compound_detail', kwargs={'pk': cpd.pk}))


class UploadIndexView(generic.ListView):
    template_name = 'drugquery/uploads.html'
    context_object_name = "all_uploads"

    def get_queryset(self):
        return Upload.objects.all()


class CompoundIndexView(generic.ListView):
    template_name = 'drugquery/compounds.html'
    context_object_name = "all_compounds"
    paginate_by = 5

    def get_queryset(self):
        return Compound.objects.all()


class TargetIndexView(generic.ListView):
    template_name = 'drugquery/targets.html'
    context_object_name = "all_targets"

    def get_queryset(self):
        return Target.objects.all()


class JobIndexView(generic.ListView):
    template_name = 'drugquery/queue.html'
    context_object_name = 'all_jobs'
    paginate_by = 50

    def get_queryset(self):
        sorted_jobs = sorted(Job.objects.all(), reverse = True, key = lambda x: x.datetime)
        return sorted_jobs


class CompoundDetailView(generic.DetailView):
    # a generic.DetailView expects a primary key, in this case the pk of an compound
    model = Compound
    context_object_name = "compound" # the default is the lowercase model name
    template_name = 'drugquery/compound_detail.html'


class GeneIndexView(generic.ListView):
    template_name = 'drugquery/genes.html'
    context_object_name = 'all_genes'
    paginate_by = 100

    def get_queryset(self):
        sorted_genes = sorted(Gene.objects.all(), key = lambda g: g.name)
        return sorted_genes


def geneDetailView(request, gene_name):
    gene = get_object_or_404(Gene, name=gene_name)
    return render(request, 'drugquery/gene_detail.html', {'gene': gene})


def about(request):
    return render(request, 'drugquery/about.html')


def downloadScores(request,pk):
    compound = Compound.objects.get(pk=pk)
    scoreFile = open(compound.score_file.path)
    response = HttpResponse(scoreFile, content_type='application/force-download')
    response['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(compound.score_file.name)
    return response


def downloadStructure(request, pk):
    compound = Compound.objects.get(pk=pk)
    structureFile = open(compound.compound_sdf_file.path)
    response = HttpResponse(structureFile, content_type='application/force-download')
    response['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(compound.compound_sdf_file.name)
    return response


def downloadDockings(request, pk):

    compound = Compound.objects.get(pk=pk)

    # retrieve docking objects and groupby target object
    docking_ids = request.POST.getlist('checks[]')
    dockings = [ Docking.objects.get(pk=docking_id) for docking_id in docking_ids ]
    target_labelled_dockings = [ (docking.pocket.target, docking) for docking in dockings]
    target_labelled_dockings.sort(key=lambda d: d[0].name)

    # create a directory to store the user-selected results
    if not os.path.exists(settings.TMP_ROOT): os.makedirs(settings.TMP_ROOT)
    timestamp = '{:%Y-%m-%d__%H.%M.%S}'.format(datetime.datetime.now())
    result_dir_name = compound.get_name() + '__' + timestamp
    result_dir = os.path.join(settings.TMP_ROOT, result_dir_name)
    strdir = str(result_dir)
    os.mkdir(strdir)

    # organize results by target subdir
    for target, dockings in groupby(target_labelled_dockings, lambda x: x[0]):
        target_result_dir = os.path.join(result_dir, target.name)
        os.mkdir(target_result_dir)
        shutil.copy2(target.target_file.path, target_result_dir)
        for target, docking in dockings:
            shutil.copy2(docking.docking_file.path, target_result_dir)

    # zip results and
    shutil.make_archive(result_dir, 'zip', result_dir)
    shutil.rmtree(result_dir)

    zipFile_name = result_dir + '.zip'
    resultFile = open(zipFile_name, 'rb')
    response = HttpResponse(resultFile, content_type='application/force-download')
    response['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(zipFile_name)
    return response


    #return redirect(reverse('drugquery:compound_detail', kwargs={'pk': pk}))


def redockCompound(request, pk):
    compound = Compound.objects.get(pk=pk)
    job = compound.job_set.create(email='none@none.com')
    return redirect(reverse('drugquery:compound_detail', kwargs={'pk': pk}))


def searchCompounds(request):

    context = {}
    smiles_query = request.GET.get('smiles_query')
    context['smiles_query'] = smiles_query

    # if the string is not a recognized file, return an error
    try:
        query_mol = pybel.readstring("smi", smiles_query)
    except OSError:
        error_message = "Error: query is not a valid SMILES string"
        context['error_message'] = error_message
        query_mol = None

    # look for similar molecules
    if query_mol:
        similar_cpds = get_similar_cpds(query_mol, Compound.objects.all())
        context['similar_cpds'] = similar_cpds
        print(similar_cpds)

    return render(request, 'drugquery/search_results.html', context)
