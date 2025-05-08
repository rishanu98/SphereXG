import sqlite3, requests, json, os, mimetypes

def get_token(project_id):
    token_resp = requests.post(
        "https://core.api.dev.holobuilder.eu/v3/auth/token",
        json={
            "scopes": ["user:project"],
            "data": {"projects": [{"id": project_id}]}
        }
    )

    if token_resp.status_code == 200:
        return token_resp.json()['data'].get("token")
    else:
        raise Exception(f"Failed to get token: {token_resp.status_code} - {token_resp.text}")

def sqlite_save(data):
    
    conn = sqlite3.connect("project_cache.db")
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS iElements")
    for record in data['page']:
        # create table
        #cursor.execute("DROP TABLE IF EXISTS iElements")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS iElements (
                id TEXT PRIMARY KEY,
                type TEXT,
                typeHint TEXT,
                name TEXT,
                uri TEXT,
                metaData TEXT,
                pose TEXT,
                globalPose TEXT,
                boundingBox TEXT,
                childrenIds TEXT,
                full_json TEXT
            )
        ''')

        cursor.execute('''
            INSERT OR REPLACE INTO iElements (
                id, type, typeHint, name, uri,
                metaData, pose, globalPose, boundingBox,
                childrenIds, full_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record.get('id'),
            record.get('type'),
            record.get('typeHint'),
            record.get('name'),
            record.get('uri'), 
            json.dumps(record.get('metaDataMap', {})),
            json.dumps(record.get('pose', {})),
            json.dumps(record.get('globalPose', {})),
            json.dumps(record.get('boundingBox', {})),
            json.dumps(record.get('childrenIds', [])),
            json.dumps(record)
        ))

        conn.commit()
    conn.close()
    print(f"✅ {len(record)} iElements saved in database.")

def download_file(url, index, total,path:str):
    try:
        print(f"📥 Downloading {index}/{total} → {url}")
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

    except Exception as e:
        print(f"Error downloading {url}: {e}")