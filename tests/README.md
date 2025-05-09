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

I'm still not comfortable doing everything with sam.  I know I can, I just didn't have time to learn while working on this, so I did it manually.  I'm pretty command-line phobic for most things.

1. Build for the execution environment
```bash
sam build --use-container --parameter-overrides Architecture=x86_64
```

2. Build .zip package for deployment
```bash
cd .aws-sam/build/LodgifyCalendarLambda 
zip -r ~/deploy.zip .
```

3. Upload `~/deploy.zip` via the console (and do anything else you need there)

#### Deployment architecture

Calendar requests like this for my short-term rental page are light, very light.  So, hosting the API aggregator to produce the calendar data, [app.py](../lambda_function/app.py), as a lambda function makes sense.  It, and the [.js](../calendar_frontend/lodgify-calendar.js) and [.css](../calendar_frontend/lodgiify-styles.css) files sit behand an API gateway.  To further protect them from abuse, I set throttling limits.  The lambda function also implements CORS whitelisting of allowed domains, so you wont be able to just in a reference on your own webpage without getting errors in the browser.   You are more than welcome to clone this project and adapt it for your own needs and deploy your own resources.  