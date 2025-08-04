#GPT

import modal
from huggingface_hub import hf_hub_download, list_repo_files, snapshot_download
from tqdm import tqdm

MODELS_PATH = "/kohya_ss/models"
models_vol = modal.Volume.from_name("kohya-models", create_if_missing=True)

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
    files=None,            # string / list / None
    auto_ext=None          # filter ekstensi kalau files=None
):
    """
    Robust downloader for Hugging Face models.
    - repo_id   : nama repo huggingface, ex: black-forest-labs/FLUX.1-dev
    - files     : nama file (str), list[str], atau None → kalau None maka snapshot_download
    - auto_ext  : filter ekstensi, default ["safetensors", "bin", "pt"]
    """

    try:
        # Case 1: user tidak kasih files → download repo dengan snapshot
        if files is None:
            if auto_ext is None:
                auto_ext = ["safetensors", "bin", "pt"]

            allow_patterns = [f"*.{ext}" for ext in auto_ext]
            local_dir = snapshot_download(
                repo_id=repo_id,
                repo_type="model",
                local_dir=MODELS_PATH,
                local_dir_use_symlinks=False,
                allow_patterns=allow_patterns
            )
            return {"status": "done", "mode": "snapshot", "path": local_dir}

        # Case 2: user kasih 1 file (string)
        if isinstance(files, str):
            files = [files]

        # Case 3: user kasih banyak file
        results = []
        for fname in tqdm(files, desc=f"Downloading from {repo_id}"):
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
        return {"status": "done", "mode": "per-file", "results": results}

    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.local_entrypoint()
def main():
    # Contoh 1 → download 1 file spesifik
    repo_id = "black-forest-labs/FLUX.1-dev"
    res = download_model.remote(repo_id, files="flux1-dev.safetensors")
    print("Download spesifik:", res)

    # Contoh 2 → download semua safetensors & bin pakai snapshot
    repo_id = "stabilityai/stable-diffusion-xl-base-1.0"
    res = download_model.remote(repo_id, files=None, auto_ext=["safetensors", "bin"])
    print("Download snapshot:", res)
