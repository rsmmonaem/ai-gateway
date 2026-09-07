#!/usr/bin/env bash
set -e

echo "=== Deploying AI Model Gateway to Kubernetes ==="

# 1. Build Gateway container image locally
echo "Step 1: Building Docker image 'ai-gateway:latest'..."
docker build -t ai-gateway:latest ./backend

# 2. Check kubectl connection
if ! command -v kubectl &> /dev/null; then
    echo "kubectl not found. Please install via: brew install kubectl"
    exit 1
fi

echo "Connected to Kubernetes cluster: $(kubectl config current-context)"

# 3. Apply manifests using Kustomize
echo "Step 2: Applying Kubernetes manifests..."
kubectl apply -k ./infrastructure/k8s

# 4. Wait for pods to be ready
echo "Step 3: Waiting for pods to become ready in namespace 'ai-gateway'..."
kubectl rollout status deployment/postgres -n ai-gateway --timeout=60s || true
kubectl rollout status deployment/redis -n ai-gateway --timeout=60s || true
kubectl rollout status deployment/ai-gateway -n ai-gateway --timeout=60s || true

echo ""
echo "=== Deployment Status ==="
kubectl get pods,svc,hpa -n ai-gateway

echo ""
echo "To port-forward the Gateway locally:"
echo "kubectl port-forward svc/ai-gateway-service -n ai-gateway 8000:8000"
echo "=== Kubernetes Deployment Complete ==="
