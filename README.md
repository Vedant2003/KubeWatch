# 🚀 KubeWatch
### Kubernetes Multi-Cluster Monitoring & Alerting Dashboard

KubeWatch is a Python-based Kubernetes monitoring dashboard built with Streamlit. It provides a centralized view of multiple Kubernetes clusters, allowing users to monitor nodes, pods, resource utilization, workloads and cluster health through an interactive dashboard.

The project integrates with the Kubernetes Python Client and Metrics Server to retrieve real-time resource metrics and identify potential issues within Kubernetes workloads.

**Version:** `v1.0.0`  
**Status:** Initial Release  
**Technology:** Python | Kubernetes | Streamlit

---

## ✨ Features

### 1. Multi-Cluster Monitoring
- Connect to multiple Kubernetes clusters.
- Switch between available Kubernetes contexts.
- Monitor clusters from a centralized dashboard.

### 2. Cluster Overview
- Total number of nodes.
- Total number of pods.
- Running pods.
- Pending pods.
- Failed or unknown pods.

### 3. Node Monitoring
- Monitor Kubernetes nodes.
- Retrieve CPU utilization.
- Retrieve memory utilization.
- Visualize resource usage through interactive charts.

### 4. Pod Monitoring
- View pods across namespaces.
- Filter pods by namespace.
- Monitor pod status and restart counts.
- Identify the Kubernetes workload associated with a pod.
- View container readiness information.

### 5. Resource Analytics
- Pod-level CPU monitoring.
- Pod-level memory monitoring.
- Container-level resource metrics.
- Interactive resource utilization charts.

### 6. Intelligent Alert Engine

KubeWatch identifies common Kubernetes pod and container issues:

| Condition | Severity |
|---|---|
| Pod Failed | Critical |
| Pod not Running | Warning |
| CrashLoopBackOff | Critical |
| ImagePullBackOff | Critical |
| ErrImagePull | Critical |
| Container not ready | Warning |
| Container restarts ≥ 5 | Info |

### 7. Alert Management
- Filter alerts by namespace.
- Filter by workload type and workload name.
- Filter by severity.
- Filter by pod.
- Search across alert details.
- View affected pods and matching alert counts.

### 8. Automatic Dashboard Refresh
- Automatic refresh every 10 seconds.
- Manual refresh option.
- Cached cluster data to reduce unnecessary API requests.

---

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core programming language |
| Streamlit | Interactive dashboard |
| Kubernetes Python Client | Kubernetes API integration |
| Metrics Server | Resource metrics |
| Pandas | Data processing |
| Plotly | Interactive charts |
| streamlit-autorefresh | Automatic dashboard refresh |

---

## 🏗️ Project Structure

```text
KubeWatch/
│
├── app.py                  # Streamlit dashboard
├── kubernetes_client.py    # Kubernetes API integration
├── alerts.py               # Alert generation engine
├── requirements.txt        # Python dependencies
├── README.md               # Project documentation
└── .gitignore              # Git ignored files
```

---

## ⚙️ Installation & Setup

### Prerequisites

Make sure you have:

- Python 3.10 or later
- Kubernetes cluster (Kind, Minikube or another Kubernetes environment)
- kubectl
- Kubernetes Metrics Server
- Git

### Step 1: Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/KubeWatch.git

cd KubeWatch
```

### Step 2: Create a Virtual Environment

```bash
python -m venv .venv
```

Activate it:

**Windows Git Bash:**
```bash
source .venv/Scripts/activate
```

**Windows CMD:**
```cmd
.venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Kubernetes Access

Make sure your Kubernetes clusters are running and your kubeconfig contains the contexts you want to monitor.

Check available contexts:

```bash
kubectl config get-contexts
```

Check the active context:

```bash
kubectl config current-context
```

Verify cluster connectivity:

```bash
kubectl get nodes
```

For resource monitoring, ensure Metrics Server is installed and working:

```bash
kubectl top nodes
kubectl top pods -A
```

### Step 5: Run KubeWatch

```bash
streamlit run app.py
```

The dashboard will be available at:

```text
http://localhost:8501
```

---

## 🔍 How It Works

KubeWatch communicates with Kubernetes clusters using the Kubernetes Python Client.

1. The user selects a Kubernetes context.
2. KubeWatch establishes a connection to the selected cluster.
3. Kubernetes API calls retrieve node and pod information.
4. Metrics Server provides CPU and memory usage data.
5. The alert engine analyzes pod and container states.
6. Streamlit displays monitoring information through interactive dashboards and charts.

---

## 🚧 Future Improvements

Planned features for upcoming releases:

- [ ] Docker support.
- [ ] Historical CPU and memory metrics.
- [ ] Advanced alert management.
- [ ] Email and Microsoft Teams notifications.
- [ ] Kubernetes RBAC integration.
- [ ] Unit and integration testing.
- [ ] GitHub Actions CI/CD pipeline.
- [ ] Kubernetes deployment manifests.

---

## 📌 Version History

| Version | Description |
|---|---|
| v1.0.0 | Initial release: multi-cluster monitoring, resource analytics, workload identification and alert engine |
| v1.1.0 | Planned: Docker support and deployment improvements |
| v1.2.0 | Planned: historical metrics and advanced monitoring |
| v1.3.0 | Planned: notifications, testing and CI/CD |
| v2.0.0 | Planned: production-oriented deployment and RBAC |

---

## 🔐 Security Notes

- Never commit Kubernetes kubeconfig files.
- Never expose cluster credentials, certificates or tokens.
- Use appropriate Kubernetes RBAC permissions.
- Avoid granting unnecessary cluster-wide access.

---

## 👨‍💻 Author

**Vedant Agnihotri**

KubeWatch is a hands-on project focused on Kubernetes monitoring, Python automation and cloud-native infrastructure.

---

⭐ If you find this project useful, consider giving it a star!

**KubeWatch – Monitor your Kubernetes clusters from one dashboard.**
