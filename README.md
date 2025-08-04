# kohya modal deployment

fast deployment of kohya_ss to modal with optimizations

## quick start

1. `pip install modal`
2. `modal token new`
3. edit config.toml if needed
4. `python deploy.py dev`

## files

- app.py - main modal application
- config.toml - configuration
- deploy.py - deployment helper script

## usage

```bash
# development server
python deploy.py dev

# production deployment
python deploy.py prod

# build image only
python deploy.py build

# check service health
python deploy.py health

# cleanup old files (default 7 days)
python deploy.py cleanup
python deploy.py cleanup 14

# view logs
python deploy.py logs

# list volumes
python deploy.py volumes

# check requirements
python deploy.py check
```

## optimizations applied

- shallow git clone (faster repo download)
- parallel pip installs 
- wheel pre-downloading and caching
- tcmalloc memory allocator
- pre-download pytorch wheels
- clean requirements.txt (remove conflicts)

build time: ~5-8 minutes vs ~15-20 minutes before

## configuration

edit config.toml for:
- gpu type (A10G, A100, H100, T4)
- port settings
- timeout values
- concurrent request limits

## storage

modal volumes used:
- kohya-models - model files
- kohya-dataset - training datasets
- kohya-outputs - training results
- kohya-configs - configuration files  
- hf-cache - huggingface model cache

## troubleshooting

if something breaks:
1. `python deploy.py check` - verify setup
2. `python deploy.py logs` - check error logs
3. `python deploy.py build` - rebuild image

gpu memory issues? change gpu to A100 in config.toml or reduce concurrent_inputs
