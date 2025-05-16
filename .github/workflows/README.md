# Instructions for workflows

## Environment

To test workflows locally, create a file `.secrets.env` in this directory with the following set

```bash
AWS_ACCESS_KEY_ID=...replace this...
AWS_SECRET_ACCESS_KEY=...replace this...
AWS_REGION=...replace this...
S3_BUCKET_NAME=...replace this...
```

The file is not checked into source control and the values required are obviously not `...replace this...`

Be sure to set the real values with in github secrets

## Running github actions locally

### Prerequisites

<dl>
<dt>homebrew</dt>
<dd>the start of so many journeys. installed via <a href="https://docs.brew.sh/Installation">instructions</a></dd>

<dt>docker</dt>
<dd>for running tests, installed via <a href="https://docs.docker.com/get-started/get-docker/">download</a></dd>

<dt>act</dt>
<dd>for running GitHub Action pipeline, v0.2.76 installed via <code>homebrew</code></dd>
</dl>

### Running the pipelines locally

#### pr-checks.yml

```bash
act -P ubuntu-latest=ghcr.io/catthehacker/ubuntu:act-latest \
    -W .github/workflows/pr-checks.yml
```

#### deploy-to-aws.yml

This one needs the secrets since it pushes artifacts to S3 and updates live lambda function.
```bash
act -P ubuntu-latest=ghcr.io/catthehacker/ubuntu:act-latest \
    --secret-file .github/workflows/.secrets.env \
    -W .github/workflows/deploy-to-aws.yml
```
