#!/bin/bash

# ComfyUI Setup Script
# This script helps set up ComfyUI for image generation

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}➜ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

echo "=========================================="
echo "  ComfyUI Setup for Marketing Assistant"
echo "=========================================="
echo ""

# Detect operating system
OS_TYPE="unknown"
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS_TYPE="linux"
fi

# macOS setup path
if [ "$OS_TYPE" = "macos" ]; then
    print_info "Detected macOS"

    # Check for Apple Silicon
    if [[ $(uname -m) == "arm64" ]]; then
        print_success "Apple Silicon detected (M1/M2/M3/M4)"
        print_info "For best performance, install ComfyUI natively instead of Docker"
        echo ""
        echo "Docker on macOS doesn't support GPU passthrough."
        echo "Native installation will use MPS (Metal) for acceleration."
        echo ""
        print_info "Quick native installation:"
        echo ""
        echo "  1. Install Python:"
        echo "     brew install python@3.11"
        echo ""
        echo "  2. Clone ComfyUI:"
        echo "     git clone https://github.com/comfyanonymous/ComfyUI.git"
        echo "     cd ComfyUI"
        echo ""
        echo "  3. Setup environment:"
        echo "     python3.11 -m venv venv"
        echo "     source venv/bin/activate"
        echo "     pip install torch torchvision torchaudio"
        echo "     pip install -r requirements.txt"
        echo ""
        echo "  4. Run ComfyUI:"
        echo "     python main.py"
        echo ""
        echo "Access at: http://localhost:8188"
        echo ""
        print_info "Would you like to download models to ./comfyui_models anyway? (y/n)"
        read -r download_models

        if [ "$download_models" = "y" ] || [ "$download_models" = "Y" ]; then
            # Create models directory
            mkdir -p comfyui_models/checkpoints
            mkdir -p comfyui_models/vae
            mkdir -p comfyui_models/loras
            print_success "Models directory created"

            # Download model
            if [ ! -f "comfyui_models/checkpoints/sd_xl_turbo_1.0_fp16.safetensors" ]; then
                print_info "Downloading SDXL Turbo 1.0 FP16 (~6.9 GB)..."
                curl -L -o comfyui_models/checkpoints/sd_xl_turbo_1.0_fp16.safetensors \
                    "https://huggingface.co/stabilityai/sdxl-turbo/resolve/main/sd_xl_turbo_1.0_fp16.safetensors"
                print_success "Model downloaded to ./comfyui_models/checkpoints/"
                print_info "Copy this model to your ComfyUI installation's models/checkpoints folder"
            else
                print_success "Model already exists"
            fi
        fi
        echo ""
        print_info "See COMFYUI_SETUP.md for detailed macOS instructions"
        exit 0
    else
        print_info "Intel Mac detected - will use CPU mode (slow)"
    fi
fi

# Linux/Intel Mac - Check for NVIDIA GPU
print_info "Checking for NVIDIA GPU..."
if ! command -v nvidia-smi &> /dev/null; then
    print_error "NVIDIA GPU not detected or nvidia-smi not available"
    print_info "Options:"
    echo "  1. Run ComfyUI on CPU (very slow, not recommended)"
    echo "  2. Use OpenAI for image generation instead"
    echo "  3. Install on a machine with NVIDIA GPU"
    echo ""
    if [ "$OS_TYPE" = "macos" ]; then
        print_info "On macOS, install ComfyUI natively for MPS acceleration"
        print_info "See COMFYUI_SETUP.md for instructions"
    fi
    exit 1
fi

print_success "NVIDIA GPU detected"
nvidia-smi --query-gpu=name --format=csv,noheader

# Check Docker
print_info "Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running"
    exit 1
fi
print_success "Docker is running"

# Check for NVIDIA Docker runtime
print_info "Checking NVIDIA Docker runtime..."
if ! docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
    print_error "NVIDIA Docker runtime not available"
    print_info "Install nvidia-container-toolkit:"
    echo "  https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
    exit 1
fi
print_success "NVIDIA Docker runtime available"

# Create models directory
print_info "Creating models directory..."
mkdir -p comfyui_models/checkpoints
mkdir -p comfyui_models/vae
mkdir -p comfyui_models/loras
print_success "Models directory created"

# Check if SDXL Turbo model exists
if [ ! -f "comfyui_models/checkpoints/sd_xl_turbo_1.0_fp16.safetensors" ]; then
    print_info "SDXL Turbo model not found"
    print_info "Would you like to download it? (~6.9 GB) (y/n)"
    read -r download_model

    if [ "$download_model" = "y" ] || [ "$download_model" = "Y" ]; then
        print_info "Downloading SDXL Turbo 1.0 FP16..."
        print_info "This may take a while depending on your connection..."

        curl -L -o comfyui_models/checkpoints/sd_xl_turbo_1.0_fp16.safetensors \
            "https://huggingface.co/stabilityai/sdxl-turbo/resolve/main/sd_xl_turbo_1.0_fp16.safetensors"

        print_success "SDXL Turbo model downloaded"
    else
        print_info "Skipping model download"
        print_info "You can download models manually to: ./comfyui_models/checkpoints/"
        print_info "Recommended: SDXL Turbo from https://huggingface.co/stabilityai/sdxl-turbo"
    fi
else
    print_success "SDXL Turbo model found"
fi

# Start ComfyUI
print_info "Starting ComfyUI with GPU support..."
docker compose --profile gpu up -d comfyui

print_info "Waiting for ComfyUI to start..."
sleep 5

# Check if ComfyUI is running
if docker ps | grep -q "marketer_comfyui"; then
    print_success "ComfyUI is running!"
    echo ""
    echo "=========================================="
    echo "  ComfyUI Access Information"
    echo "=========================================="
    echo ""
    echo "  Web UI:      http://localhost:8188"
    echo "  API:         http://localhost:8188/api"
    echo ""
    echo "  Model Location: ./comfyui_models/checkpoints/"
    echo ""
    echo "=========================================="
    echo ""
    print_info "Next steps:"
    echo "  1. Open http://localhost:8188 in your browser"
    echo "  2. Verify the model is loaded in the CheckpointLoaderSimple node"
    echo "  3. Update your settings to use ComfyUI for image generation"
    echo ""
else
    print_error "ComfyUI failed to start"
    print_info "Check logs with: docker compose logs comfyui"
fi
