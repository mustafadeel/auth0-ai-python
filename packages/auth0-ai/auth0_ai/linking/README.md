# Account linking Action

You need to install this Action in your Auth0 tenant within the post-login trigger to enable linking.

## Pre-requisites

Create an API within Auth0 Dashboard

- Navigate to Auth0 Dashboard > Applications > APIs and select Create API
- Give the API a name (eg. account-linking) and set the identifier to "my-account"

Create an Application within Auth0 Dashboard

- Navigate to Auth0 Dashboard > Applications > Applications and select Create Application and select Machine to Machine application
  - You might aleady see an application automatically created matching the API (eg. <api-name> (Test Application)). You can rename as needed and use this application as well
- Select Auth0 Management API as an authorized API and further select at least `read:users` and `update:users` scopes
  - Reocrd the `Domain`, `Client ID` and `Client Secret` for this Application.

## Installation

### Create Action

- Navigate to Auth0 Dashboard > Actions > Triggers and select post-login.
- From the Add Action section on the right side of the page, click on (+) sign and select build from scratch.
- Give the Action a name (eg. Account-Linking), select Node 22 as runtime and click on Create.
- Now replace the content within the newly created Aciton with the content from the actions.js file.

### Setup Action secrets

- Select Secrets section of the Action.
- Select "Add Secret" and individually add the following with the respective values from the machine to machine application created in pre-requisites.
  - `domain`
  - `clientId`
  - `clientSecret`

### Setup Action dependencies

- Select the depdendencies section of the Action.
- Select "Add Dependency" and individually add the following as dependencies:
  - auth0
  - auth0-js
  - crypto
  - axios
  - jsonwebtoken
  - jwks-rsa

### Save & Deploy

Select `Save Draft` and then select `Deploy` to enable the Action.
