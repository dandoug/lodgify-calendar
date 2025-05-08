## Test setup

### secrets_lambda_stub.py

Create a `.secrets.json` file (this is never checked in), that contains `"key": "value"` pairs of secrets you wish to simulate.  The `key` is the ARN of the secret and the value is the value you wish to return.

Run with
```bash
fastapi dev secrets_lambda_stub.py --port 2773
```

### Launching function with sam

Create an enviornment variables file named `.env-vars.json` that has 
```json
{
    "Parameters": {
        "SECRET_SERVICE_BASE_URL": "http://host.docker.internal:2773",
        "SECRET_NAME": "...your secret arn here..."
    }
}
```

and reference it when launching lambda (note that any variables must be defined in the [template.yaml](../template.yaml) file)
```bash
sam local start-api --env-vars tests/.env-vars.json
```