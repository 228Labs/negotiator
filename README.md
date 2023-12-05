# Negotiator

An app that helps you to practice negotiations with ChatGPT.

## Challenge
- We’re building a simple app to help our users practice negotiating to buy a used car.
- Stack: Python Flask application, integrates with OpenAI’s LLM, and talks to a Postgres database.
- We would like to extend the application to support:
    - A way for users to see the negotiations they have created including:
        - The negotiation ID
        - A count of the messages included in the negotiation
        - The final message sent in the negotiation - representing a rough “outcome” of the negotiation
        - A link to resume the negotiation.
    - Start with the simplest working solution you can, we can refactor at the end.
    - Write tests to help you work through the implementation.
    - Ask questions now and as you go.

## Architecture

Negotiator is a server side rendered app using [Flask](https://flask.palletsprojects.com/).
It uses [Lit](https://lit.dev/) to create [web components](https://developer.mozilla.org/en-US/docs/Web/API/Web_components)
to add dynamic capabilities to each page.
Lit web components are developed and tested in the [web components](./web-components) directory, and build Javascript
and CSS artifacts are copied to the Flask app's [static](./negotiator/static) directory.
This approach allows for the simplicity of server side rendered app with the dynamic features of a single page app.

## Build and run

1.  Install dependencies
    ```shell
    brew install pyenv poetry nodejs postgresql@14
    poetry install
    npm install --prefix web-components
    ```

1.  Set up the database
    ```shell
    psql postgres < databases/drop_and_create_databases.sql
    make migrate migrate-test
    ```

1.  Build the frontend and watch for changes
    ```shell
    npm run build:watch --prefix web-components
    ```

1.  Run the app in a separate terminal
    ```shell
    cp .env.example .env
    vi .env
    source .env
    poetry run python -m negotiator
    ```

### Running tests

```shell
poetry run mypy negotiator tests
poetry run python -m unittest
npm run test --prefix web-components
```

### Running without poetry

1. Install dependencies and run via gunicorn
    ```shell
    poetry export --without-hashes --format=requirements.txt > requirements.txt
    ```

    ```shell 
   pip install -r requirements.txt
    ```

    ```shell  
   gunicorn -w 4 'negotiator.app:create_app()' --bind=0.0.0.0:${PORT}
    ```
   
1. Pack and run via docker
    ```shell
    poetry export --without-hashes --format=requirements.txt > requirements.txt
    ```

    ```shell 
   pack build negotiator --builder=gcr.io/buildpacks/builder:v1
    ```

    ```shell
   docker run -p 8081:8081 --env-file .env.docker negotiator
    ```   
