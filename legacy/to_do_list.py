# TO-DO LIST PROJECT

# Store all tasks
tasks = []


# Add a new task
def add_tasks():

    print("===== Add Tasks =====")

    task = input("Enter tasks:")
    tasks.append(task)
    print("Task added successfully!")
    return task


# Display all tasks
def view_tasks():

    print("===== View Tasks =====")

    if not tasks:
        return "No tasks added yet"
    else:
        for number, task in enumerate(tasks, start=1):
            print(number, task)


# Delete a task using its number
def delete_tasks():

    print("===== Delete Tasks =====")

    task = int(input("Enter task number to delete:"))
    tasks.pop(task - 1)
    print("Task deleted successfully!")


# Keep the menu running until the user exits
while True:

    print("===== To-Do List =====")

    print("1. Add Tasks:")
    print("2. View Tasks")
    print("3. Delete Tasks")
    print("4. Exit")

    choice = int(input("Choose an option:"))

    if choice == 1:
        add_tasks()

    elif choice == 2:
        view_tasks()

    elif choice == 3:
        delete_tasks()

    elif choice == 4:
        print("Goodbye!")
        break

    else:
        print("Invalid choice. Please try again.")

