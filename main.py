import tkinter as tk
from ui import TaskPlannerApp

def main():
    root = tk.Tk()
    app = TaskPlannerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
