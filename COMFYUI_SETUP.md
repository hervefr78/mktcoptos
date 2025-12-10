# ComfyUI Setup Guide

ComfyUI is a powerful node-based image generation tool using Stable Diffusion models. This guide helps you set it up with the Marketing Assistant.

## Requirements

### Linux with NVIDIA GPU (Best Performance)

- **NVIDIA GPU** with at least 6GB VRAM
- **CUDA support** (drivers installed)
- **NVIDIA Container Toolkit** for Docker
- **6-10 GB** disk space for models

### macOS with Apple Silicon (M1/M2/M3/M4)

- **Native installation** recommended (Docker doesn't support GPU passthrough on Mac)
- **8GB+ RAM** recommended
- **6-10 GB** disk space for models
- Uses MPS (Metal Performance Shaders) for acceleration

### CPU Only (Not Recommended)

- Image generation will be **very slow** (10-30 minutes per image)
- Only use if GPU is not available
- Consider using OpenAI image generation instead

## Quick Start

### Linux with NVIDIA GPU

```bash
./setup-comfyui.sh
```

This script will:
1. Check for NVIDIA GPU and Docker
2. Create model directories
3. Optionally download SDXL Turbo model (~6.9 GB)
4. Start ComfyUI with GPU support

### macOS (Apple Silicon)

```bash
./setup-comfyui.sh
```

This script will:
1. Detect macOS and Apple Silicon
2. Guide you through native ComfyUI installation
3. Create model directories
4. Optionally download SDXL Turbo model

**Note**: For best performance on Mac, install ComfyUI natively instead of using Docker.

## macOS Native Installation (Recommended for Mac)

### 1. Install Dependencies

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python and Git
brew install python@3.11 git
```

### 2. Clone ComfyUI

```bash
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
```

### 3. Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
```

### 4. Install Requirements

```bash
pip install --upgrade pip
pip install torch torchvision torchaudio
pip install -r requirements.txt
```

### 5. Download Models

```bash
mkdir -p models/checkpoints
cd models/checkpoints
curl -L -o sd_xl_turbo_1.0_fp16.safetensors \
    "https://huggingface.co/stabilityai/sdxl-turbo/resolve/main/sd_xl_turbo_1.0_fp16.safetensors"
```

### 6. Run ComfyUI

```bash
cd /path/to/ComfyUI
source venv/bin/activate
python main.py
```

Access at: http://localhost:8188

## Manual Setup

### 1. Install NVIDIA Container Toolkit

**Ubuntu/Debian:**
```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

**Test GPU access:**
```bash
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### 2. Create Model Directory

```bash
mkdir -p comfyui_models/checkpoints
mkdir -p comfyui_models/vae
mkdir -p comfyui_models/loras
```

### 3. Download SDXL Models

**Option A: SDXL Turbo (Recommended - Fast)**
```bash
# 6.9 GB - Very fast, 6 steps, good quality
cd comfyui_models/checkpoints
wget https://huggingface.co/stabilityai/sdxl-turbo/resolve/main/sd_xl_turbo_1.0_fp16.safetensors
```

**Option B: SDXL Base (High Quality)**
```bash
# 6.6 GB - Slower, 20+ steps, best quality
cd comfyui_models/checkpoints
wget https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors
```

**Option C: Both**
```bash
# Use Turbo for posts, Base for blog images
cd comfyui_models/checkpoints
wget https://huggingface.co/stabilityai/sdxl-turbo/resolve/main/sd_xl_turbo_1.0_fp16.safetensors
wget https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors
```

### 4. Start ComfyUI

**With GPU:**
```bash
docker compose --profile gpu up -d comfyui
```

**CPU Only (Slow):**
Edit `docker-compose.yml` and remove the GPU sections, then:
```bash
docker compose up -d comfyui
```

### 5. Verify Installation

Open http://localhost:8188 in your browser. You should see the ComfyUI interface.

## Configuration in Marketing Assistant

1. Go to **Settings** → **Image Generation**
2. Select **ComfyUI (SDXL)** or **Hybrid (Recommended)**
3. Configure:
   - **ComfyUI Base URL**: `http://comfyui:8188` (inside Docker) or `http://localhost:8188` (outside Docker)
   - **SDXL Model**: `sd_xl_turbo_1.0_fp16.safetensors`
   - **Steps**: `6` (for Turbo) or `20` (for Base)
   - **CFG Scale**: `1.0` (for Turbo) or `7.0` (for Base)
   - **Sampler**: `euler_ancestral` (for Turbo) or `dpmpp_2m` (for Base)

4. For **Hybrid Mode**:
   - ✅ Use OpenAI for LinkedIn Posts (fast, $0.015/image)
   - ✅ Use ComfyUI for Blog Images (best quality, free, local)

## Model Comparison

| Model | Size | Speed | Quality | Steps | Best For |
|-------|------|-------|---------|-------|----------|
| **SDXL Turbo** | 6.9 GB | ⚡ Very Fast | ⭐⭐⭐⭐ Good | 6 | Social media, quick iterations |
| **SDXL Base** | 6.6 GB | 🐌 Slower | ⭐⭐⭐⭐⭐ Excellent | 20-40 | Blog headers, marketing materials |

## Recommended Settings

### For SDXL Turbo (Fast)
```
Model: sd_xl_turbo_1.0_fp16.safetensors
Steps: 6
CFG Scale: 1.0
Sampler: euler_ancestral
Size: 1024x1024
```

### For SDXL Base (Quality)
```
Model: sd_xl_base_1.0.safetensors
Steps: 25
CFG Scale: 7.0
Sampler: dpmpp_2m
Size: 1024x1024
```

## Troubleshooting

### ComfyUI won't start

**Check GPU access:**
```bash
nvidia-smi
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

**Check logs:**
```bash
docker compose logs comfyui
```

**Common issues:**
- NVIDIA drivers not installed
- nvidia-container-toolkit not installed
- Insufficient VRAM (need 6GB+)

### Model not loading

**Check model file:**
```bash
ls -lh comfyui_models/checkpoints/
```

**Verify model in ComfyUI:**
1. Open http://localhost:8188
2. Find the "CheckpointLoaderSimple" node
3. Click dropdown to see available models
4. If model missing, check file location

### Out of memory errors

**Reduce resolution:**
- Use 512x512 or 768x768 instead of 1024x1024

**Close other GPU applications:**
```bash
# Check GPU usage
nvidia-smi
```

**Use FP16 models:**
- Always use `fp16.safetensors` versions (half precision)

### Slow generation

**On GPU:**
- Should take 5-10 seconds for SDXL Turbo
- 30-60 seconds for SDXL Base

**On CPU:**
- Will take 10-30 minutes (not recommended)
- Use OpenAI instead

## Additional Models

### VAE (Optional - Better Colors)
```bash
cd comfyui_models/vae
wget https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors
```

### LoRAs (Optional - Style Control)
```bash
cd comfyui_models/loras
# Download LoRAs from https://civitai.com or https://huggingface.co
```

## CPU-Only Alternative

If you don't have a GPU, consider these alternatives:

1. **Use OpenAI Image Generation**
   - Fast (5-10 seconds)
   - Good quality
   - $0.005-0.040 per image
   - No local setup required

2. **Use Stable Diffusion Online Services**
   - Replicate.com
   - Stability AI API
   - Hugging Face Inference API

3. **Rent GPU Cloud Instance**
   - Vast.ai
   - RunPod
   - Lambda Labs

## Performance Optimization

### For Faster Generation

1. **Use SDXL Turbo**
   - Only 6 steps needed
   - Same quality in 1/4 the time

2. **Reduce Steps**
   - Turbo: 4-6 steps
   - Base: 20-25 steps (not less)

3. **Use Smaller Resolutions**
   - 512x512 or 768x768 for drafts
   - 1024x1024 for final

### For Better Quality

1. **Use SDXL Base**
   - More steps (25-40)
   - Higher CFG scale (7-9)

2. **Use VAE**
   - Better color accuracy
   - Sharper details

3. **Add LoRAs**
   - Style control
   - Concept refinement

## Useful Commands

```bash
# Start ComfyUI
docker compose --profile gpu up -d comfyui

# Stop ComfyUI
docker compose stop comfyui

# View logs
docker compose logs -f comfyui

# Restart ComfyUI
docker compose restart comfyui

# Check GPU usage
nvidia-smi

# List downloaded models
ls -lh comfyui_models/checkpoints/

# Access ComfyUI shell
docker exec -it marketer_comfyui /bin/bash
```

## URLs

- **ComfyUI Web Interface**: http://localhost:8188
- **ComfyUI API**: http://localhost:8188/api
- **Model Storage**: `./comfyui_models/checkpoints/`

## Resources

- [ComfyUI GitHub](https://github.com/comfyanonymous/ComfyUI)
- [SDXL Models on Hugging Face](https://huggingface.co/stabilityai)
- [CivitAI Models](https://civitai.com)
- [ComfyUI Examples](https://comfyui-examples.com)
