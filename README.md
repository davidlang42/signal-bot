# signal-bot
A signal bot which actions tasks based on emoji'd messages.

This contains 2 parts:
- A Google Apps Script service which performs google-based actions (send email, create task)
- A Docker container which monitors incoming Signal messages and triggers those actions

## Set up local repo
* Clone git repo: `git clone https://github.com/davidlang42/signal-bot.git`
* Install [clasp](https://developers.google.com/apps-script/guides/clasp): `npm install @google/clasp -g`
* Login to clasp: `clasp login`
* Enter app directory: `cd app`
* Connect apps script project: `clasp clone [scriptId]`

## Deploying Google Apps Script changes
### Use bash script
* Run from the root of the repo: `./deploy.sh`
  * Warning: This will overwrite any changes made directly on google apps scripts, but they will still exist in a reverted commit labelled 'possible lost changes'
### Execute manually
* Enter app directory: `cd app`
* Pull changes to local git repo: `git pull`
* Push changes to apps scripts: `clasp push`
  * Warning: This will overwrite any changes made directly on google apps scripts
* Find existing deployment: `clasp deployments`
  * Returns deployment id: `- AKfycbxSDJouDbOKVTQ3cnnGaJaLW5EbR86YRTwCX-PJb7Mvua9egDM @58 - Test via Clasp`
* Create version & update existing deployment: `clasp deploy -i [deploymentId] -d "[description]"`

## Deploying Docker container changes
This happens automatically on release in GitHub Actions.

Available as `davidlang42/signal-bot:latest` on [Docker Hub](https://hub.docker.com/r/davidlang42/signal-bot)