import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from keycloak import KeycloakAdmin

from config import settings
from k8s_service import K8sService

app = FastAPI(title="KubeAuth Manager")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

k8s = K8sService()

def get_kc_admin():
    return KeycloakAdmin(
        server_url=settings.KEYCLOAK_URL,
        username=settings.KEYCLOAK_ADMIN_USER,
        password=settings.KEYCLOAK_ADMIN_PASSWORD,
        realm_name=settings.KEYCLOAK_REALM,
        user_realm_name="master",
        verify=False
    )

class BindingRequest(BaseModel):
    username: str
    namespace: str
    role: str

@app.get("/api/v1/health")
def health():
    return {
        "status": "healthy",
        "k8s_connected": k8s.connected,
        "keycloak_url": settings.KEYCLOAK_URL,
        "realm": settings.KEYCLOAK_REALM
    }

@app.get("/api/v1/users")
def get_users():
    try:
        kc = get_kc_admin()
        users = kc.get_users({})
        return [
            {
                "id": u["id"],
                "username": u.get("username"),
                "email": u.get("email"),
                "firstName": u.get("firstName", ""),
                "lastName": u.get("lastName", "")
            }
            for u in users
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Keycloak error: {str(e)}")

@app.get("/api/v1/namespaces")
def get_namespaces():
    return k8s.list_namespaces()

@app.get("/api/v1/bindings")
def get_bindings(namespace: str = None):
    return k8s.list_role_bindings(namespace)

@app.post("/api/v1/bindings")
def create_binding(req: BindingRequest):
    try:
        k8s.create_role_binding(req.username, req.namespace, req.role)
        return {"status": "success", "message": f"Assigned {req.role} to {req.username} in {req.namespace}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/v1/bindings/{namespace}/{name}")
def delete_binding(namespace: str, name: str):
    try:
        k8s.delete_role_binding(name, namespace)
        return {"status": "success", "message": f"Deleted {name}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
app.mount("/static", StaticFiles(directory=os.path.join(frontend_path, "static")), name="static")

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(frontend_path, "index.html"))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=settings.APP_PORT, reload=True)
