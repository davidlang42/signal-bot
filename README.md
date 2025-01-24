# signal-bot
A signal bot which actions tasks based on emoji'd messages.

This contains 2 parts:
- A Google Apps Script service which performs google-based actions (send email, create task)
- A Docker container which monitors incoming Signal messages and triggers those actions

## Usage

There are 2 steps to running SignalBot. As SignalBot is a single user application, 1 instance of each of these is required per user.

### Create Google Apps Script

- Sign in to the Google Account in which you would like newly created Tasks to appear
- Create a new [Apps Script project](https://script.google.com/home/projects/create)
- Set the name by clicking "Untitled project" in the top left
  - This can be anything you want, but I recommend "SignalBot"
- Add each js file in the app dir by clicking the + (next to Files) > Script and copy/pasting the code, then clicking Ctrl+S to save
- Click Deploy > New Deployment, Gear icon (next to Select type) > Web App
- Set "Who has access" to "Anyone", and click Deploy
- Copy the URL below Web App (eg. https://script.google.com/macros/s/.../exec) to use the docker configuration below
  - NOTE: This URL is a SECRET! If you let anyone see this, they will be able to spam you with new tasks/ send you emails at any time. If you inadvertedly leak this secret, delete the Apps Script file from your google drive, AND delete it forever from your [Google Drive bin](https://drive.google.com/drive/trash), and re-create the Google Apps Script from scratch.

### Run docker container

- Run an instance of the docker image (available as `davidlang42/signal-bot:latest` on [Docker Hub](https://hub.docker.com/repository/docker/davidlang42/signal-bot/general)) on whatever server or computer you would like
- Configure environment variable `GOOGLE_APPS_SCRIPT_URL` to be the Web App URL (secret) you created above
- Configure a persistent volume at mount point `/signal_bot_messages` to store the incoming messages received by Signal
- Configure a persistent volume at mount point `/signal_bot_config` to store the account credentials once Signal is linked

## Development

### Set up local repo
* Clone git repo: `git clone https://github.com/davidlang42/signal-bot.git`
* Install [clasp](https://developers.google.com/apps-script/guides/clasp): `npm install @google/clasp -g`
* Login to clasp: `clasp login`
* Enter app directory: `cd app`
* Connect apps script project: `clasp clone [scriptId]`

### Deploying Google Apps Script changes
#### Use bash script
* Run from the root of the repo: `./deploy.sh`
  * Warning: This will overwrite any changes made directly on google apps scripts, but they will still exist in a reverted commit labelled 'possible lost changes'
#### Execute manually
* Enter app directory: `cd app`
* Pull changes to local git repo: `git pull`
* Push changes to apps scripts: `clasp push`
  * Warning: This will overwrite any changes made directly on google apps scripts
* Find existing deployment: `clasp deployments`
  * Returns deployment id: `- AKfycbxSDJouDbOKVTQ3cnnGaJaLW5EbR86YRTwCX-PJb7Mvua9egDM @58 - Test via Clasp`
* Create version & update existing deployment: `clasp deploy -i [deploymentId] -d "[description]"`

### Deploying Docker container changes
This happens automatically on release in GitHub Actions.
