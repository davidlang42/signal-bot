const EMAIL_ADDRESS = Session.getEffectiveUser().getEmail();

function doGet(e) {
  const action = e.parameter.action;
  if(action == "email") {
    return doEmail(e);
  } else if (action == "task") {
    return doTask(e);
  } else {
    return doError(e, "Invalid action: " + action);
  }
}

function doError(e, reason) {
  GmailApp.sendEmail(EMAIL_ADDRESS, "Error: SignalBot", reason + "\n\n" + JSON.stringify(e))
  return ContentService.createTextOutput(reason);
}

function doSuccess(done) {
  return ContentService.createTextOutput(done);
}