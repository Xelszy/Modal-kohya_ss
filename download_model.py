#GPT

import modal
from huggingface_hub import hf_hub_download, list_repo_files

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
    files=None,            # bisa string atau list
    auto_ext=None          # filter ekstensi (contoh: ["safetensors", "bin"])
):
    """
    Unduh model Hugging Face ke volume /kohya_ss/models
    - repo_id   : nama repo huggingface, ex: black-forest-labs/FLUX.1-dev
    - files     : nama file (str) atau list file (list[str])
    - auto_ext  : jika None, akan default ke ["safetensors", "bin", "pt"]
    """

    results = []
    try:
        # Kalau user tidak kasih files → auto mode
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

        # Mulai download
        for fname in files:
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


@app.local_entrypoint()
def main():
    # contoh langsung download flux
    repo_id = "black-forest-labs/FLUX.1-dev"
    res = download_model.remote(repo_id, files="flux1-dev.safetensors")
    print(res)
