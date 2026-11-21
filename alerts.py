
def generate_alerts(pods):
    alerts = []

    for pod in pods:

        pod_name = pod["name"]
        namespace = pod["namespace"]

        # Workload information
        workload_type = pod.get("workload_type", "Unknown")
        workload_name = pod.get("workload_name", "Unknown")

        # -----------------------------------
        # 1. Pod-level Alerts
        # -----------------------------------

        if pod["status"] == "Failed":
            alerts.append({
                "severity": "Critical",
                "namespace": namespace,
                "workload_type": workload_type,
                "workload_name": workload_name,
                "pod": pod_name,
                "container": None,
                "message": "Pod has failed"
            })

        elif pod["status"] != "Running":
            alerts.append({
                "severity": "Warning",
                "namespace": namespace,
                "workload_type": workload_type,
                "workload_name": workload_name,
                "pod": pod_name,
                "container": None,
                "message": f"Pod status is {pod['status']}"
            })

        # -----------------------------------
        # 2. Container-level Alerts
        # -----------------------------------

        for container in pod["containers"]:

            container_name = container["name"]
            reason = container["reason"]
            restarts = container["restarts"]
            ready = container["ready"]

            # CrashLoopBackOff
            if reason == "CrashLoopBackOff":
                alerts.append({
                    "severity": "Critical",
                    "namespace": namespace,
                    "workload_type": workload_type,
                    "workload_name": workload_name,
                    "pod": pod_name,
                    "container": container_name,
                    "message": f"{container_name}: CrashLoopBackOff"
                })

            # Image pull failures
            elif reason in ["ImagePullBackOff", "ErrImagePull"]:
                alerts.append({
                    "severity": "Critical",
                    "namespace": namespace,
                    "workload_type": workload_type,
                    "workload_name": workload_name,
                    "pod": pod_name,
                    "container": container_name,
                    "message": f"{container_name}: {reason}"
                })

            # Container readiness
            if not ready:
                alerts.append({
                    "severity": "Warning",
                    "namespace": namespace,
                    "workload_type": workload_type,
                    "workload_name": workload_name,
                    "pod": pod_name,
                    "container": container_name,
                    "message": f"{container_name}: Container is not ready"
                })

            # Historical restart count
            elif restarts >= 5:
                alerts.append({
                    "severity": "Info",
                    "namespace": namespace,
                    "workload_type": workload_type,
                    "workload_name": workload_name,
                    "pod": pod_name,
                    "container": container_name,
                    "message": (
                        f"{container_name}: "
                        f"Historical restart count ({restarts})"
                    )
                })

    return alerts
