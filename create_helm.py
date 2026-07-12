import os

helm_dir = "helm/chaos-platform"
os.makedirs(helm_dir, exist_ok=True)
os.makedirs(f"{helm_dir}/templates/crds", exist_ok=True)

chart_yaml = """apiVersion: v2
name: chaos-platform
description: A Helm chart for the Chaos Engineering Platform
type: application
version: 0.1.0
appVersion: "1.0.0"
dependencies:
  - name: kube-prometheus-stack
    version: "61.3.0"
    repository: "https://prometheus-community.github.io/helm-charts"
    condition: prometheus.enabled
"""

values_yaml = """replicaCount: 1

image:
  repository: myrepo/chaos-platform
  pullPolicy: IfNotPresent
  tag: "latest"

operator:
  image:
    repository: myrepo/chaos-operator
    tag: "latest"
  replicaCount: 1

agent:
  image:
    repository: myrepo/chaos-agent
    tag: "latest"

service:
  type: ClusterIP
  port: 8000

ingress:
  enabled: false
  className: ""
  annotations: {}
  hosts:
    - host: chart-example.local
      paths:
        - path: /
          pathType: ImplementationSpecific

resources: {}

autoscaling:
  enabled: false
  minReplicas: 1
  maxReplicas: 100
  targetCPUUtilizationPercentage: 80

nodeSelector: {}

tolerations: []

affinity: {}

prometheus:
  enabled: false
"""

deployment_yaml = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "chaos-platform.fullname" . }}
  labels:
    {{- include "chaos-platform.labels" . | nindent 4 }}
spec:
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ .Values.replicaCount }}
  {{- end }}
  selector:
    matchLabels:
      {{- include "chaos-platform.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      {{- with .Values.podAnnotations }}
      annotations:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      labels:
        {{- include "chaos-platform.selectorLabels" . | nindent 8 }}
    spec:
      serviceAccountName: {{ include "chaos-platform.serviceAccountName" . }}
      securityContext:
        {{- toYaml .Values.podSecurityContext | nindent 8 }}
      containers:
        - name: {{ .Chart.Name }}
          securityContext:
            {{- toYaml .Values.securityContext | nindent 12 }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: {{ .Values.service.port }}
              protocol: TCP
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
"""

helpers_tpl = """{{/*
Expand the name of the chart.
*/}}
{{- define "chaos-platform.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "chaos-platform.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "chaos-platform.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "chaos-platform.labels" -}}
helm.sh/chart: {{ include "chaos-platform.chart" . }}
{{ include "chaos-platform.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "chaos-platform.selectorLabels" -}}
app.kubernetes.io/name: {{ include "chaos-platform.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "chaos-platform.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "chaos-platform.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
"""

service_yaml = """apiVersion: v1
kind: Service
metadata:
  name: {{ include "chaos-platform.fullname" . }}
  labels:
    {{- include "chaos-platform.labels" . | nindent 4 }}
spec:
  type: {{ .Values.service.type }}
  ports:
    - port: {{ .Values.service.port }}
      targetPort: http
      protocol: TCP
      name: http
  selector:
    {{- include "chaos-platform.selectorLabels" . | nindent 4 }}
"""

ingress_yaml = """{{- if .Values.ingress.enabled -}}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ include "chaos-platform.fullname" . }}
  labels:
    {{- include "chaos-platform.labels" . | nindent 4 }}
  {{- with .Values.ingress.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
spec:
  {{- if .Values.ingress.className }}
  ingressClassName: {{ .Values.ingress.className }}
  {{- end }}
  rules:
    {{- range .Values.ingress.hosts }}
    - host: {{ .host | quote }}
      http:
        paths:
          {{- range .paths }}
          - path: {{ .path }}
            pathType: {{ .pathType }}
            backend:
              service:
                name: {{ include "chaos-platform.fullname" $ }}
                port:
                  number: {{ $.Values.service.port }}
          {{- end }}
    {{- end }}
{{- end }}
"""

configmap_yaml = """apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "chaos-platform.fullname" . }}-config
  labels:
    {{- include "chaos-platform.labels" . | nindent 4 }}
data:
  config.yaml: |
    server:
      port: 8000
"""

secret_yaml = """apiVersion: v1
kind: Secret
metadata:
  name: {{ include "chaos-platform.fullname" . }}-secret
  labels:
    {{- include "chaos-platform.labels" . | nindent 4 }}
type: Opaque
data:
  # Base64 encoded values
  example-key: {{ "example-value" | b64enc | quote }}
"""

serviceaccount_yaml = """apiVersion: v1
kind: ServiceAccount
metadata:
  name: {{ include "chaos-platform.fullname" . }}
  labels:
    {{- include "chaos-platform.labels" . | nindent 4 }}
"""

rbac_yaml = """apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: {{ include "chaos-platform.fullname" . }}-role
rules:
  - apiGroups: ["*"]
    resources: ["*"]
    verbs: ["*"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: {{ include "chaos-platform.fullname" . }}-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: {{ include "chaos-platform.fullname" . }}-role
subjects:
  - kind: ServiceAccount
    name: {{ include "chaos-platform.fullname" . }}
    namespace: {{ .Release.Namespace }}
"""

operator_deployment_yaml = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "chaos-platform.fullname" . }}-operator
  labels:
    {{- include "chaos-platform.labels" . | nindent 4 }}
    app: chaos-operator
spec:
  replicas: {{ .Values.operator.replicaCount }}
  selector:
    matchLabels:
      {{- include "chaos-platform.selectorLabels" . | nindent 6 }}
      app: chaos-operator
  template:
    metadata:
      labels:
        {{- include "chaos-platform.selectorLabels" . | nindent 8 }}
        app: chaos-operator
    spec:
      serviceAccountName: {{ include "chaos-platform.fullname" . }}
      containers:
        - name: operator
          image: "{{ .Values.operator.image.repository }}:{{ .Values.operator.image.tag }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
"""

agent_daemonset_yaml = """apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: {{ include "chaos-platform.fullname" . }}-agent
  labels:
    {{- include "chaos-platform.labels" . | nindent 4 }}
    app: chaos-agent
spec:
  selector:
    matchLabels:
      {{- include "chaos-platform.selectorLabels" . | nindent 6 }}
      app: chaos-agent
  template:
    metadata:
      labels:
        {{- include "chaos-platform.selectorLabels" . | nindent 8 }}
        app: chaos-agent
    spec:
      serviceAccountName: {{ include "chaos-platform.fullname" . }}
      containers:
        - name: agent
          image: "{{ .Values.agent.image.repository }}:{{ .Values.agent.image.tag }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
"""

chaosexperiment_crd_yaml = """apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: chaosexperiments.chaos-platform.io
spec:
  group: chaos-platform.io
  names:
    kind: ChaosExperiment
    listKind: ChaosExperimentList
    plural: chaosexperiments
    singular: chaosexperiment
  scope: Namespaced
  versions:
    - name: v1alpha1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              required:
                - experiment
              properties:
                experiment:
                  type: string
                target:
                  type: string
                targetType:
                  type: string
                durationSeconds:
                  type: integer
                dryRun:
                  type: boolean
                schedule:
                  type: string
                hypothesisOverride:
                  type: object
                  x-kubernetes-preserve-unknown-fields: true
                argoWorkflow:
                  type: string
                tektonPipeline:
                  type: string
            status:
              type: object
              properties:
                phase:
                  type: string
                startedAt:
                  type: string
                finishedAt:
                  type: string
                result:
                  type: string
                rollbackResult:
                  type: string
                hypothesisResults:
                  type: array
                  items:
                    type: string
      subresources:
        status: {}
"""

chaosschedule_crd_yaml = """apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: chaosschedules.chaos-platform.io
spec:
  group: chaos-platform.io
  names:
    kind: ChaosSchedule
    listKind: ChaosScheduleList
    plural: chaosschedules
    singular: chaosschedule
  scope: Namespaced
  versions:
    - name: v1alpha1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              required:
                - schedule
                - experimentTemplate
              properties:
                schedule:
                  type: string
                experimentTemplate:
                  type: object
                  x-kubernetes-preserve-unknown-fields: true
            status:
              type: object
              properties:
                lastRun:
                  type: string
                nextRun:
                  type: string
      subresources:
        status: {}
"""

hpa_yaml = """{{- if .Values.autoscaling.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include "chaos-platform.fullname" . }}
  labels:
    {{- include "chaos-platform.labels" . | nindent 4 }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include "chaos-platform.fullname" . }}
  minReplicas: {{ .Values.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.autoscaling.maxReplicas }}
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: {{ .Values.autoscaling.targetCPUUtilizationPercentage }}
{{- end }}
"""

pdb_yaml = """apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: {{ include "chaos-platform.fullname" . }}
  labels:
    {{- include "chaos-platform.labels" . | nindent 4 }}
spec:
  minAvailable: 1
  selector:
    matchLabels:
      {{- include "chaos-platform.selectorLabels" . | nindent 6 }}
"""

networkpolicy_yaml = """apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ include "chaos-platform.fullname" . }}
  labels:
    {{- include "chaos-platform.labels" . | nindent 4 }}
spec:
  podSelector:
    matchLabels:
      {{- include "chaos-platform.selectorLabels" . | nindent 6 }}
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - {}
  egress:
    - {}
"""

readme_md = """# Chaos Engineering Platform Helm Chart

This Helm chart deploys the Chaos Engineering Platform including its backend API, operator, and daemonset agent.

## Prerequisites

- Kubernetes 1.20+
- Helm 3.0+

## Installing the Chart

```bash
helm install chaos-platform ./helm/chaos-platform
```
"""

files = {
    f"{helm_dir}/Chart.yaml": chart_yaml,
    f"{helm_dir}/values.yaml": values_yaml,
    f"{helm_dir}/templates/_helpers.tpl": helpers_tpl,
    f"{helm_dir}/templates/deployment.yaml": deployment_yaml,
    f"{helm_dir}/templates/service.yaml": service_yaml,
    f"{helm_dir}/templates/ingress.yaml": ingress_yaml,
    f"{helm_dir}/templates/configmap.yaml": configmap_yaml,
    f"{helm_dir}/templates/secret.yaml": secret_yaml,
    f"{helm_dir}/templates/serviceaccount.yaml": serviceaccount_yaml,
    f"{helm_dir}/templates/rbac.yaml": rbac_yaml,
    f"{helm_dir}/templates/operator-deployment.yaml": operator_deployment_yaml,
    f"{helm_dir}/templates/agent-daemonset.yaml": agent_daemonset_yaml,
    f"{helm_dir}/templates/crds/chaosexperiment.yaml": chaosexperiment_crd_yaml,
    f"{helm_dir}/templates/crds/chaosschedule.yaml": chaosschedule_crd_yaml,
    f"{helm_dir}/templates/hpa.yaml": hpa_yaml,
    f"{helm_dir}/templates/pdb.yaml": pdb_yaml,
    f"{helm_dir}/templates/networkpolicy.yaml": networkpolicy_yaml,
    f"{helm_dir}/README.md": readme_md,
}

for path, content in files.items():
    with open(path, "w") as f:
        f.write(content)

print("Created Helm chart")
