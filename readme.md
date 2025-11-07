To install requirements for the project
pip install -r requirements.txt


to run backend (make sure in backend directory) 
source venv/Scripts/activate
uvicorn app.main:app --reload --port 8000
to run ingest
python -m app.services.ingest_service

(venv) .../backend> python -m app.diagnostic_script

frontend
cd
npm install 
npm run dev