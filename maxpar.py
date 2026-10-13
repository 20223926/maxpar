from typing import Dict, List, Callable, Any
from threading import Thread
from timeit import timeit
from datetime import datetime
import graphviz
import random
import dis

class Task():
    __name: str
    __reads: List[str]
    __writes: List[str]
    __run: Callable[[Any], Any]

    def __init__(self, name: str, reads: List[str], writes: List[str], run: Callable[[Any], Any]):
        try:
            # Analyze the bytecode of the provided function to check that the 'reads' and 'writes' 
            # parameters match the actual global variables accessed by the function
            r = set()
            w = set()
            for instruction in dis.get_instructions(run):
                if instruction.opname == 'STORE_GLOBAL':
                    w.add(instruction.argval)
                elif instruction.opname == 'LOAD_GLOBAL':
                    r.add(instruction.argval)

            if sorted(reads) != sorted(list(r)):
                raise Exception(f"The provided 'reads' parameter does not match the provided function")
            
            if sorted(writes) != sorted(list(w)):
                raise Exception(f"The provided 'writes' parameter does not match the provided function")
            
            self.__name = name
            self.__reads = reads
            self.__writes = writes
            self.__run = run
        except Exception as e:
            raise Exception(f"Error creating Task ({name}): {e}")
    
    def run(self):
        self.__run()

    def get_name(self) -> str:
        return self.__name
    
    def get_reads(self) -> list[str]:
        return self.__reads
    
    def get_writes(self) -> list[str]:
        return self.__writes
    
    def info(self) -> None:
        print(f"Task Info\nName : {self.__name}\nReads = {self.__reads}\nWrites = {self.__writes}\n")

class TaskSystem():
    __tasks: list[Task]
    __pred: Dict[str, list[str]]

    def __init__(self, tasks: list[Task], pred: Dict[str, list[str]]):
            try:
                task_names = [task.get_name() for task in tasks]

                # Check for duplicate task names
                duplicates = set(name for name in task_names if task_names.count(name) > 1)
                if duplicates:
                    raise Exception(f"'tasks' param contains duplicate task names: {', '.join(duplicates)}")
                
                # Check for nonexistent task names in precedence dictionary
                pred_names = set([key for key in pred.keys()] + [value for values in pred.values() for value in values])
                nonexistent_names = [name for name in pred_names if name not in task_names]
                if nonexistent_names:
                    raise Exception(f"'pred' param contains nonexistent task names: {', '.join(nonexistent_names)}")
                
                self.__tasks = tasks
                self.__pred = pred

                # Check for Bernstein conditions for each pair of tasks
                for i in range(len(tasks) - 1):
                    task_i = tasks[i]
                    task_i_name = task_i.get_name()
                    task_i_reads = set(task_i.get_reads())
                    task_i_writes = set(task_i.get_writes())
                    
                    for j in range(i + 1, len(tasks)):
                        task_j = tasks[j]
                        task_j_name = task_j.get_name()
                        task_j_reads = set(task_j.get_reads())
                        task_j_writes = set(task_j.get_writes())
                        
                        read_write_conflicts_i = task_i_reads & task_j_writes
                        read_write_conflicts_j = task_j_reads & task_i_writes
                        write_write_conflicts = task_i_writes & task_j_writes
                        
                        conflicts = read_write_conflicts_i | read_write_conflicts_j | write_write_conflicts
                        
                        if conflicts and (task_j_name not in self.get_dependencies(task_i_name) and 
                                        task_i_name not in self.get_dependencies(task_j_name)):
                            raise Exception(f"Tasks {task_i_name} and {task_j_name} have conflicting accesses to variables: {conflicts}, but no precedence relationship exists between them")
            except Exception as e:
                raise Exception(f"Error creating TaskSystem: {e}") from e
    
    def info(self) -> None:
        print(f"Task System Info\nTasks: {[task.get_name() for task in self.__tasks]}\nPred: {self.__pred}\n")
    
    def get_dependencies(self, task_name: str) -> list[str]:
        if task_name not in self.__pred:
            return []
        
        direct_deps = self.__pred[task_name]
        all_deps = set(direct_deps)
        
        for dep in direct_deps:
            all_deps.update(self.get_dependencies(dep))
        
        return all_deps

    def get_tasks_to_execute(self, pred: Dict[str, list[str]]) -> list[str]:
        # Get tasks that have no dependencies
        tasks_to_execute = [task_name for task_name in pred.keys() if len(pred[task_name]) == 0]

        # Check for cycles
        if len(tasks_to_execute) == 0 and len(pred.keys()) > 0:
            remaining_tasks = list(pred.keys())
            raise Exception(f"Cycle detected in precedence relationships. The following tasks are part of a dependency cycle: {', '.join(remaining_tasks)}")
            
        return tasks_to_execute

    def run_seq(self) -> None:
        try:
            pred = self.__pred.copy()
            while len(pred.keys()) > 0:
                # Get tasks that have no dependencies and check for cycles
                tasks_to_execute = self.get_tasks_to_execute(pred)
                
                # Execute tasks sequentially
                for task_name in tasks_to_execute:
                    [task for task in self.__tasks if task.get_name() == task_name][0].run()
                    pred.pop(task_name)

                # Remove executed tasks from dependencies of the remaining tasks
                for task_name in pred.keys():
                    pred[task_name] = [dependency for dependency in pred[task_name] if dependency not in tasks_to_execute]
                                
        except Exception as e:
            raise Exception(f"Error running tasks sequentially: {e}")

    def run(self) -> None:
        try:
            pred = self.__pred.copy()
            threads: list[Thread] = []
            while len(pred.keys()) > 0:
                # Get tasks that have no dependencies and check for cycles
                tasks_to_execute = self.get_tasks_to_execute(pred)

                # Execute tasks in parallel
                for task_name in tasks_to_execute:
                    task = [task for task in self.__tasks if task.get_name() == task_name][0]
                    t = Thread(target=task.run)
                    threads.append(t)
                    t.start()
                
                for thread in threads:
                    thread.join()
                
                threads.clear()

                # Remove executed tasks from precedence relationships
                for task_name in tasks_to_execute:
                    pred.pop(task_name)

                # Remove executed tasks from dependencies of the remaining tasks
                for task_name in pred.keys():
                        pred[task_name] = [dependency for dependency in pred[task_name] if dependency not in tasks_to_execute]               
                    
        except Exception as e:
            raise Exception(f"Error running tasks in parallel: {e}")
    
    def draw(self) -> None:
        try:
            node_key_name: Dict[str, str] = dict()
            graph = graphviz.Digraph(name="Task System Precedence Relationships", comment="Task System")
            
            # Add the nodes to the graph, and fill the node_key_name dictionary
            for index, task in enumerate(self.__tasks):
                graph.node(name=f"{index}", label=task.get_name())
                node_key_name[task.get_name()] = f"{index}"
            
            # Add the edges to the graph based on the defined precedence relationships
            edges = []
            for dist_task in self.__pred.keys():
                for src_task in self.__pred[dist_task]:
                    edges.append(f"{node_key_name[src_task]}{node_key_name[dist_task]}")    

            graph.edges(edges)

            # Save the generated graph
            date_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            graph.render(f"./graphs/{date_time}/task-system", format="png", view=True)

        except Exception as e:
            raise Exception(f"Error drawing the precedence relationships graph: {e}")

    def det_test_rnd(self, globals_dict: dict, test_vals: int = 3, value_set_rep: int = 3) -> None:
            global_vars: set[str] = {var for task in self.__tasks for var in task.get_reads() + task.get_writes()}

            for i in range(test_vals):
                initial_global_vals = {var: random.randint(1, 10) for var in global_vars}
                for var in global_vars:
                    globals_dict[var] = initial_global_vals[var]
                
                print(f"Value set N°{i+1}: {initial_global_vals}")                

                for i in range(value_set_rep):
                    self.run()

                    if i == 0:
                        for var in global_vars:
                            initial_global_vals[var] = globals_dict[var]
                        print(f"Output for value set N°{i+1}: {initial_global_vals}")
                    else:
                        current_global_vals = {var: globals_dict[var] for var in global_vars}
                        if current_global_vals != initial_global_vals:
                            print(f"Task system is not deterministic: output for value set N°{i+1} is {current_global_vals}, but expected output is {initial_global_vals}.")
                            return
                        
            print("Task system is deterministic.")
    
    def par_cost(self, warmup_runs: int = 5, num_runs: int = 3) -> None:
        # Warm-up runs
        for _ in range(warmup_runs):
            self.run_seq()
            self.run()
        
        # Calculate average execution time for both methods
        sequential_execution_time = timeit(self.run_seq, number=num_runs) / num_runs
        parallel_execution_time = timeit(self.run, number=num_runs) / num_runs

        print(f"Average sequential execution time ({num_runs} runs) = {sequential_execution_time:.6f} seconds")
        print(f"Average parallel execution time ({num_runs} runs) = {parallel_execution_time:.6f} seconds")
        print("Sequential Execution" if sequential_execution_time < parallel_execution_time else "Parallel Execution", f"is faster by {abs(sequential_execution_time-parallel_execution_time):.6f} seconds")