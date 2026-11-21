
print("KubeWatch backend is starting...")

from kubernetes import client, config
from kubernetes.client.exceptions import ApiException


# -----------------------------------
# 1. Convert CPU and Memory Units
# -----------------------------------

def convert_cpu(cpu):
    if cpu.endswith("n"):
        return round(int(cpu[:-1]) / 1_000_000, 2)

    elif cpu.endswith("u"):
        return round(int(cpu[:-1]) / 1000, 2)

    elif cpu.endswith("m"):
        return float(cpu[:-1])

    return float(cpu)


def convert_memory(memory):
    if memory.endswith("Ki"):
        return round(int(memory[:-2]) / 1024, 2)

    elif memory.endswith("Mi"):
        return float(memory[:-2])

    elif memory.endswith("Gi"):
        return round(float(memory[:-2]) * 1024, 2)

    elif memory.endswith("Ti"):
        return round(float(memory[:-2]) * 1024 * 1024, 2)

    elif memory.endswith("K"):
        return round(float(memory[:-1]) / 1024, 2)

    elif memory.endswith("M"):
        return float(memory[:-1])

    elif memory.endswith("G"):
        return round(float(memory[:-1]) * 1024, 2)

    return memory


# -----------------------------------
# 2. Connect to Kubernetes Cluster
# -----------------------------------

def connect_to_cluster(context_name):
    try:
        api_client = config.new_client_from_config(
            context=context_name
        )

        v1 = client.CoreV1Api(api_client)

        print(
            f"Successfully connected to Kubernetes: {context_name}"
        )

        return v1, api_client

    except Exception as e:
        print(f"Connection failed: {e}")
        raise


# -----------------------------------
# 3. Fetch Node Information
# -----------------------------------

def get_nodes(v1):
    try:
        nodes = v1.list_node()

        node_data = []

        for node in nodes.items:

            ready_status = "Unknown"

            for condition in node.status.conditions or []:
                if condition.type == "Ready":
                    ready_status = condition.status

            node_data.append({
                "name": node.metadata.name,
                "status": ready_status,
                "cpu_capacity": node.status.capacity.get("cpu"),
                "memory_capacity": node.status.capacity.get("memory")
            })

        return node_data

    except ApiException as e:
        print(f"Error fetching nodes: {e}")
        return []


# -----------------------------------
# 4. Identify Pod Workloads
# -----------------------------------

def get_workload_mapping(v1):
    """
    Build a mapping between ReplicaSets and Deployments.

    Deployment -> ReplicaSet -> Pod

    This allows us to identify the actual Deployment
    that owns a particular pod.
    """

    workload_mapping = {}

    try:
        apps_v1 = client.AppsV1Api(v1.api_client)

        replica_sets = apps_v1.list_replica_set_for_all_namespaces()

        for rs in replica_sets.items:

            namespace = rs.metadata.namespace
            rs_name = rs.metadata.name

            workload_type = "ReplicaSet"
            workload_name = rs_name

            for owner in rs.metadata.owner_references or []:

                if owner.kind == "Deployment" and owner.controller:
                    workload_type = "Deployment"
                    workload_name = owner.name
                    break

            workload_mapping[(namespace, rs_name)] = {
                "workload_type": workload_type,
                "workload_name": workload_name
            }

        return workload_mapping

    except ApiException as e:
        print(f"Error fetching ReplicaSets: {e}")
        return workload_mapping


# -----------------------------------
# 5. Get Workload Information for Pod
# -----------------------------------

def get_pod_workload(pod, workload_mapping):

    namespace = pod.metadata.namespace

    owner_references = pod.metadata.owner_references or []

    # Find the controller owner
    controller_owner = next(
        (
            owner for owner in owner_references
            if owner.controller
        ),
        None
    )

    # Pod has no controller owner
    if controller_owner is None:
        return {
            "workload_type": "Pod",
            "workload_name": pod.metadata.name
        }

    owner_kind = controller_owner.kind
    owner_name = controller_owner.name

    # ReplicaSet -> Deployment mapping
    if owner_kind == "ReplicaSet":

        workload = workload_mapping.get(
            (namespace, owner_name)
        )

        if workload:
            return workload

        # Fallback if ReplicaSet lookup was unavailable
        return {
            "workload_type": "ReplicaSet",
            "workload_name": owner_name
        }

    # Handle direct workload owners
    supported_workloads = [
        "StatefulSet",
        "DaemonSet",
        "Job",
        "ReplicationController"
    ]

    if owner_kind in supported_workloads:
        return {
            "workload_type": owner_kind,
            "workload_name": owner_name
        }

    # Kubernetes static pods commonly have Node as owner
    if owner_kind == "Node":
        return {
            "workload_type": "StaticPod",
            "workload_name": pod.metadata.name
        }

    # Unknown owner type
    return {
        "workload_type": owner_kind,
        "workload_name": owner_name
    }


# -----------------------------------
# 6. Fetch Pod Information
# -----------------------------------

def get_pods(v1):

    try:
        pod_list = v1.list_pod_for_all_namespaces()

        pods = []

        # Build ReplicaSet -> Deployment mapping once
        workload_mapping = get_workload_mapping(v1)

        for pod in pod_list.items:

            name = pod.metadata.name
            namespace = pod.metadata.namespace

            status = (
                pod.status.phase
                if pod.status.phase
                else "Unknown"
            )

            node = pod.spec.node_name or "Not Assigned"

            # Get workload details
            workload = get_pod_workload(
                pod,
                workload_mapping
            )

            # Container information
            container_statuses = (
                pod.status.container_statuses or []
            )

            restarts = sum(
                container.restart_count
                for container in container_statuses
            )

            ready_containers = sum(
                1 for container in container_statuses
                if container.ready
            )

            total_containers = len(container_statuses)

            # Detailed container states
            container_details = []

            for container in container_statuses:

                container_state = "Unknown"
                reason = None

                if container.state:

                    if container.state.waiting:
                        container_state = "Waiting"
                        reason = container.state.waiting.reason

                    elif container.state.running:
                        container_state = "Running"

                    elif container.state.terminated:
                        container_state = "Terminated"
                        reason = container.state.terminated.reason

                container_details.append({
                    "name": container.name,
                    "state": container_state,
                    "reason": reason,
                    "ready": container.ready,
                    "restarts": container.restart_count
                })

            # Store pod information
            pods.append({

                "name": name,
                "namespace": namespace,
                "status": status,
                "node": node,
                "restarts": restarts,

                "ready_containers": ready_containers,
                "total_containers": total_containers,

                # Workload information
                "workload_type": workload["workload_type"],
                "workload_name": workload["workload_name"],

                "containers": container_details
            })

        return pods

    except ApiException as e:
        print(f"Error fetching pods: {e}")
        return []


# -----------------------------------
# 7. Fetch Node CPU and Memory Metrics
# -----------------------------------

def get_node_metrics(api_client):

    try:
        custom_api = client.CustomObjectsApi(api_client)

        metrics = custom_api.list_cluster_custom_object(
            group="metrics.k8s.io",
            version="v1beta1",
            plural="nodes"
        )

        node_metrics = []

        for item in metrics["items"]:

            node_metrics.append({

                "name": item["metadata"]["name"],

                "cpu_millicores": convert_cpu(
                    item["usage"]["cpu"]
                ),

                "memory_mib": convert_memory(
                    item["usage"]["memory"]
                )
            })

        return node_metrics

    except ApiException as e:
        print(f"Error fetching node metrics: {e}")
        return []


# -----------------------------------
# 8. Fetch Pod CPU and Memory Metrics
# -----------------------------------

def get_pod_metrics(api_client):

    try:
        custom_api = client.CustomObjectsApi(api_client)

        metrics = custom_api.list_cluster_custom_object(
            group="metrics.k8s.io",
            version="v1beta1",
            plural="pods"
        )

        pod_metrics = []

        for item in metrics["items"]:

            containers = []

            for container in item["containers"]:

                containers.append({

                    "name": container["name"],

                    "cpu_millicores": convert_cpu(
                        container["usage"]["cpu"]
                    ),

                    "memory_mib": convert_memory(
                        container["usage"]["memory"]
                    )
                })

            pod_metrics.append({

                "name": item["metadata"]["name"],
                "namespace": item["metadata"]["namespace"],
                "containers": containers
            })

        return pod_metrics

    except ApiException as e:
        print(f"Error fetching pod metrics: {e}")
        return []


# -----------------------------------
# 9. Main Function - Test Backend
# -----------------------------------

if __name__ == "__main__":

    context_name = "kind-dev"

    v1, api_client = connect_to_cluster(context_name)

    try:
        nodes = get_nodes(v1)
        pods = get_pods(v1)

        node_metrics = get_node_metrics(api_client)
        pod_metrics = get_pod_metrics(api_client)

        print("\n========== NODE INFORMATION ==========")

        for node in nodes:
            print(node)

        print("\n========== POD INFORMATION ==========")

        for pod in pods:
            print(pod)

        # Workload Summary
        print("\n========== WORKLOAD SUMMARY ==========")

        workloads = {}

        for pod in pods:

            key = (
                pod["namespace"],
                pod["workload_type"],
                pod["workload_name"]
            )

            workloads[key] = workloads.get(key, 0) + 1

        for key, count in workloads.items():

            namespace, workload_type, workload_name = key

            print(
                f"Namespace: {namespace} | "
                f"Type: {workload_type} | "
                f"Name: {workload_name} | "
                f"Pods: {count}"
            )

        print("\n========== CLUSTER SUMMARY ==========")

        print("Cluster:", context_name)
        print("Total Nodes:", len(nodes))
        print("Total Pods:", len(pods))

        running_pods = sum(
            1 for pod in pods if pod["status"] == "Running"
        )

        print("Running Pods:", running_pods)

        print("\n========== NODE METRICS ==========")

        for node in node_metrics:
            print(node)

        print("\n========== POD METRICS ==========")

        for pod in pod_metrics:
            print(pod)

    finally:
        api_client.close()
