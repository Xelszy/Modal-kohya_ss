import modal
import subprocess
import toml
import logging
import os
from pathlib import Path

# setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
PYTHON_VERSION = "3.10"
KOHYA_REPO_URL = "https://github.com/bmaltais/kohya_ss.git"
base_image = (
    modal.Image.from_registry(
        "nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04", add_python=PYTHON_VERSION
    )
    .env({
        "DEBIAN_FRONTEND": "noninteractive",
        "TZ": "Etc/UTC",
        "PYTORCH_CUDA_ALLOC_CONF": "max_split_size_mb:128",
        "PIP_CACHE_DIR": "/tmp/pip-cache",
        "PIP_NO_CACHE_DIR": "false",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PYTHONUNBUFFERED": "1",
    })
    .run_commands([

##=========DEPEDENCIES=========##
      
        "apt-get update && apt-get install -y --no-install-recommends "
        "git wget curl unzip "
        "libgl1-mesa-glx libglib2.0-0 python3-tk libjpeg-dev libpng-dev "
        "google-perftools build-essential cmake ninja-build && "
        "apt-get clean && rm -rf /var/lib/apt/lists/*",
        
        "mkdir -p /tmp/pip-cache",
        "pip install --upgrade pip setuptools wheel",
    ])
)

##=============================##


kohya_image = (
    base_image
    .env({
        "KOHYA_VERSION_DATE": "2025-01-15",
        "LD_PRELOAD": "/usr/lib/x86_64-linux-gnu/libtcmalloc.so.4",
    })
    .run_commands([

#shallow speedup
      
        f"git clone --depth 1 {KOHYA_REPO_URL} /kohya_ss",
    ], gpu="any")
    .workdir("/kohya_ss")
    .run_commands([

      ##==============wheels go brr=============##
      
        "pip download --timeout 600 "
        "torch==2.1.2+cu118 torchvision==0.16.2+cu118 torchaudio==2.1.2+cu118 "
        "--extra-index-url https://download.pytorch.org/whl/cu118 -d /tmp/pip-cache",
        
        "pip download --timeout 600 "
        "xformers==0.0.23.post1+cu118 --index-url https://download.pytorch.org/whl/cu118 -d /tmp/pip-cache",
        
        "pip download --timeout 600 "
        "bitsandbytes==0.41.1 diffusers accelerate -d /tmp/pip-cache"
    ], gpu="any")
    .run_commands([

      #conflict solution
        
        # clone sd-scripts
        
        "if [ ! -d /kohya_ss/sd-scripts ]; then git clone https://github.com/kohya-ss/sd-scripts.git /kohya_ss/sd-scripts; fi",

        "[ -f requirements.txt ] && sed -i -e '/torch/d' -e '/torchvision/d' -e '/torchaudio/d' -e '/xformers/d' -e '/bitsandbytes/d' -e '/sd-scripts/d' requirements.txt",
        "pip install --use-pep517 --timeout 600 --find-links /tmp/pip-cache -r requirements.txt",
        "pip uninstall -y torch torchvision torchaudio triton xformers bitsandbytes || true",

      #+++++++++++++method speedup process+++++++#
        "pip install --timeout 600 --find-links /tmp/pip-cache "
        "torch==2.1.2+cu118 torchvision==0.16.2+cu118 torchaudio==2.1.2+cu118 || "
        "pip install --timeout 600 "
        "torch==2.1.2+cu118 torchvision==0.16.2+cu118 torchaudio==2.1.2+cu118 "
        "--extra-index-url https://download.pytorch.org/whl/cu118",
        "pip install --timeout 600 --find-links /tmp/pip-cache "
        "xformers==0.0.23.post1+cu118 || "
        "pip install --timeout 600 "
        "xformers==0.0.23.post1+cu118 --index-url https://download.pytorch.org/whl/cu118",
        "pip install --timeout 600 --find-links /tmp/pip-cache "
        "bitsandbytes==0.41.1 diffusers accelerate",
        
        "accelerate config default",
        
        "python -c 'import torch; print(f\"torch: {torch.__version__}\")'",
        "python -c 'import xformers; print(f\"xformers: {xformers.__version__}\")'",
        
        # cleanup
        "rm -rf /tmp/pip-cache models dataset outputs configs",
        "mkdir -p models dataset outputs configs",
    ], gpu="any")
)




CONFIG_FILE = Path(__file__).parent / "config.toml"

try:
    if CONFIG_FILE.exists():
        config = toml.load(CONFIG_FILE)
    else:
        config = {}
        
    modal_settings = config.get('modal_settings', {})
    kohya_settings = config.get('kohya_settings', {})
    ALLOW_CONCURRENT_INPUTS = modal_settings.get('allow_concurrent_inputs', 10)
    scaledown_window = modal_settings.get('scaledown_window', 600)
    TIMEOUT = modal_settings.get('timeout', 3600)
    GPU_CONFIG = modal_settings.get('gpu', "A10G")
    PORT = kohya_settings.get('port', 8000)
    
except Exception as e:
    ALLOW_CONCURRENT_INPUTS = 5
    scaledown_window = 300 #depreciations fix
    TIMEOUT = 1800
    GPU_CONFIG = "A10G"
    PORT = 8000

app = modal.App(name="kohya-ss-gui", image=kohya_image)

##============PATH=============##

CACHE_PATH = "/cache"
KOHYA_BASE = "/kohya_ss"  
MODELS_PATH = "/kohya_ss/models"
DATASET_PATH = "/kohya_ss/dataset"
OUTPUTS_PATH = "/kohya_ss/outputs"
CONFIGS_PATH = "/kohya_ss/configs"
##################VOLUME####################
cache_vol = modal.Volume.from_name("hf-cache", create_if_missing=True)
models_vol = modal.Volume.from_name("kohya-models", create_if_missing=True)
dataset_vol = modal.Volume.from_name("kohya-dataset", create_if_missing=True)
outputs_vol = modal.Volume.from_name("kohya-outputs", create_if_missing=True)
configs_vol = modal.Volume.from_name("kohya-configs", create_if_missing=True)

@app.function(
    gpu=GPU_CONFIG,
    timeout=TIMEOUT,
    scaledown_window=scaledown_window,
    volumes={
        CACHE_PATH: cache_vol,
        MODELS_PATH: models_vol,
        DATASET_PATH: dataset_vol,
        OUTPUTS_PATH: outputs_vol,
        CONFIGS_PATH: configs_vol,
    },
    memory=8192,
    cpu=4,
    max_containers=1,
)
@modal.web_server(PORT, startup_timeout=300)
@modal.concurrent(max_inputs=ALLOW_CONCURRENT_INPUTS)
def run_kohya_gui():
    import torch, os, subprocess

    print(f"pytorch version: {torch.__version__}")
    print(f"cuda available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"gpu name: {torch.cuda.get_device_name(0)}")

    os.environ["HF_HOME"] = CACHE_PATH
    os.environ["TRANSFORMERS_CACHE"] = CACHE_PATH

    for path in [MODELS_PATH, DATASET_PATH, OUTPUTS_PATH, CONFIGS_PATH]:
        os.makedirs(path, exist_ok=True)

    cmd = (
        f"cd {KOHYA_BASE} && "
        f"accelerate launch --num_cpu_threads_per_process=4 kohya_gui.py "
        f"--listen 0.0.0.0 --server_port {PORT} --share --headless --noverify"
    )
    print(f"starting kohya with: {cmd}")

    try:
        process = subprocess.Popen(cmd, shell=True)
        process.wait()
    except Exception as e:
        print(f"error starting kohya: {e}")
        raise

#dataset downlaod

@app.function(volumes={DATASET_PATH: dataset_vol})
def download_hf_dataset(repo_id: str, allow_patterns: str = "*", repo_type: str = "dataset"):
    from huggingface_hub import snapshot_download

    local_dir = snapshot_download(
        repo_id=repo_id,
        repo_type=repo_type,
        local_dir=DATASET_PATH,
        local_dir_use_symlinks=False,
        allow_patterns=allow_patterns
    )
    return {"status": "ok", "path": local_dir}


#FLux download

@app.function(secrets=[modal.Secret.from_name("huggingface-token")], volumes={MODELS_PATH: models_vol})
def download_flux_model(repo_id: str = "black-forest-labs/FLUX.1-dev", subfolder: str = None):
    from huggingface_hub import snapshot_download

    local_dir = snapshot_download(
        repo_id=repo_id,
        repo_type="model",
        local_dir=MODELS_PATH,
        local_dir_use_symlinks=False,
        allow_patterns="*"
    )
    return {"status": "ok", "path": local_dir}

  ########## START KOHYA ###########
@app.function(
    gpu=GPU_CONFIG,
    timeout=600,
    volumes={
        MODELS_PATH: models_vol,
        OUTPUTS_PATH: outputs_vol,
    }
)
def upload_model(model_data: bytes, model_name: str):
    import os
    
    model_path = os.path.join(MODELS_PATH, model_name)
    
    try:
        with open(model_path, 'wb') as f:
            f.write(model_data)
        return {"status": "success", "path": model_path}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# cleanup function
@app.function(
    volumes={
        OUTPUTS_PATH: outputs_vol,
    }
)
def cleanup_old_files(days_old: int = 7):
    import os
    import time
    
    current_time = time.time()
    cutoff = current_time - (days_old * 24 * 60 * 60)
    cleaned_count = 0
    
    if os.path.exists(OUTPUTS_PATH):
        for root, dirs, files in os.walk(OUTPUTS_PATH):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    if os.path.getmtime(file_path) < cutoff:
                        os.remove(file_path)
                        cleaned_count += 1
                except:
                    # ignore errors
                    pass
    
    return {"files_cleaned": cleaned_count}

@app.function()  
def health_check():
    import torch
    import time
    
    return {
        "status": "healthy",
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "timestamp": time.time()
    }

@app.local_entrypoint()
def main():
    print("kohya_ss modal deployment")
    print(f"gpu config: {GPU_CONFIG}")
    print(f"port: {PORT}")
    print("")
    print("available commands:")
    print("  modal serve app.py     # development server")
    print("  modal deploy app.py    # production deployment")
    print("")
    print("edit config.toml to change settings")
