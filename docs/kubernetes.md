# Kubernetes Integration Guide

Chaos Platform supports Kubernetes in three ways:

1. **Lightweight gRPC Agent**: A DaemonSet running on nodes that injects chaos at the OS level (CPU, Memory, Process Kill).
2. **Chaos Mesh Integration**: Native integration with the Chaos Mesh API for `NetworkChaos`, `PodChaos`, and `StressChaos`.
3. **LitmusChaos Integration**: Native integration with Litmus `ChaosEngine` resources.

## 1. gRPC Agent Setup (mTLS)

The agent runs as a privileged DaemonSet to execute OS-level chaos. Communication is secured via mTLS.

### Prerequisites
- cert-manager installed in the cluster.

### Deployment

```bash
kubectl apply -f k8s/agent/manifests/tls.yaml
kubectl apply -f k8s/agent/manifests/rbac.yaml
kubectl apply -f k8s/agent/manifests/service.yaml
kubectl apply -f k8s/agent/manifests/daemonset.yaml
```

The agent listens on `50051` (gRPC) and `8081` (Health check).

## 2. Kubernetes Operator

The platform includes a Kopf-based operator to manage chaos via GitOps.

### Deployment

```bash
kubectl apply -f k8s/operator/crds/chaosexperiment_crd.yaml
kubectl apply -f k8s/operator/manifests/operator-rbac.yaml
kubectl apply -f k8s/operator/manifests/operator-deployment.yaml
```

### Usage Example

```yaml
apiVersion: chaos-platform.io/v1alpha1
kind: ChaosExperiment
metadata:
  name: cpu-spike-test
spec:
  experiment: cpu_stress
  target: demo-node-1
  targetType: kubernetes
  durationSeconds: 120
```

## 3. Chaos Mesh & LitmusChaos Modules

If Chaos Mesh or LitmusChaos is installed, you can use the corresponding modules directly in your experiments without the gRPC agent:
- `chaos_mesh_network`
- `chaos_mesh_pod`
- `chaos_mesh_stress`
- `litmus_engine`
