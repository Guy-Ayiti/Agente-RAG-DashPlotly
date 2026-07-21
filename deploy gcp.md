# (0)
gcloud init 

# (1)
gcloud artifacts repositories create dashboard-rag-repositorio --repository-format docker --project datapath-aiengineer --location us-central1

# (2)
gcloud builds submit --tag us-central1-docker.pkg.dev/datapath-aiengineer/dashboard-rag-repositorio/dashboard-rag-imagen

#  If it gives the following error :
# ERROR: (gcloud.builds.submit) PERMISSION_DENIED: The caller does not have permission.
# This command is authenticated as guy3hil@gmail.com which is the active account specified by the [core/account] property
# ==>
gcloud auth configure-docker us-central1

## gcloud run services replace service.yaml --region us-central1 --project datapath-aiengineer

# substitute for : gcloud run deploy
# gcloud run deploy --image us-central1-docker.pkg.dev/datapath-aiengineer/langgraph-texttosql-repositorio/imagendocker-streamlit-texttosql

# (3.1)
gcloud run deploy dashboard-rag-servicio --image datapath-aiengineer/dashboard-rag-repositorio/dashboard-rag-imagen --region us-central1

# ====> or run as the following : 

# (3.2)
gcloud run deploy dashboard-rag-servicio --region us-central1 --image us-central1-docker.pkg.dev/datapath-aiengineer/dashboard-rag-repositorio/dashboard-rag-imagen

####  Check for Hidden Crashes (Missing Dependencies)
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --limit=10
