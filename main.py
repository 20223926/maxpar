from maxpar import TaskSystem, Task

X = None
Y = None
Z = None

def run1():
    global X
    X = 1

def run2():
    global Y
    Y = 1

def run3():
    global X, Y, Z
    Z = X + Y

def run4():
    global X, Y, Z
    X = 2
    Y = 2
    Z = X + Y

t1 = Task(name="task 1", reads=[], writes=["X"], run=run1)
t2 = Task(name="task 2", reads=[], writes=["Y"], run=run2)
t3 = Task(name="task 3", reads=["X", "Y"], writes=["Z"], run=run3)
t4 = Task(name="task 4", reads=["X", "Y"], writes=["X", "Y", "Z"], run=run4)

ts = TaskSystem(tasks=[t1, t2, t3, t4], pred={"task 1": [], "task 2": [], "task 3": ["task 1", "task 2"], "task 4": ["task 3"]})
print(ts.get_dependencies("task 4"))
ts.par_cost()
ts.draw()
ts.det_test_rnd(globals())