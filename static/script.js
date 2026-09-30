const API_URL = "/api/tasks";

const taskInput = document.getElementById("task-input");
const addBtn = document.getElementById("add-btn");
const taskList = document.getElementById("task-list");
const emptyMsg = document.getElementById("empty");
const errorMsg = document.getElementById("error");
const summary = document.getElementById("summary");
const progress = document.getElementById("progress");
const progressFill = document.getElementById("progress-fill");

document.getElementById("today").textContent = new Date().toLocaleDateString(
  "en-US",
  { weekday: "long", month: "long", day: "numeric" }
);

function showError(message) {
  errorMsg.textContent = message;
  errorMsg.hidden = false;
}

function clearError() {
  errorMsg.hidden = true;
}

// View tasks
async function loadTasks() {
  try {
    const res = await fetch(API_URL);
    if (!res.ok) throw new Error();
    renderTasks(await res.json());
    clearError();
  } catch {
    showError("Could not load tasks. Check that the server is running.");
  }
}

function renderTasks(tasks) {
  taskList.innerHTML = "";

  tasks.forEach((task) => {
    const li = document.createElement("li");
    li.className = "task" + (task.completed ? " done" : "");

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = task.completed;
    checkbox.setAttribute("aria-label", "Mark \"" + task.title + "\" as done");
    checkbox.addEventListener("change", () => toggleTask(task.id));

    const title = document.createElement("span");
    title.className = "task-title";
    title.textContent = task.title;

    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "delete-btn";
    deleteBtn.textContent = "Delete";
    deleteBtn.setAttribute("aria-label", "Delete \"" + task.title + "\"");
    deleteBtn.addEventListener("click", () => deleteTask(task.id));

    li.append(checkbox, title, deleteBtn);
    taskList.appendChild(li);
  });

  const doneCount = tasks.filter((t) => t.completed).length;
  emptyMsg.hidden = tasks.length > 0;
  summary.textContent = tasks.length
    ? doneCount + " of " + tasks.length + " done"
    : "";

  const percent = tasks.length ? Math.round((doneCount / tasks.length) * 100) : 0;
  progressFill.style.width = percent + "%";
  progress.setAttribute("aria-valuenow", percent);
}

// Add task
async function addTask() {
  const title = taskInput.value.trim();
  if (!title) {
    showError("Enter a task before adding it.");
    return;
  }

  addBtn.disabled = true;
  try {
    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Could not add the task.");

    taskInput.value = "";
    clearError();
    await loadTasks();
  } catch (err) {
    showError(err.message);
  } finally {
    addBtn.disabled = false;
    taskInput.focus();
  }
}

// Mark done / not done
async function toggleTask(id) {
  try {
    const res = await fetch(API_URL + "/" + id, { method: "PATCH" });
    if (!res.ok) throw new Error();
    await loadTasks();
  } catch {
    showError("Could not update the task.");
  }
}

// Delete task
async function deleteTask(id) {
  try {
    const res = await fetch(API_URL + "/" + id, { method: "DELETE" });
    if (!res.ok) throw new Error();
    await loadTasks();
  } catch {
    showError("Could not delete the task.");
  }
}

addBtn.addEventListener("click", addTask);
taskInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") addTask();
});

loadTasks();