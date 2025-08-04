#GPT
import modal
from huggingface_hub import hf_hub_download, list_repo_files, snapshot_download
from tqdm import tqdm

DATASET_PATH = "/kohya_ss/dataset"
dataset_vol = modal.Volume.from_name("kohya-dataset", create_if_missing=True)

app = modal.App(name="download-hf-dataset")

@app.function(
    timeout=7200,
    secrets=[modal.Secret.from_name("huggingface-token")],
    volumes={DATASET_PATH: dataset_vol},
    memory=4096,
    cpu=2,
)
def download_dataset(
    repo_id: str,
    files=None,            # bisa string / list / None
    auto_ext=None          # filter ekstensi, contoh: ["jpg","png","json"]
):
    """
    Unduh dataset Hugging Face ke volume /kohya_ss/dataset
    - repo_id   : nama repo huggingface, ex: myuser/mydataset
    - files     : nama file (str) / list file / None untuk full snapshot
    - auto_ext  : filter ekstensi (list), ex: ["jpg","png"]
    """

    results = []
    try:
        # === CASE 1: download full repo (snapshot) ===
        if files is None and auto_ext is None:
            local_dir = snapshot_download(
                repo_id=repo_id,
                repo_type="dataset",
                local_dir=DATASET_PATH,
                local_dir_use_symlinks=False
            )
            return {"status": "done", "mode": "snapshot", "path": local_dir}

        # === CASE 2: filter by auto_ext or specific files ===
        if files is None:
            repo_files = list_repo_files(repo_id, repo_type="dataset")
            if auto_ext is None:
                auto_ext = ["jpg", "png", "json"]
            files = [f for f in repo_files if f.split(".")[-1] in auto_ext]

        elif isinstance(files, str):
            files = [files]

        # === download per file with progress ===
        for fname in tqdm(files, desc=f"Downloading {repo_id}"):
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

        return {"status": "done", "mode": "file-download", "results": results}

    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.local_entrypoint()
def main():
    # contoh langsung download dataset full snapshot
    repo_id = "datasets/your-dataset-id"
    res = download_dataset.remote(repo_id)
    print(res)
