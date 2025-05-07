"""
Stub to simulate AWS Parameters and Secrets Lambda extension in test environments.
"""
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException

THIS_DIR = Path(__file__).parent
SECRET_FILE = THIS_DIR / ".secrets.json"

# read and save the secrets
with open(SECRET_FILE, encoding='utf-8') as f:
    SECRETS = json.load(f)

app = FastAPI()


@app.get("/secretsmanager/get")
async def get_secret(secretId: str):  # pylint: disable=invalid-name
    """x
    Handles fetching a secret's details by its unique identifier. This route checks
    if the secret exists, if found, returns its associated
    details. If the secret cannot be found, it returns a 404 error.

    Parameters:
    secretId (str): The unique identifier (ARN) of the secret to retrieve.

    Returns:
    dict: Contains the secret's ARN (Amazon Resource Name), name, and its string
    representation, if found. Returns an error otherwise.

    """
    if secretId in SECRETS:
        return {"ARN": secretId, "Name": secretId, "SecretString": SECRETS[secretId]}

    raise HTTPException(status_code=404, detail=f"Item {secretId} not found")
