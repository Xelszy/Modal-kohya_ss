#GPT

import modal
from huggingface_hub import hf_hub_download, list_repo_files
from tqdm import tqdm
import os

# path dan volume
MODELS_PATH = "/kohya_ss/models"
models_vol = modal.Volume.from_name("kohya-models", create_if_missing=True)

# definisi app
app = modal.App(name="download-hf-model")

@app.function(
    timeout=3600,
    secrets=[modal.Secret.from_name("huggingface-token")],
    volumes={MODELS_PATH: models_vol},
    memory=4096,
    cpu=2,
)
def download_model(
    repo_id: str,
    files=None,             # string atau list file
    auto_ext=None           # filter ekstensi
):
    """
    Unduh model Hugging Face ke volume /kohya_ss/models
    Args:
      repo_id (str): nama repo Hugging Face, contoh: stabilityai/stable-diffusion-xl-base-1.0
      files (str|list): nama file (bisa 1 string atau list of string)
      auto_ext (list): filter ekstensi otomatis, contoh ["safetensors","bin"]
    """
    results = []
    try:
        # ambil daftar file dari repo kalau files None
        if files is None:
            repo_files = list_repo_files(repo_id, repo_type="model")
            if auto_ext is None:
                auto_ext = ["safetensors", "bin", "pt"]
            files = [f for f in repo_files if f.split(".")[-1] in auto_ext]

        elif isinstance(files, str):
            files = [files]

        elif isinstance(files, list):
            pass
        else:
            return {"error": "files harus string atau list"}

        if not files:
            return {"status": "error", "message": "Tidak ada file cocok di repo"}

        print(f"Mulai download dari repo: {repo_id}")
        print(f"Total file: {len(files)}")

        for fname in tqdm(files, desc="Downloading", unit="file"):
            try:
                local_path = hf_hub_download(
                    repo_id=repo_id,
                    repo_type="model",
                    filename=fname,
                    local_dir=MODELS_PATH,
                    local_dir_use_symlinks=False
                )
                results.append({"file": fname, "status": "ok", "path": local_path})
            except Exception as e:
                results.append({"file": fname, "status": "error", "message": str(e)})

        return {"status": "done", "results": results}

    except Exception as e:
        return {"status": "error", "message": str(e)}


# contoh local entry
@app.local_entrypoint()
def main():
    repo_id = "black-forest-labs/FLUX.1-dev"
    res = download_model.remote(repo_id, files="flux1-dev.safetensors")
    print(res)
