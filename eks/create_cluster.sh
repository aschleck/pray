#!/usr/bin/env bash

CLUSTER_NAME="REPLACE_ME"

AWS_DEFAULT_REGION="us-west-2"
AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
K8S_VERSION=1.28

cd $(dirname $(readlink -f $0))

aws cloudformation deploy \
    --stack-name "karpenter-${CLUSTER_NAME}" \
    --template-file "./cloudformation.yaml" \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides "ClusterName=${CLUSTER_NAME}"

eksctl create cluster -f - <<EOF
---
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ${CLUSTER_NAME}
  region: ${AWS_DEFAULT_REGION}
  version: "${K8S_VERSION}"
  tags:
    karpenter.sh/discovery: ${CLUSTER_NAME}

iam:
  withOIDC: true
  podIdentityAssociations:
  - namespace: "kube-system"
    serviceAccountName: karpenter
    roleName: ${CLUSTER_NAME}-karpenter
    permissionPolicyARNs:
    - arn:aws:iam::${AWS_ACCOUNT_ID}:policy/KarpenterControllerPolicy-${CLUSTER_NAME}

## Optionally run on fargate or on k8s 1.23
# Pod Identity is not available on fargate  
# https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html
# iam:
#   withOIDC: true
#   serviceAccounts:
#   - metadata:
#       name: karpenter
#       namespace: "kube-system"
#     roleName: ${CLUSTER_NAME}-karpenter
#     attachPolicyARNs:
#     - arn:aws:iam::${AWS_ACCOUNT_ID}:policy/KarpenterControllerPolicy-${CLUSTER_NAME}
#     roleOnly: true

iamIdentityMappings:
- arn: "arn:aws:iam::${AWS_ACCOUNT_ID}:role/KarpenterNode-${CLUSTER_NAME}"
  username: system:node:{{EC2PrivateDNSName}}
  groups:
  - system:bootstrappers
  - system:nodes
  ## If you intend to run Windows workloads, the kube-proxy group should be specified.
  # For more information, see https://github.com/aws/karpenter/issues/5099.
  # - eks:kube-proxy-windows

managedNodeGroups:
- instanceType: t3.medium
  amiFamily: AmazonLinux2
  name: ${CLUSTER_NAME}-t3.medium
  desiredCapacity: 1
  minSize: 1
  maxSize: 2

addons:
- name: eks-pod-identity-agent

## Optionally run on fargate
# fargateProfiles:
# - name: karpenter
#  selectors:
#  - namespace: "kube-system"
EOF

CLUSTER_ENDPOINT="$(aws eks describe-cluster --name "${CLUSTER_NAME}" --query "cluster.endpoint" --output text)"
KARPENTER_IAM_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${CLUSTER_NAME}-karpenter"

echo "${CLUSTER_ENDPOINT}" "${KARPENTER_IAM_ROLE_ARN}"
