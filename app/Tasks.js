function doTask(e) {
  const title = e.parameter.title;
  if (!title) return doError(e, "No title set for task.");
  const notes = e.parameter.notes;
  let due = e.parameter.due;
  const taskListName = e.parameter.list;
  // find task list
  var taskListId;
  if (taskListName) {
    taskListId = getTaskList(taskListName);
  } else {
    taskListId = getFirstTaskList();
  }
  if (!taskListId) return doError(e, "Task list not found: " + taskListName);
  // add task
  var task = Tasks.newTask();
  task.title = title;
  if (notes) task.notes = notes;
  if (due) {
    if (!isNaN(due)) due = parseInt(due); // timestamp
    task.due = formatDate(new Date(due));
  }
  Tasks.Tasks.insert(task, taskListId);
  return doSuccess("Task actioned.");
}

function getTaskList(listName) {
  for (const taskList of Tasks.Tasklists.list({ maxResult: 100 }).items) {
    if (taskList.title == listName) {
      return taskList.id;
    }
  }
  return null;
}

function getFirstTaskList() {
  var items  = Tasks.Tasklists.list({ maxResult: 1 }).items;
  if (items.length) {
    return items[0].id;
  } else {
    return null;
  }
}

function formatDate(d) {
  return Utilities.formatDate(d, Session.getScriptTimeZone(), "yyyy-MM-dd'T'00:00:00.000'Z'"); 
}