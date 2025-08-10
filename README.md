### RefAIree stream

# 1. Install dependencies on Raspberry Pi

Update system and install needed packages:
```
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

Create a Python virtual environment (optional but cleaner):
```
python3 -m venv ~/stream-api
source ~/stream-api/bin/activate
```

Install FastAPI and Uvicorn (server):
```
pip install fastapi uvicorn
```

# 2. Run the API

```
uvicorn stream_api:app --host 0.0.0.0 --port 8000
```
