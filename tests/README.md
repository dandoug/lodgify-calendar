## Test And Deployment

### Secrets server

The lambda function using the AWS secrets layer in production.  To simulate this in test, there is a simple HTTP server implemented in python that you should start and leave running.

Create a `.secrets.json` file (this is never checked in) in the [tests](.), that contains `"key": "value"` pairs of secrets you wish to simulate.  The `key` is the ARN of the secret and the value is the value you wish to return.  The file should be placed in the 

In the [tests](.) (wehre this README.md is located) run the secrets server with
```bash
fastapi dev secrets_lambda_stub.py --port 2773
```

### Launching function with sam

Create an environment variables file named `.env-vars.json` that has 
```json
{
    "Parameters": {
        "SECRET_SERVICE_BASE_URL": "http://host.docker.internal:2773",
        "SECRET_NAME": "...your secret arn here..."
    }
}
```

and reference it when launching lambda (note that any variables must be defined in the [template.yaml](../template.yaml) file)

#### Build for test

From the project [root directory](..) where the [template.yaml](../template.yaml) is located, run this build command, assuming you are on a `arm64` machine.
```bash
sam build --use-container --parameter-overrides Architecture=arm64

```

#### Execute for test

Ensure the secrets server is running as described [above](#secrets-server) and then
```bash
sam local start-api --parameter-overrides Architecture=arm64 --env-vars tests/.env-vars.json

```

### Deployment

...tbd