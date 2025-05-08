import os
import threading, mimetypes
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import requests, json, sqlite3
from sqlmodel import Field, Session, SQLModel, create_engine, select
from sqlalchemy import Column, JSON, func
from concurrent.futures import ThreadPoolExecutor, as_completed


# Pydantic models for request and query parameters
class ProjectRequest(BaseModel):
    project_id: str

class QueryParams(BaseModel):
    type: Optional[str] = None
    name: Optional[str] = None

# Define the SQLModel for iElements
class IElements(SQLModel, table=True):
    __tablename__ = "iElements" 
    id: str = Field(primary_key=True)
    type: str
    name: str
    uri: Optional[str] = None


    # These are dicts, so we use SQLAlchemy's JSON type
    metaData: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    pose: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    globalPose: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    boundingBox: Optional[dict] = Field(default=None, sa_column=Column(JSON))

  
    childrenIds: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))

    
    full_json: Optional[dict] = Field(default=None, sa_column=Column(JSON))

app = FastAPI()

download_lock = threading.Lock()
download_progress = {
            "status": "in_progress",
            "downloaded": 0,
            "total": 0
        }

# database setup
DATABASE_PATH = "sqlite:///project_cache.db"
engine = create_engine(DATABASE_PATH, echo=True, future=True)
SQLModel.metadata.create_all(engine)

# Dependency to get a session
def get_session():
    with Session(engine) as session:
        yield session



def fetch_token(project_id):
    url = "https://core.api.dev.holobuilder.eu/v3/auth/token"
    payload = {
        "scopes": ["user:project"],
        "data": {"projects": [{"id": project_id}]}
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()['data']['token']
    # Placeholder function to simulate token fetching

def intilaize_project(token, project_id):
    # Placeholder function to simulate project initialization
    headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json" 
    }   

    project_resp = requests.get(url= f"https://v2.project.api.dev.holobuilder.eu/v1/{project_id}/ielements", headers=headers).text
    
    # Handle the response
    data = json.loads(project_resp)
    return data

def save_sqlite(data: dict):
    # Placeholder function to simulate saving to SQLite
    with Session(engine) as session:
        for item in data['page']:
            i_element = IElements(
                id=item["id"],
                type=item["type"],
                name=item["name"],
                uri=item.get("uri"),
                metaData=item.get("metaData"),
                pose=item.get("pose"),
                globalPose=item.get("globalPose"),
                boundingBox=item.get("boundingBox"),
                childrenIds=item.get("childrenIds"),
                full_json=item
            )
            session.add(i_element)
        session.commit()

def download_file(url, index, total):
    try:
        print(f"📥 Downloading {index}/{total} → {url}",flush=True)
        response = requests.get(url, timeout=30)
        content_type = requests.head(url).headers.get('Content-Type')
        extension = mimetypes.guess_extension(content_type) or ''
        
        filename = url.split("/")[-1]
        if not filename.endswith(extension):
            filename += extension

        os.makedirs("downloads", exist_ok=True)
        filepath = os.path.join("downloads", filename)

        with open(filepath, "wb") as f:
            f.write(response.content)

        with download_lock:
            download_progress["downloaded"] += 1

    except Exception as e:
        print(f"Error downloading {url}: {e}")


def run_downloads(urls: List[str]):
    futures = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        for i, url in enumerate(urls):
            futures.append(executor.submit(download_file, url, i + 1, len(urls)))

        for future in as_completed(futures):
            try:
                future.result()  # triggers error if download_file raised

            except Exception as e:
                print(f"Error in future: {e}")

    with download_lock:
        download_progress["status"] = "Finished"

    return download_progress
    
@app.get("/")  ## route for the root path
def read_root():
    return {"Hello": "Welcome to the API!"}

@app.post("/initialize_project/")  ## route for initializing a project
def init_project(request: ProjectRequest):
    project_id = request.project_id
    token = fetch_token(project_id)
    data = intilaize_project(token, project_id)
    save_sqlite(data)
    return {"message": f"iElements for project {project_id} fetched.", "data": data, "Save":True}
   

@app.post("/query",response_model=List[IElements])  ## route for querying the database
async def query(Query_params:QueryParams,session: Session = Depends(get_session)):
    try:
        stmt = select(IElements)
        if Query_params.type:
            stmt = stmt.where(IElements.type == Query_params.type)
        if Query_params.name:
            stmt = stmt.where(IElements.name.contains(Query_params.name))

        results = session.exec(stmt).fetchmany(100)

        print(f"✅ Found {len(results)} results")
        
        if not results:
            raise HTTPException(status_code=404, detail="No records found")
        
        
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/status")
async def get_download_status():
    return download_progress
    
@app.post("/download")  ## route for querying the database
async def fetch_url(Query_params:QueryParams,session: Session = Depends(get_session)):
    try:
        if Query_params.type:

            urls = session.exec(select(IElements.uri).where(IElements.type == Query_params.type, IElements.uri != None)).all()

        else:

            urls = session.exec(select(IElements.uri).where(IElements.uri != None)).all()
        
        print(f"🔗 {len(urls)} URLs fetched")

        with download_lock:
            download_progress["status"] = "in_progress"
            download_progress["downloaded"] = 0
            download_progress["total"] = len(urls)
        #run_downloads(urls)
        # Run downloads in background thread
        threading.Thread(target=run_downloads, args=(urls,), daemon=True).start() # keeps API server responsive


        return {"message": "Download finished",'download_progres': download_progress}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
        

       

        