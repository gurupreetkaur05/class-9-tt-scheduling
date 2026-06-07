"""OR-Tools CP-SAT solver for timetable scheduling."""

from ortools.sat.python import cp_model
from models import TimetableData

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


class SolutionCollector(cp_model.CpSolverSolutionCallback):
    """Collects up to max_solutions from the solver."""

    def __init__(self, variables, max_solutions=5):
        super().__init__()
        self._variables = variables
        self._max_solutions = max_solutions
        self._solutions = []

    def on_solution_callback(self):
        solution = {}
        for key, var in self._variables.items():
            solution[key] = self.value(var)
        self._solutions.append(solution)
        if len(self._solutions) >= self._max_solutions:
            self.stop_search()

    @property
    def solutions(self):
        return self._solutions


def build_model(data: TimetableData):
    """Build the CP-SAT model with hard constraints.

    Returns (model, assign_vars) where assign_vars is a dict:
        assign[(teacher_id, subject_id, section_id, day, period)] = BoolVar

    The 5D key ensures a teacher who teaches multiple subjects to the same
    section gets separate variables for each subject.
    """
    model = cp_model.CpModel()
    assign = {}

    # Create variables for each assignment x timeslot
    for a in data.assignments:
        for d in range(data.num_days):
            for p in range(data.num_periods):
                var_name = f"a_t{a.teacher_id}_sub{a.subject_id}_s{a.section_id}_d{d}_p{p}"
                assign[(a.teacher_id, a.subject_id, a.section_id, d, p)] = model.new_bool_var(var_name)

    # --- Hard Constraints ---

    # 1. Each section must have exactly one teacher (one assignment) per slot
    for sec in data.sections:
        section_assignments = data.get_assignments_for_section(sec.id)
        for d in range(data.num_days):
            for p in range(data.num_periods):
                model.add(
                    sum(
                        assign[(a.teacher_id, a.subject_id, sec.id, d, p)]
                        for a in section_assignments
                    ) == 1
                )

    # 2. No teacher can be in two places at the same time
    #    (across all their assignments in different sections)
    for teacher in data.teachers:
        teacher_assignments = [a for a in data.assignments if a.teacher_id == teacher.id]
        if len(teacher_assignments) <= 1:
            continue
        for d in range(data.num_days):
            for p in range(data.num_periods):
                model.add(
                    sum(
                        assign[(a.teacher_id, a.subject_id, a.section_id, d, p)]
                        for a in teacher_assignments
                    ) <= 1
                )

    # 3. Each assignment must meet the required subject hours per week
    for a in data.assignments:
        subject = data.get_subject_by_id(a.subject_id)
        model.add(
            sum(
                assign[(a.teacher_id, a.subject_id, a.section_id, d, p)]
                for d in range(data.num_days)
                for p in range(data.num_periods)
            ) == subject.periods_per_week
        )

    return model, assign


def solve(data: TimetableData, extra_constraints_code: list[str] | None = None,
          max_solutions: int = 5, time_limit_seconds: float = 30.0):
    """Solve the timetable and return solutions.

    Args:
        data: The timetable input data.
        extra_constraints_code: List of Python code strings to exec against the model.
        max_solutions: Maximum number of solutions to collect.
        time_limit_seconds: Solver time limit.

    Returns:
        dict with keys:
            - status: str ("OPTIMAL", "FEASIBLE", "INFEASIBLE", "ERROR")
            - solutions: list of solution dicts, each mapping
              (section_id, day, period) -> (teacher_name, subject_name)
            - error: str or None
    """
    model, assign = build_model(data)

    # Apply extra constraints from LLM-generated code
    if extra_constraints_code:
        for code in extra_constraints_code:
            try:
                safe_globals = {
                    "__builtins__": {},
                    "model": model,
                    "assign": assign,
                    "data": data,
                    "NUM_DAYS": data.num_days,
                    "NUM_PERIODS": data.num_periods,
                    "NUM_SECTIONS": len(data.sections),
                    "range": range,
                    "sum": sum,
                    "len": len,
                    "any": any,
                    "all": all,
                    "True": True,
                    "False": False,
                    "print": print,
                }
                exec(code, safe_globals, {})
            except Exception as e:
                return {
                    "status": "ERROR",
                    "solutions": [],
                    "error": f"Error in constraint code: {e}\n\nCode:\n{code}",
                }

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds
    solver.parameters.enumerate_all_solutions = True

    collector = SolutionCollector(assign, max_solutions)
    status = solver.solve(model, collector)

    status_name = {
        cp_model.OPTIMAL: "OPTIMAL",
        cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE",
        cp_model.MODEL_INVALID: "MODEL_INVALID",
        cp_model.UNKNOWN: "UNKNOWN",
    }.get(status, "UNKNOWN")

    if status in (cp_model.INFEASIBLE, cp_model.MODEL_INVALID):
        return {
            "status": status_name,
            "solutions": [],
            "error": "No valid timetable found. Your constraints may conflict — try removing the most recent constraint.",
        }

    # Convert solutions to readable format
    readable_solutions = []
    for sol in collector.solutions:
        timetable = {}  # (section_id, day, period) -> (teacher_name, subject_name)
        for (t_id, sub_id, s_id, d, p), val in sol.items():
            if val == 1:
                teacher = data.get_teacher_by_id(t_id)
                subject = data.get_subject_by_id(sub_id)
                timetable[(s_id, d, p)] = (teacher.name, subject.name)
        readable_solutions.append(timetable)

    return {
        "status": status_name,
        "solutions": readable_solutions,
        "error": None,
    }


def print_timetable(data: TimetableData, timetable: dict, section_id: int):
    """Print a timetable grid for a section."""
    section = data.get_section_by_id(section_id)
    print(f"\n{'=' * 80}")
    print(f"  Timetable for Section {section.name}")
    print(f"{'=' * 80}")

    # Header
    header = f"{'Period':<10}"
    for d in range(data.num_days):
        day_name = DAY_NAMES[d] if d < len(DAY_NAMES) else f"Day{d}"
        header += f"{day_name:<14}"
    print(header)
    print("-" * 80)

    # Rows
    for p in range(data.num_periods):
        row = f"P{p + 1:<9}"
        for d in range(data.num_days):
            entry = timetable.get((section_id, d, p))
            if entry:
                teacher_name, subject_name = entry
                short_teacher = teacher_name.split()[-1][:6]
                short_subject = subject_name[:6]
                cell = f"{short_subject}/{short_teacher}"
            else:
                cell = "---"
            row += f"{cell:<14}"
        print(row)


if __name__ == "__main__":
    from sample_data import create_sample_data

    data = create_sample_data()
    print("Solving timetable...")
    result = solve(data, max_solutions=3)

    print(f"\nStatus: {result['status']}")
    print(f"Solutions found: {len(result['solutions'])}")

    if result['error']:
        print(f"Error: {result['error']}")

    for i, timetable in enumerate(result['solutions']):
        print(f"\n{'#' * 80}")
        print(f"  SOLUTION {i + 1}")
        print(f"{'#' * 80}")
        for sec in data.sections:
            print_timetable(data, timetable, sec.id)
