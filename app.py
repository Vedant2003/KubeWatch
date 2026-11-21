import streamlit as st
import pandas as pd
import plotly.express as px

from kubernetes import config
from streamlit_autorefresh import st_autorefresh

from kubernetes_client import (
    connect_to_cluster,
    get_nodes,
    get_pods,
    get_node_metrics,
    get_pod_metrics,
)

from alerts import generate_alerts


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="KubeWatch | Kubernetes Monitoring",
    page_icon="☸️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------
# CUSTOM CSS
# --------------------------------------------------

st.markdown(
    """
    <style>
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }

    [data-testid="stSidebar"] {
        background-color: #161b22;
    }

    [data-testid="stMetric"] {
        background-color: #1c2330;
        border: 1px solid #303846;
        padding: 16px;
        border-radius: 12px;
    }

    [data-testid="stMetricLabel"] {
        color: #aab4c3;
    }

    [data-testid="stMetricValue"] {
        color: #ffffff;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: #303846;
        border-radius: 12px;
    }

    .main-title {
        font-size: 34px;
        font-weight: 750;
        color: #ffffff;
    }

    .sub-title {
        color: #9ca8b8;
        font-size: 14px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def section_heading(title, description=None):
    st.subheader(title)

    if description:
        st.caption(description)


def style_chart(fig, height=350):
    fig.update_layout(
        height=height,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=35, b=20),
        font=dict(color="#e5e7eb"),
        legend_title_text="",
    )

    return fig


def metrics_to_dataframe(metrics, metric_type, pods=None):
    """
    Convert backend metrics into dashboard DataFrames.

    Backend node metrics:
        name, cpu_millicores, memory_mib

    Backend pod metrics:
        name, namespace, containers[
            cpu_millicores, memory_mib
        ]

    Pod container metrics are summed to get pod-level totals.
    """

    rows = []

    if not metrics:
        return pd.DataFrame()

    if metric_type == "node":

        for item in metrics:
            rows.append({
                "Node": item.get("name", "Unknown"),
                "CPU": float(item.get("cpu_millicores", 0)),
                "Memory": float(item.get("memory_mib", 0)),
            })

    elif metric_type == "pod":

        # Map pod identity to its workload information.
        pod_lookup = {}

        for pod in pods or []:
            key = (pod.get("namespace"), pod.get("name"))
            pod_lookup[key] = {
                "Workload Type": pod.get("workload_type", "Unknown"),
                "Workload": pod.get("workload_name", "Unknown"),
            }

        for item in metrics:

            containers = item.get("containers", [])

            total_cpu = sum(
                float(container.get("cpu_millicores", 0))
                for container in containers
            )

            total_memory = sum(
                float(container.get("memory_mib", 0))
                for container in containers
            )

            namespace = item.get("namespace", "default")
            pod_name = item.get("name", "Unknown")

            workload = pod_lookup.get(
                (namespace, pod_name),
                {
                    "Workload Type": "Unknown",
                    "Workload": "Unknown",
                },
            )

            rows.append({
                "Pod": pod_name,
                "Namespace": namespace,
                "Workload Type": workload["Workload Type"],
                "Workload": workload["Workload"],
                "CPU": total_cpu,
                "Memory": total_memory,
            })

    return pd.DataFrame(rows)


# --------------------------------------------------
# CACHED CLUSTER DATA
# --------------------------------------------------

@st.cache_data(ttl=5, show_spinner=False)
def load_cluster_data(context_name):

    api_client = None

    try:
        v1, api_client = connect_to_cluster(context_name)

        nodes = get_nodes(v1)
        pods = get_pods(v1)

        node_metrics = get_node_metrics(api_client)
        pod_metrics = get_pod_metrics(api_client)

        return (
            nodes,
            pods,
            node_metrics,
            pod_metrics,
            None,
        )

    except Exception as e:
        return [], [], [], [], str(e)

    finally:
        if api_client:
            api_client.close()


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:

    st.markdown("## ☸️ KubeWatch")
    st.caption("Kubernetes Multi-Cluster Monitoring")

    st.divider()

    st.markdown("### Cluster Selection")

    try:
        contexts, active_context = config.list_kube_config_contexts()

        context_names = [
            context["name"] for context in contexts
        ] if contexts else []

    except Exception as e:
        context_names = []
        st.error(f"Unable to load Kubernetes contexts: {e}")

    if not context_names:
        st.error("No Kubernetes contexts found.")
        st.stop()

    selected_context = st.selectbox(
        "Select Cluster",
        context_names,
        index=(
            context_names.index(active_context["name"])
            if active_context
            and active_context.get("name") in context_names
            else 0
        ),
    )

    st.divider()

    if st.button("🔄 Refresh Dashboard", width="stretch"):
        load_cluster_data.clear()
        st.rerun()

    st.markdown("### Monitoring")
    st.success("Auto refresh enabled")
    st.caption("Dashboard refreshes every 10 seconds.")

    st.divider()

    st.caption("KubeWatch v1.1")


# --------------------------------------------------
# AUTO REFRESH
# --------------------------------------------------

st_autorefresh(
    interval=10000,
    key="kube_watch_refresh",
)


# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

nodes, pods, node_metrics, pod_metrics, error = load_cluster_data(
    selected_context
)

if error:
    st.error(f"Cluster connection failed: {error}")
    st.stop()


# --------------------------------------------------
# PREPARE DATA
# --------------------------------------------------

total_nodes = len(nodes)
total_pods = len(pods)

running_pods = sum(
    1 for pod in pods if pod.get("status") == "Running"
)

pending_pods = sum(
    1 for pod in pods if pod.get("status") == "Pending"
)

failed_pods = sum(
    1 for pod in pods
    if pod.get("status") in ["Failed", "Unknown"]
)

node_df = metrics_to_dataframe(node_metrics, "node")
pod_df = metrics_to_dataframe(pod_metrics, "pod", pods)


# --------------------------------------------------
# DASHBOARD HEADER
# --------------------------------------------------

st.markdown(
    '<div class="main-title">☸️ KubeWatch Dashboard</div>',
    unsafe_allow_html=True,
)

st.markdown(
    f'<div class="sub-title">Monitoring cluster: '
    f'<b>{selected_context}</b></div>',
    unsafe_allow_html=True,
)

st.write("")


# --------------------------------------------------
# CLUSTER OVERVIEW
# --------------------------------------------------

with st.container(border=True):

    section_heading(
        "Cluster Overview",
        "Real-time health and workload summary",
    )

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Total Nodes", total_nodes)
    col2.metric("Total Pods", total_pods)
    col3.metric("Running Pods", running_pods)
    col4.metric("Pending Pods", pending_pods)
    col5.metric("Failed / Unknown", failed_pods)


# --------------------------------------------------
# NODE MONITORING
# --------------------------------------------------

st.write("")

with st.container(border=True):

    section_heading(
        "Node Monitoring",
        "CPU and memory usage across cluster nodes",
    )

    if not node_df.empty:

        col1, col2 = st.columns(2)

        with col1:
            fig = px.bar(
                node_df,
                x="Node",
                y="CPU",
                title="Node CPU Usage (millicores)",
                text_auto=True,
            )

            st.plotly_chart(
                style_chart(fig),
                width="stretch",
            )

        with col2:
            fig = px.bar(
                node_df,
                x="Node",
                y="Memory",
                title="Node Memory Usage (MiB)",
                text_auto=True,
            )

            st.plotly_chart(
                style_chart(fig),
                width="stretch",
            )

        with st.expander("View Node Metrics Details"):
            st.dataframe(
                node_df,
                width="stretch",
                hide_index=True,
            )

    else:
        st.info("Node metrics are currently unavailable.")


# --------------------------------------------------
# POD MONITORING
# --------------------------------------------------

st.write("")

with st.container(border=True):

    section_heading(
        "Pod Monitoring",
        "Monitor pod status, workloads, namespaces and container restarts",
    )

    if pods:

        pod_df_display = pd.DataFrame([
            {
                "Pod": pod.get("name"),
                "Namespace": pod.get("namespace"),
                "Workload Type": pod.get("workload_type", "Unknown"),
                "Workload": pod.get("workload_name", "Unknown"),
                "Status": pod.get("status"),
                "Node": pod.get("node"),
                "Restarts": pod.get("restarts", 0),
                "Ready Containers": (
                    f"{pod.get('ready_containers', 0)}/"
                    f"{pod.get('total_containers', 0)}"
                ),
            }
            for pod in pods
        ])

        namespaces = sorted(
            set(pod.get("namespace", "default") for pod in pods)
        )

        selected_namespace = st.selectbox(
            "Filter Pods by Namespace",
            ["All Namespaces"] + namespaces,
            key="pod_namespace_filter",
        )

        if selected_namespace != "All Namespaces":
            pod_df_display = pod_df_display[
                pod_df_display["Namespace"] == selected_namespace
            ]

        st.dataframe(
            pod_df_display,
            width="stretch",
            hide_index=True,
        )

        st.caption(
            f"Showing {len(pod_df_display)} of {total_pods} pods"
        )

    else:
        st.info("No pods found in this cluster.")


# --------------------------------------------------
# POD RESOURCE ANALYTICS
# --------------------------------------------------

st.write("")

with st.container(border=True):

    section_heading(
        "Pod Resource Analytics",
        "Analyze CPU and memory consumption at pod level",
    )

    if not pod_df.empty:

        tab1, tab2, tab3 = st.tabs([
            "CPU Usage",
            "Memory Usage",
            "Resource Details",
        ])

        with tab1:

            cpu_df = pod_df.sort_values(
                "CPU", ascending=False
            ).head(10)

            fig = px.bar(
                cpu_df,
                x="CPU",
                y="Pod",
                color="Namespace",
                orientation="h",
                title="Top 10 Pods by CPU Usage (millicores)",
            )

            fig.update_layout(
                yaxis={"categoryorder": "total ascending"}
            )

            st.plotly_chart(
                style_chart(fig),
                width="stretch",
            )

        with tab2:

            memory_df = pod_df.sort_values(
                "Memory", ascending=False
            ).head(10)

            fig = px.bar(
                memory_df,
                x="Memory",
                y="Pod",
                color="Namespace",
                orientation="h",
                title="Top 10 Pods by Memory Usage (MiB)",
            )

            fig.update_layout(
                yaxis={"categoryorder": "total ascending"}
            )

            st.plotly_chart(
                style_chart(fig),
                width="stretch",
            )

        with tab3:

            st.dataframe(
                pod_df,
                width="stretch",
                hide_index=True,
            )

    else:
        st.info("Pod resource metrics are currently unavailable.")


# --------------------------------------------------
# CLUSTER HEALTH & WORKLOAD-AWARE ALERTS
# --------------------------------------------------

st.write("")

with st.container(border=True):

    section_heading(
        "🚨 Cluster Health & Alerts",
        "Investigate issues by namespace, workload, severity and pod",
    )

    alerts = generate_alerts(pods)
    alerts_df = pd.DataFrame(alerts)

    if not alerts_df.empty:

        # Ensure consistent columns even if older alert records exist.
        expected_columns = [
            "severity",
            "namespace",
            "workload_type",
            "workload_name",
            "pod",
            "container",
            "message",
        ]

        for column in expected_columns:
            if column not in alerts_df.columns:
                alerts_df[column] = "Unknown"

        alerts_df = alerts_df[expected_columns].copy()

        # ------------------------------------------
        # ALERT SUMMARY
        # ------------------------------------------

        critical_count = (
            alerts_df["severity"] == "Critical"
        ).sum()

        warning_count = (
            alerts_df["severity"] == "Warning"
        ).sum()

        info_count = (
            alerts_df["severity"] == "Info"
        ).sum()

        affected_pods = alerts_df["pod"].nunique()

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Critical Alerts", int(critical_count))
        c2.metric("Warnings", int(warning_count))
        c3.metric("Information", int(info_count))
        c4.metric("Affected Pods", int(affected_pods))

        st.divider()

        # ------------------------------------------
        # ALERT FILTERS
        # ------------------------------------------

        st.markdown("### Filter Alerts")

        # Namespace filter
        available_namespaces = sorted(
            alerts_df["namespace"].dropna().astype(str).unique().tolist()
        )

        selected_alert_namespace = st.selectbox(
            "Namespace",
            ["All Namespaces"] + available_namespaces,
            key="alert_namespace_filter",
        )

        namespace_filtered_df = alerts_df.copy()

        if selected_alert_namespace != "All Namespaces":
            namespace_filtered_df = namespace_filtered_df[
                namespace_filtered_df["namespace"]
                == selected_alert_namespace
            ]

        # Workload type filter
        available_workload_types = sorted(
            namespace_filtered_df["workload_type"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        selected_workload_type = st.selectbox(
            "Workload Type",
            ["All Workload Types"] + available_workload_types,
            key="alert_workload_type_filter",
        )

        workload_type_filtered_df = namespace_filtered_df.copy()

        if selected_workload_type != "All Workload Types":
            workload_type_filtered_df = workload_type_filtered_df[
                workload_type_filtered_df["workload_type"]
                == selected_workload_type
            ]

        # Workload name filter
        available_workloads = sorted(
            workload_type_filtered_df["workload_name"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        selected_workload = st.selectbox(
            "Workload Name",
            ["All Workloads"] + available_workloads,
            key="alert_workload_name_filter",
        )

        # Severity and pod filters
        filter_col1, filter_col2 = st.columns(2)

        with filter_col1:
            selected_severity = st.selectbox(
                "Severity",
                ["All Severities", "Critical", "Warning", "Info"],
                key="alert_severity_filter",
            )

        with filter_col2:
            available_pods = sorted(
                workload_type_filtered_df["pod"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            selected_alert_pod = st.selectbox(
                "Pod",
                ["All Pods"] + available_pods,
                key="alert_pod_filter",
            )

        search_text = st.text_input(
            "Search alerts",
            placeholder="Search workload, pod, container or message...",
            key="alert_search",
        )

        # ------------------------------------------
        # APPLY ALL FILTERS
        # ------------------------------------------

        filtered_alerts = alerts_df.copy()

        if selected_alert_namespace != "All Namespaces":
            filtered_alerts = filtered_alerts[
                filtered_alerts["namespace"]
                == selected_alert_namespace
            ]

        if selected_workload_type != "All Workload Types":
            filtered_alerts = filtered_alerts[
                filtered_alerts["workload_type"]
                == selected_workload_type
            ]

        if selected_workload != "All Workloads":
            filtered_alerts = filtered_alerts[
                filtered_alerts["workload_name"]
                == selected_workload
            ]

        if selected_severity != "All Severities":
            filtered_alerts = filtered_alerts[
                filtered_alerts["severity"]
                == selected_severity
            ]

        if selected_alert_pod != "All Pods":
            filtered_alerts = filtered_alerts[
                filtered_alerts["pod"] == selected_alert_pod
            ]

        if search_text.strip():

            search_columns = [
                "namespace",
                "workload_type",
                "workload_name",
                "pod",
                "container",
                "message",
            ]

            search_mask = pd.Series(
                False,
                index=filtered_alerts.index,
            )

            for column in search_columns:
                search_mask = search_mask | (
                    filtered_alerts[column]
                    .astype(str)
                    .str.contains(
                        search_text.strip(),
                        case=False,
                        na=False,
                        regex=False,
                    )
                )

            filtered_alerts = filtered_alerts[search_mask]

        # ------------------------------------------
        # FILTERED ALERT RESULTS
        # ------------------------------------------

        st.divider()

        result_col1, result_col2 = st.columns(2)

        result_col1.metric(
            "Matching Alerts",
            len(filtered_alerts),
        )

        result_col2.metric(
            "Affected Pods",
            filtered_alerts["pod"].nunique()
            if not filtered_alerts.empty else 0,
        )

        if not filtered_alerts.empty:

            st.markdown("### Alert Details")

            st.dataframe(
                filtered_alerts[
                    [
                        "severity",
                        "namespace",
                        "workload_type",
                        "workload_name",
                        "pod",
                        "container",
                        "message",
                    ]
                ],
                width="stretch",
                hide_index=True,
            )

        else:
            st.success(
                "No alerts match the selected filters. "
                "Your selected view is clear."
            )

    else:
        st.success("No active alerts. Your cluster looks healthy!")


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.write("")
st.divider()

st.markdown(
    """
    <div style="text-align:center; color:#7f8b9b;">
        KubeWatch | Kubernetes Multi-Cluster Monitoring Dashboard
        <br>
        Built with Python, Streamlit and Kubernetes API
    </div>
    """,
    unsafe_allow_html=True,
)
