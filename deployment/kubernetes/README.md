# Kubernetes Deployment Guide for OGX

This guide demonstrates how to deploy OGX and vLLM servers in a Kubernetes cluster using Kind and the OGX Kubernetes operator.

## Overview

This deployment uses:
- **vLLM**: OpenAI-compatible inference server for serving LLM models
- **OGX**: Unified API for interacting with LLM models
- **OGX Kubernetes Operator**: Manages OGX deployments via custom resources

## Prerequisites

### 1. Create a Kind Cluster

```bash
kind create cluster --image kindest/node:v1.32.0 --name ogx-test
```

### 2. Set Up Hugging Face Token

Export your Hugging Face token as a base64-encoded environment variable:

```bash
export HF_TOKEN=$(echo -n "your-hugging-face-token" | base64)
```

This token is required for downloading models from Hugging Face.

Edit `vllm-serve/base/00-hf-token-secret.yaml` with your base64-encoded token.

## Deployment Steps

### Step 1: Deploy vLLM Server

Deploy the vLLM server using Kustomize. Choose the overlay matching your CPU architecture:

```bash
# For x86_64 (Intel/AMD)
kubectl apply -k vllm-serve/overlays/x86_64/

# For ARM64 (Apple Silicon, ARM servers)
kubectl apply -k vllm-serve/overlays/arm64/
```

The overlays use architecture-specific container images:
- x86_64: `public.ecr.aws/q9t5s3a7/vllm-cpu-release-repo:latest`
- ARM64: `public.ecr.aws/q9t5s3a7/vllm-arm64-cpu-release-repo:latest`

The vLLM server will:
- Serve an OpenAI-compatible API on port 8000
- Mount model cache at `/root/.cache/huggingface`
- Use the HF token for authentication

### Step 2: Install OGX Operator

Install the OGX Kubernetes operator:

```bash
# Option 1: Apply from remote URL
kubectl apply -f https://raw.githubusercontent.com/ogx-ai/ogx-k8s-operator/main/release/operator.yaml
```

Verify the operator is running:

```bash
kubectl get pods -n ogx-k8s-operator-system
```

### Step 3: Deploy OGX

Create an `OGXServer` custom resource:

```bash
# Create OGX distribution
kubectl apply -f ogx/00-lls-cr.yaml
```

This creates a OGX deployment that:
- Uses the "starter" distribution
- Exposes port 8321
- Connects to the vLLM service at `http://vllm-server.default.svc.cluster.local:8000/v1`
- Allocates 20Gi of storage for OGX data

### Step 4: Test the Deployment

Forward the OGX port to your local machine:

```bash
kubectl port-forward svc/ogx-vllm 8321:8321
```

Test the deployment using the OGX client:

```bash
ogx-client --endpoint http://localhost:8321 inference chat-completion --message "hello, what model are you?"
```

## Configuration Files

The deployment consists of the following YAML files:

### vLLM Server (`vllm-serve/`)

```text
vllm-serve/
├── base/                           # Base Kubernetes resources
│   ├── kustomization.yaml
│   ├── 00-hf-token-secret.yaml    # Secret containing Hugging Face token
│   ├── 01-vllm-models-pvc.yaml    # PersistentVolumeClaim (50Gi) for model storage
│   ├── 02-vllm-server-deploy.yaml # vLLM server deployment
│   └── 03-vllm-server-service.yaml # ClusterIP service exposing vLLM on port 8000
└── overlays/                       # Architecture-specific overlays
    ├── x86_64/                     # Intel/AMD CPU variant
    │   └── kustomization.yaml
    └── arm64/                      # ARM64 CPU variant
        └── kustomization.yaml
```

### OGX (`ogx/`)
- `00-lls-cr.yaml` - OGXServer custom resource

## Troubleshooting

### vLLM Issues

Check pod status:
```bash
kubectl get pods -l app.kubernetes.io/name=vllm
kubectl logs -l app.kubernetes.io/name=vllm
```

Verify service connectivity from a debug pod:
```bash
kubectl run curl --rm -it --image=curlimages/curl -- /bin/sh
curl http://vllm-server.default.svc.cluster.local:8000/v1/models
```

### OGX Issues

Inspect the custom resource:
```bash
kubectl describe ogxserver ogx-vllm
```

Check operator logs:
```bash
kubectl logs -n ogx-k8s-operator-system -l control-plane=controller-manager
```

Check OGX pod:
```bash
kubectl get pods -l app.kubernetes.io/instance=ogx-vllm
kubectl logs -l app.kubernetes.io/instance=ogx-vllm
```

## Customization

### Using a Different Model

Edit `vllm-serve/base/02-vllm-server-deploy.yaml` and change the model in the args:

```yaml
args: ["serve", "your-model-name"]
```

### Custom OGX Configuration

To use a custom `config.yaml`, create a ConfigMap and reference it in the `OGXServer` resource. See the [OGXServer API documentation](https://github.com/ogx-ai/ogx-k8s-operator) for details.

## Related Resources

- [OGX Documentation](https://ogx-ai.github.io/)
- [OGX Kubernetes Operator](https://github.com/ogx-ai/ogx-k8s-operator)
- [vLLM Documentation](https://docs.vllm.ai)
- [OGXServer API Reference](https://github.com/ogx-ai/ogx-k8s-operator/blob/main/docs/api-reference.md)

## Clean Up

To remove all resources:

```bash
# Delete OGX deployment
kubectl delete -f ogx/00-lls-cr.yaml

# Delete vLLM resources (use the same overlay you deployed with)
kubectl delete -k vllm-serve/overlays/x86_64/  # or arm64

# Delete operator
kubectl delete -f https://raw.githubusercontent.com/ogx-ai/ogx-k8s-operator/main/release/operator.yaml

# Delete Kind cluster
kind delete cluster --name ogx-test
```
