# What's the data structure for a single todo? Stack
# How am I parsing the command line argument (add/list/done/remove)?
# Where does the JSON file live?
# What happens if the file doesn't exist yet?


import sys
import json

TODO_FILE = "todos.json"

def load_todos():
    try:
        with open(TODO_FILE,'r') as F:
            data = json.load(F)
            return(list(data))
    except FileNotFoundError:
        #print(f"Error: The file '{TODO_FILE}' was not found.")
        return []
    pass

def save_todos(todos):
    try:
        with open(TODO_FILE,"w") as F:
            json.dump(todos,F,indent = 4)
    except TypeError as e:
        print("Error: The data contains objects that cannot be serialized to JSON.")
        print(f"Details: {e}")

    except PermissionError:
        print(f"Error: You do not have permission to write to '{TODO_FILE}'.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    pass

def add_todos(task):
    todos = load_todos()
    new_todo = {"task": task, "done": False}
    todos.append(new_todo)
    save_todos(todos)
    print(f"The file '{TODO_FILE}' was saved.")

    pass

def list_todos():
    todos = load_todos()

    if(not todos):
        print("No Todos yet")
    else:
        for i in range (len(todos)) :
            status = "[x]" if todos[i]["done"] else "[ ]"
            print(f"  {i + 1}. {status} {todos[i]['task']}")

    pass
def remove_todos(task):
    todos = load_todos()
    TaskToRemove = int(task)
    todos.pop((TaskToRemove -1))
    save_todos(todos)

    print("Task Removed")
    pass
def done_todos(task):
    todos = load_todos()
    TaskToRemove = int(task);
    for i in range(len(todos)):
        if(i == (TaskToRemove - 1)):
            todos[i]["done"] = True
            break
    save_todos(todos)
    pass
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python todo.py <command> [arguments]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "add":
        # What goes here? How do you get the task text from sys.argv?
        add_todos(sys.argv[2])
        pass
    elif command == "list":
        list_todos()
    elif command == "remove":
        remove_todos(sys.argv[2])
    elif command == "done":
        done_todos(sys.argv[2])
    else:
        print(f"Unknown command: {command}")