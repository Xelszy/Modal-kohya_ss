#GPT

import modal
from huggingface_hub import hf_hub_download, list_repo_files
from tqdm import tqdm

DATASET_PATH = "/kohya_ss/dataset"
dataset_vol = modal.Volume.from_name("kohya-dataset", create_if_missing=True)

app = modal.App(name="download-hf-dataset")

@app.function(
    timeout=7200,  # dataset biasanya gede
    secrets=[modal.Secret.from_name("huggingface-token")],
    volumes={DATASET_PATH: dataset_vol},
    memory=8192,
    cpu=4,
)
def download_dataset(
    repo_id: str,
    files=None,            # bisa string atau list
    auto_ext=None          # filter ekstensi, contoh: ["jpg","png","zip"]
):
    """
    Unduh dataset Hugging Face ke volume /kohya_ss/dataset
    - repo_id   : nama repo huggingface, ex: laion/laion400m
    - files     : nama file (str) atau list file (list[str])
    - auto_ext  : filter berdasarkan ekstensi
    """

    results = []
    try:
        if files is None:
            repo_files = list_repo_files(repo_id, repo_type="dataset")
            if auto_ext is None:
                auto_ext = ["jpg", "png", "zip"]
            files = [f for f in repo_files if f.split(".")[-1].lower() in auto_ext]

        elif isinstance(files, str):
            files = [files]

        elif isinstance(files, list):
            pass
        else:
            return {"error": "files harus string atau list"}

        for fname in tqdm(files, desc=f"Downloading {repo_id}", unit="file"):
            try:
                local_path = hf_hub_download(
                    repo_id=repo_id,
                    repo_type="dataset",
                    filename=fname,
                    local_dir=DATASET_PATH,
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
    # contoh langsung download dataset demo
    repo_id = "datasets/laion/laion400m-meta"
    res = download_dataset.remote(repo_id, auto_ext=["parquet"])
    print(res)
