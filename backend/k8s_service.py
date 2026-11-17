import os
from kubernetes import client, config
from config import settings

class K8sService:
    def __init__(self):
        self.connected = False
        try:
            if os.getenv("KUBERNETES_SERVICE_HOST"):
                config.load_incluster_config()
                self.connected = True
            elif settings.KUBECONFIG_PATH:
                config.load_kube_config(config_file=settings.KUBECONFIG_PATH)
                self.connected = True
            else:
                config.load_kube_config()
                self.connected = True

            self.rbac_api = client.RbacAuthorizationV1Api()
            self.core_api = client.CoreV1Api()
        except Exception as e:
            print(f"[WARN] Kubernetes config load failed: {e}. Running in mocked/offline mode.")
            self.connected = False

    def list_namespaces(self):
        if not self.connected:
            return ["default", "kube-system", "dev-team-alpha", "staging"]
        try:
            ns_list = self.core_api.list_namespace()
            return [ns.metadata.name for ns in ns_list.items]
        except Exception as e:
            print(f"Error listing namespaces: {e}")
            return ["default", "dev-team-alpha"]

    def list_role_bindings(self, namespace: str = None):
        if not self.connected:
            return []
        try:
            if namespace:
                res = self.rbac_api.list_namespaced_role_binding(namespace)
            else:
                res = self.rbac_api.list_role_binding_for_all_namespaces()

            bindings = []
            for item in res.items:
                if item.metadata.labels and item.metadata.labels.get("managed-by") == "kubeauth":
                    for subject in item.subjects or []:
                        bindings.append({
                            "name": item.metadata.name,
                            "namespace": item.metadata.namespace,
                            "subject": subject.name,
                            "kind": subject.kind,
                            "role": item.role_ref.name
                        })
            return bindings
        except Exception as e:
            print(f"Error listing rolebindings: {e}")
            return []

    def create_role_binding(self, username: str, namespace: str, role_name: str):
        if not self.connected:
            return {"name": f"mock-{username}-{role_name}", "namespace": namespace}

        clean_user = username.replace("@", "-at-").replace(".", "-").lower()
        binding_name = f"kubeauth-{clean_user}-{role_name}"
        full_username = f"{settings.OIDC_USERNAME_PREFIX}{username}"

        body = client.V1RoleBinding(
            metadata=client.V1ObjectMeta(
                name=binding_name,
                namespace=namespace,
                labels={"managed-by": "kubeauth"}
            ),
            subjects=[
                client.RbacV1Subject(
                    kind="User",
                    name=full_username,
                    api_group="rbac.authorization.k8s.io"
                )
            ],
            role_ref=client.V1RoleRef(
                kind="ClusterRole",
                name=role_name,
                api_group="rbac.authorization.k8s.io"
            )
        )
        return self.rbac_api.create_namespaced_role_binding(namespace=namespace, body=body)

    def delete_role_binding(self, name: str, namespace: str):
        if not self.connected:
            return True
        return self.rbac_api.delete_namespaced_role_binding(name=name, namespace=namespace)
