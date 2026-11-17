# 🚀 KubeAuth: OIDC Kubernetes RBAC Management Platform

KubeAuth is a centralized Web platform designed to bridge Identity Providers (Keycloak, Azure AD/Entra, Okta, Red Hat SSO) and Kubernetes clusters. It empowers **Project Owners** to manage team membership and granular Kubernetes RBAC permissions across namespaces directly from an intuitive UI, without manually authoring YAML manifests.

---

## 🏛️ System Architecture

```mermaid
graph TB
    %% External Actors
    subgraph Users ["Actors & Clients"]
        Admin["👤 Cluster Admin / Project Owner"]
        Dev["💻 Developer / Contributor"]
        KLogin["⚙️ kubectl + kubelogin plugin"]
    end

    %% Web Application Plane
    subgraph KubeAuthPlatform ["KubeAuth Application (FastAPI + TemplateMo UI)"]
        UI["🖥️ Web UI (Bootstrap 5 / TemplateMo)<br/>Port: 8000"]
        
        subgraph Backend ["FastAPI Core Services"]
            APIRouter["API Router (/api/v1)"]
            KCClient["Keycloak Admin Client (python-keycloak)"]
            K8sEngine["K8s RBAC Engine (kubernetes-client)"]
        end
    end

    %% Identity Provider Plane
    subgraph IdP ["Identity Provider (Docker Compose)"]
        subgraph KeycloakServer ["Keycloak 24 (Port: 8080)"]
            MasterRealm["Master Realm (Admin Console)"]
            K8sRealm["Realm: k8s-realm"]
            KC_Client_App["Client: kubeauth-backend<br/>(Service Account / Admin API)"]
            KC_Client_K8s["Client: kubernetes<br/>(Public Client / PKCE)"]
            UsersDB[("Users & Groups<br/>• alice.owner<br/>• bob.dev<br/>• charlie.intern")]
        end
        PGDB[("PostgreSQL DB<br/>(keycloak-db:5432)")]
    end

    %% Kubernetes Cluster Plane
    subgraph K8sCluster ["Target Kubernetes Cluster"]
        APIServer["☸️ kube-apiserver<br/>(--oidc-issuer-url=...<br/>--oidc-client-id=kubernetes<br/>--oidc-username-claim=preferred_username)"]
        
        subgraph Namespaces ["Namespaces & Scopes"]
            subgraph NSA ["Namespace: dev-team-alpha"]
                RB1["RoleBinding: kubeauth-bob-dev-edit"]
                CR_Edit["ClusterRole: edit"]
                PodsA["Deployments / Pods / Logs"]
            end
            subgraph NSB ["Namespace: staging"]
                RB2["RoleBinding: kubeauth-charlie-intern-view"]
                CR_View["ClusterRole: view"]
                PodsB["ReadOnly Workloads"]
            end
        end
    end

    %% Control Plane Interactions
    Admin -->|"1. Opens Dashboard"| UI
    UI -->|"2. REST Calls (Bindings, Users, NS)"| APIRouter
    APIRouter -->|"Query Users & Groups"| KCClient
    KCClient -->|"3. Admin REST API"| KC_Client_App
    APIRouter -->|"Provision RBAC"| K8sEngine
    K8sEngine -->|"4. Create / Delete RoleBindings<br/>(~/.kube/config or ServiceAccount)"| APIServer

    %% Keycloak internal
    KeycloakServer <--> PGDB

    %% Runtime Developer Access Flow
    Dev -->|"5. Run kubectl command"| KLogin
    KLogin -->|"6. OIDC Auth Request (PKCE)"| KC_Client_K8s
    KC_Client_K8s -->|"7. Returns Signed ID Token (JWT)"| KLogin
    KLogin -->|"8. Send Bearer Token (JWT)"| APIServer
    APIServer -.->|"9. Validate Signature via JWKS"| K8sRealm
    APIServer -->|"10. Evaluate RoleBindings"| RB1
    RB1 -.->|"References"| CR_Edit
    CR_Edit -->|"11. Grant Access"| PodsA

    %% Styling
    classDef actor fill:#f8fafc,stroke:#334155,stroke-width:2px;
    classDef app fill:#eff6ff,stroke:#2563eb,stroke-width:2px;
    classDef idp fill:#fef3c7,stroke:#d97706,stroke-width:2px;
    classDef k8s fill:#f0fdf4,stroke:#16a34a,stroke-width:2px;

    class Admin,Dev,KLogin actor;
    class UI,APIRouter,KCClient,K8sEngine app;
    class KeycloakServer,MasterRealm,K8sRealm,KC_Client_App,KC_Client_K8s,UsersDB,PGDB idp;
    class APIServer,NSA,NSB,RB1,RB2,CR_Edit,CR_View,PodsA,PodsB k8s;
```

---

## 🔄 Sequence Diagram: End-to-End Workflow

### 1. Management Plane: Project Owner assigns a role
```mermaid
sequenceDiagram
    autonumber
    actor Owner as Project Owner / Admin
    participant UI as KubeAuth Web UI
    participant API as FastAPI Backend
    participant KC as Keycloak (k8s-realm)
    participant K8s as kube-apiserver

    Owner->>UI: Selects user "bob.dev", namespace "dev-team-alpha", role "edit"
    UI->>API: POST /api/v1/bindings {username, namespace, role}
    API->>KC: Verify user existence via Admin API
    KC-->>API: User details (username, email, id) confirmed
    API->>K8s: Create V1RoleBinding (subject: oidc:bob.dev, roleRef: edit)
    K8s-->>API: 201 Created
    API-->>UI: Success confirmation
    UI-->>Owner: Displays active RoleBinding badge
```

### 2. Runtime Plane: Developer connects using `kubectl`
```mermaid
sequenceDiagram
    autonumber
    actor Dev as Developer (bob.dev)
    participant CLI as kubectl (kubelogin)
    participant KC as Keycloak IdP
    participant K8s as kube-apiserver

    Dev->>CLI: kubectl get pods -n dev-team-alpha
    CLI->>KC: Redirect to login page (OIDC Auth Code + PKCE)
    Dev->>KC: Enter credentials (bob.dev / password123)
    KC-->>CLI: Issue signed ID Token (JWT with preferred_username: bob.dev)
    CLI->>K8s: GET /api/v1/namespaces/dev-team-alpha/pods (Bearer JWT)
    K8s->>KC: Fetch JWKS public keys (cached) to verify token signature
    K8s->>K8s: Match claim "oidc:bob.dev" with RoleBinding "kubeauth-bob-dev-edit"
    K8s-->>CLI: 200 OK (Pod list returned)
```

---

## 📁 Project Directory Layout

```text
/home/u268710/kubeauth/
├── README.md                          # Project documentation and architecture
├── docker-compose.yml                  # Keycloak 24 (Quarkus) + PostgreSQL 15
├── .env                                # Runtime configuration & credentials
├── keycloak/
│   └── realm-export.json              # Pre-provisioned realm, OIDC clients, & users
├── backend/
│   ├── config.py                      # Pydantic environment configuration
│   ├── k8s_service.py                 # Kubernetes client wrapper (RoleBindings, NS)
│   ├── main.py                        # FastAPI endpoints and Keycloak Admin integration
│   └── requirements.txt               # Python package dependencies
└── frontend/
    ├── index.html                     # Bootstrap 5 / TemplateMo dashboard UI
    └── static/
        ├── css/style.css              # Custom styling
        └── js/app.js                  # Frontend state management & REST consumer
```

---

## ⚙️ Components Description

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend UI** | HTML5, Bootstrap 5, Vanilla JS | Clean dashboard allowing Project Owners to assign/revoke developer access. |
| **API Backend** | Python 3, FastAPI, Uvicorn | Exposes REST APIs, communicates with Keycloak Admin REST API and Kubernetes RBAC API. |
| **Identity Provider** | Keycloak 24, PostgreSQL | Manages enterprise identities, groups, realms, and OpenID Connect tokens. |
| **Kubernetes RBAC Engine** | `kubernetes-client` (SIG) | Creates namespaced `RoleBinding` objects mapping `oidc:<username>` to standard `ClusterRoles` (`edit`, `view`, `admin`). |

---

## 🚀 Quick Start Guide

### 1. Launch Keycloak and Database
```bash
cd /home/u268710/kubeauth
docker compose up -d
```
- **Keycloak Admin Console**: `http://localhost:8080/admin`
- **Default Credentials**: `admin` / `adminpassword`
- **Imported Realm**: `k8s-realm`
- **Pre-configured Test Users** (password for all: `password123`):
  - `alice.owner` (Project Owner)
  - `bob.dev` (Developer)
  - `charlie.intern` (Intern / Viewer)

### 2. Start the Backend & Web UI
```bash
cd /home/u268710/kubeauth/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### 3. Open the Web Application
Navigate to:
👉 **`http://localhost:8000`**

---

## 🔒 Kubernetes Cluster Configuration (kube-apiserver)

When setting up your `kubeadm` cluster, add these arguments to `/etc/kubernetes/manifests/kube-apiserver.yaml`:

```yaml
spec:
  containers:
  - command:
    - kube-apiserver
    - --oidc-issuer-url=http://<KEYCLOAK_HOST_IP>:8080/realms/k8s-realm
    - --oidc-client-id=kubernetes
    - --oidc-username-claim=preferred_username
    - --oidc-username-prefix=oidc:
    - --oidc-groups-claim=groups
    - --oidc-groups-prefix=oidc:
```
