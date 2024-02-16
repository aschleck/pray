#!/usr/bin/env bash

CLUSTER_NAME="REPLACE_ME"

helm template karpenter \
    oci://public.ecr.aws/karpenter/karpenter \
    --include-crds \
    --version "v0.34.0" \
    --namespace "kube-system" \
    --set "settings.clusterName=${CLUSTER_NAME}" \
    --set "settings.interruptionQueue=${CLUSTER_NAME}" \
    --set controller.resources.requests.cpu=0.1 \
    --set controller.resources.requests.memory=256Mi \
    --set controller.resources.limits.cpu=1 \
    --set controller.resources.limits.memory=1Gi \
    --set replicas=1 \
    | grep -v "app.kubernetes.io/managed-by: Helm" \
    | grep -v "helm.sh/chart: " \
    > karpenter.yaml

helm template nvidia-device-plugin \
    nvidia-device-plugin \
    --repo "https://nvidia.github.io/k8s-device-plugin" \
    --namespace "kube-system" \
    --include-crds \
    --set-json 'nodeSelector={"nvidia.com/gpu": "true"}' \
    | grep -v "app.kubernetes.io/managed-by: Helm" \
    | grep -v "helm.sh/chart: " \
    > nvidia-device-plugin.yaml
