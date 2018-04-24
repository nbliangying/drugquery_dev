from django.conf.urls import url
from . import views
from django.conf import settings
from django.views.static import serve

# namespace the URLs
app_name = 'drugquery'

urlpatterns = [

    # drugquery/
    url(r'^$', views.index, name="index"),

    # drugquery/about
    url(r'^about$', views.about, name="about"),

    # drugquery/upload/
    url(r'^upload/$', views.UploadCompound.as_view(), name="upload"),

    # drugquery/upload/validate/<pk>/
    url(r'^upload/validate/(?P<upload_id>[0-9]+)/$', views.validateUpload, name="validate_upload"),

    # drugquery/uploads/
    url(r'^uploads/$', views.UploadIndexView.as_view(), name='uploads'),

    # drugquery/compounds/
    url(r'^compounds/$', views.CompoundIndexView.as_view(), name='compounds'),

    # drugquery/compounds/<pk>/
    # url(r'^compounds/(?P<pk>[0-9]+)/$', views.CompoundDetailView.as_view(), name="compound_detail"),
    url(r'^compounds/(?P<pk>[0-9]+)/$', views.compoundDetailView, name="compound_detail"),

    # drugquery/genes/<gene_name>
    url(r'^genes/(?P<gene_name>[A-Z0-9]+)/$', views.geneDetailView, name="gene_detail"),

    # drugquery/genes/
    url(r'^genes/$', views.GeneIndexView.as_view(), name="genes"),

    # drugquery/queue/
    url(r'^queue/$', views.JobIndexView.as_view(), name='queue'),

    ### URLS FOR DOWNLOADING RESULTS
    # drugquery/compounds/<pk>/download_all_dockings
    url(r'^compounds/(?P<pk>[0-9]+)/download_all_dockings/$', views.downloadAllDockings, name="download_all_dockings"),
    # drugquery/compounds/<pk>/download_top_dockings
    url(r'^compounds/(?P<pk>[0-9]+)/download_top_dockings/$', views.downloadTopDockings, name="download_top_dockings"),
    # drugquery/compounds/<pk>/download_structure
    url(r'^compounds/(?P<pk>[0-9]+)/download_structure/$', views.downloadStructure, name="download_structure"),
    # drugquery/compounds/<pk>/download_scores
    url(r'^compounds/(?P<pk>[0-9]+)/download_scores/$', views.downloadScores, name="download_scores"),

    ### URLS FOR SEARCHING
    # drugquery/compounds/search/
    url(r'^compounds/search/$', views.searchCompounds, name='search_compounds'),

    ### URLS FOR REDOCKING
    # drugquery/compounds/<pk>/redock
    url(r'^compounds/(?P<pk>[0-9]+)/redock/$', views.redockCompound, name="redock_cpd"),




]

# for the user to download files
# when we deploy we will want the apache server to do this not django
if settings.DEBUG:
    urlpatterns += [
        url(r'^download/(?P<path>.*)$', serve,
            {'document_root': settings.MEDIA_ROOT},
            name='download'),
    ]