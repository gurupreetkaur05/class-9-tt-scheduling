"""Realistic sample data for a Class 9 Indian school timetable."""

from models import Teacher, Subject, Section, Assignment, TimetableData, Grade, Cluster


def create_sample_data() -> TimetableData:
    """Create sample data: 3 sections, 10 subjects, 15 teachers.

    Total periods per section per week = 48 (6 days x 8 periods).
    Subject periods must sum to 48 for each section.
    """

    sections = [
        Section(id=0, name="9A"),
        Section(id=1, name="9B"),
        Section(id=2, name="9C"),
    ]

    # Periods per week must sum to 48 (6 days x 8 periods)
    subjects = [
        Subject(id=0, name="Mathematics", periods_per_week=7),
        Subject(id=1, name="Science", periods_per_week=7),
        Subject(id=2, name="English", periods_per_week=6),
        Subject(id=3, name="Hindi", periods_per_week=5),
        Subject(id=4, name="Social Science", periods_per_week=6),
        Subject(id=5, name="Sanskrit", periods_per_week=4),
        Subject(id=6, name="Computer Science", periods_per_week=3),
        Subject(id=7, name="Physical Education", periods_per_week=3),
        Subject(id=8, name="Art", periods_per_week=3),
        Subject(id=9, name="Moral Science", periods_per_week=4),
    ]
    # Total = 7+7+6+5+6+4+3+3+3+4 = 48 ✓

    teachers = [
        Teacher(id=0, name="Mrs. Sharma", subject_ids=[0]),         # Math
        Teacher(id=1, name="Mr. Verma", subject_ids=[0]),            # Math
        Teacher(id=2, name="Mrs. Gupta", subject_ids=[1]),           # Science
        Teacher(id=3, name="Mr. Singh", subject_ids=[1]),            # Science
        Teacher(id=4, name="Mrs. Patel", subject_ids=[2]),           # English
        Teacher(id=5, name="Mr. Kumar", subject_ids=[2]),            # English
        Teacher(id=6, name="Mrs. Joshi", subject_ids=[3]),           # Hindi
        Teacher(id=7, name="Mr. Mehta", subject_ids=[4]),            # Social Science
        Teacher(id=8, name="Mrs. Reddy", subject_ids=[4]),           # Social Science
        Teacher(id=9, name="Mr. Rao", subject_ids=[5]),              # Sanskrit
        Teacher(id=10, name="Mrs. Das", subject_ids=[6]),            # Computer Science
        Teacher(id=11, name="Mr. Chauhan", subject_ids=[7]),         # Physical Education
        Teacher(id=12, name="Mrs. Iyer", subject_ids=[8]),           # Art
        Teacher(id=13, name="Mr. Nair", subject_ids=[9]),            # Moral Science
        Teacher(id=14, name="Mrs. Banerjee", subject_ids=[3, 5]),    # Hindi + Sanskrit
    ]

    # Assignments: who teaches what to which section
    # For subjects with multiple teachers, distribute across sections
    assignments = [
        # Mathematics: Sharma teaches 9A, Verma teaches 9B & 9C
        Assignment(teacher_id=0, subject_id=0, section_id=0),
        Assignment(teacher_id=1, subject_id=0, section_id=1),
        Assignment(teacher_id=1, subject_id=0, section_id=2),

        # Science: Gupta teaches 9A & 9B, Singh teaches 9C
        Assignment(teacher_id=2, subject_id=1, section_id=0),
        Assignment(teacher_id=2, subject_id=1, section_id=1),
        Assignment(teacher_id=3, subject_id=1, section_id=2),

        # English: Patel teaches 9A & 9B, Kumar teaches 9C
        Assignment(teacher_id=4, subject_id=2, section_id=0),
        Assignment(teacher_id=4, subject_id=2, section_id=1),
        Assignment(teacher_id=5, subject_id=2, section_id=2),

        # Hindi: Joshi teaches 9A, Banerjee teaches 9B & 9C
        Assignment(teacher_id=6, subject_id=3, section_id=0),
        Assignment(teacher_id=14, subject_id=3, section_id=1),
        Assignment(teacher_id=14, subject_id=3, section_id=2),

        # Social Science: Mehta teaches 9A & 9B, Reddy teaches 9C
        Assignment(teacher_id=7, subject_id=4, section_id=0),
        Assignment(teacher_id=7, subject_id=4, section_id=1),
        Assignment(teacher_id=8, subject_id=4, section_id=2),

        # Sanskrit: Rao teaches 9A, Banerjee teaches 9B & 9C
        Assignment(teacher_id=9, subject_id=5, section_id=0),
        Assignment(teacher_id=14, subject_id=5, section_id=1),
        Assignment(teacher_id=14, subject_id=5, section_id=2),

        # Computer Science: Das teaches all
        Assignment(teacher_id=10, subject_id=6, section_id=0),
        Assignment(teacher_id=10, subject_id=6, section_id=1),
        Assignment(teacher_id=10, subject_id=6, section_id=2),

        # Physical Education: Chauhan teaches all
        Assignment(teacher_id=11, subject_id=7, section_id=0),
        Assignment(teacher_id=11, subject_id=7, section_id=1),
        Assignment(teacher_id=11, subject_id=7, section_id=2),

        # Art: Iyer teaches all
        Assignment(teacher_id=12, subject_id=8, section_id=0),
        Assignment(teacher_id=12, subject_id=8, section_id=1),
        Assignment(teacher_id=12, subject_id=8, section_id=2),

        # Moral Science: Nair teaches all
        Assignment(teacher_id=13, subject_id=9, section_id=0),
        Assignment(teacher_id=13, subject_id=9, section_id=1),
        Assignment(teacher_id=13, subject_id=9, section_id=2),
    ]

    return TimetableData(
        teachers=teachers,
        subjects=subjects,
        sections=sections,
        assignments=assignments,
        num_days=6,
        num_periods=8,
    )


def create_sample_cluster_data() -> Cluster:
    """Create sample cluster: Middle School (Grades 8-9).

    Grade 8: 2 sections, 8 subjects summing to 48
    Grade 9: 3 sections, 10 subjects summing to 48
    Some teachers shared across grades.
    """

    # --- Grade 8 subjects (IDs 100-107 to avoid collision with Grade 9's 0-9) ---
    grade8_subjects = [
        Subject(id=100, name="Mathematics", periods_per_week=7),
        Subject(id=101, name="Science", periods_per_week=7),
        Subject(id=102, name="English", periods_per_week=7),
        Subject(id=103, name="Hindi", periods_per_week=6),
        Subject(id=104, name="Social Science", periods_per_week=6),
        Subject(id=105, name="Computer Science", periods_per_week=4),
        Subject(id=106, name="Physical Education", periods_per_week=4),
        Subject(id=107, name="Art", periods_per_week=7),
    ]
    # Total = 7+7+7+6+6+4+4+7 = 48 ✓

    # Grade 8 sections (IDs 100-101)
    grade8_sections = [
        Section(id=100, name="8A", grade_id=0),
        Section(id=101, name="8B", grade_id=0),
    ]

    # --- Grade 9 subjects (same as existing, IDs 0-9) ---
    grade9_subjects = [
        Subject(id=0, name="Mathematics", periods_per_week=7),
        Subject(id=1, name="Science", periods_per_week=7),
        Subject(id=2, name="English", periods_per_week=6),
        Subject(id=3, name="Hindi", periods_per_week=5),
        Subject(id=4, name="Social Science", periods_per_week=6),
        Subject(id=5, name="Sanskrit", periods_per_week=4),
        Subject(id=6, name="Computer Science", periods_per_week=3),
        Subject(id=7, name="Physical Education", periods_per_week=3),
        Subject(id=8, name="Art", periods_per_week=3),
        Subject(id=9, name="Moral Science", periods_per_week=4),
    ]
    # Total = 48 ✓

    # Grade 9 sections (IDs 0-2)
    grade9_sections = [
        Section(id=0, name="9A", grade_id=1),
        Section(id=1, name="9B", grade_id=1),
        Section(id=2, name="9C", grade_id=1),
    ]

    # Teachers (shared across grades, IDs 0-17)
    teachers = [
        Teacher(id=0, name="Mrs. Sharma", subject_ids=[0, 100]),       # Math (both grades)
        Teacher(id=1, name="Mr. Verma", subject_ids=[0, 100]),          # Math (both grades)
        Teacher(id=2, name="Mrs. Gupta", subject_ids=[1, 101]),         # Science (both grades)
        Teacher(id=3, name="Mr. Singh", subject_ids=[1, 101]),          # Science (both grades)
        Teacher(id=4, name="Mrs. Patel", subject_ids=[2, 102]),         # English (both grades)
        Teacher(id=5, name="Mr. Kumar", subject_ids=[2, 102]),          # English (both grades)
        Teacher(id=6, name="Mrs. Joshi", subject_ids=[3, 103]),         # Hindi (both grades)
        Teacher(id=7, name="Mr. Mehta", subject_ids=[4, 104]),          # Social Science (both grades)
        Teacher(id=8, name="Mrs. Reddy", subject_ids=[4, 104]),         # Social Science (both grades)
        Teacher(id=9, name="Mr. Rao", subject_ids=[5]),                  # Sanskrit (Grade 9 only)
        Teacher(id=10, name="Mrs. Das", subject_ids=[6, 105]),           # Computer Science (both)
        Teacher(id=11, name="Mr. Chauhan", subject_ids=[7, 106]),        # PE (both grades)
        Teacher(id=12, name="Mrs. Iyer", subject_ids=[8, 107]),          # Art (both grades)
        Teacher(id=13, name="Mr. Nair", subject_ids=[9]),                # Moral Science (Grade 9 only)
        Teacher(id=14, name="Mrs. Banerjee", subject_ids=[3, 5, 103]),   # Hindi + Sanskrit (G9) + Hindi (G8)
        Teacher(id=15, name="Mr. Tiwari", subject_ids=[103]),            # Hindi (Grade 8 only)
        Teacher(id=16, name="Mrs. Saxena", subject_ids=[104]),           # Social Science (Grade 8 only)
        Teacher(id=17, name="Mr. Pillai", subject_ids=[107]),            # Art (Grade 8 only)
    ]

    # Grade 8 assignments
    grade8_assignments = [
        # Math: Sharma teaches 8A, Verma teaches 8B
        Assignment(teacher_id=0, subject_id=100, section_id=100),
        Assignment(teacher_id=1, subject_id=100, section_id=101),
        # Science: Gupta teaches 8A, Singh teaches 8B
        Assignment(teacher_id=2, subject_id=101, section_id=100),
        Assignment(teacher_id=3, subject_id=101, section_id=101),
        # English: Patel teaches 8A, Kumar teaches 8B
        Assignment(teacher_id=4, subject_id=102, section_id=100),
        Assignment(teacher_id=5, subject_id=102, section_id=101),
        # Hindi: Joshi teaches 8A, Tiwari teaches 8B
        Assignment(teacher_id=6, subject_id=103, section_id=100),
        Assignment(teacher_id=15, subject_id=103, section_id=101),
        # Social Science: Mehta teaches 8A, Saxena teaches 8B
        Assignment(teacher_id=7, subject_id=104, section_id=100),
        Assignment(teacher_id=16, subject_id=104, section_id=101),
        # Computer Science: Das teaches both
        Assignment(teacher_id=10, subject_id=105, section_id=100),
        Assignment(teacher_id=10, subject_id=105, section_id=101),
        # PE: Chauhan teaches both
        Assignment(teacher_id=11, subject_id=106, section_id=100),
        Assignment(teacher_id=11, subject_id=106, section_id=101),
        # Art: Iyer teaches 8A, Pillai teaches 8B
        Assignment(teacher_id=12, subject_id=107, section_id=100),
        Assignment(teacher_id=17, subject_id=107, section_id=101),
    ]

    # Grade 9 assignments (same as original)
    grade9_assignments = [
        Assignment(teacher_id=0, subject_id=0, section_id=0),
        Assignment(teacher_id=1, subject_id=0, section_id=1),
        Assignment(teacher_id=1, subject_id=0, section_id=2),
        Assignment(teacher_id=2, subject_id=1, section_id=0),
        Assignment(teacher_id=2, subject_id=1, section_id=1),
        Assignment(teacher_id=3, subject_id=1, section_id=2),
        Assignment(teacher_id=4, subject_id=2, section_id=0),
        Assignment(teacher_id=4, subject_id=2, section_id=1),
        Assignment(teacher_id=5, subject_id=2, section_id=2),
        Assignment(teacher_id=6, subject_id=3, section_id=0),
        Assignment(teacher_id=14, subject_id=3, section_id=1),
        Assignment(teacher_id=14, subject_id=3, section_id=2),
        Assignment(teacher_id=7, subject_id=4, section_id=0),
        Assignment(teacher_id=7, subject_id=4, section_id=1),
        Assignment(teacher_id=8, subject_id=4, section_id=2),
        Assignment(teacher_id=9, subject_id=5, section_id=0),
        Assignment(teacher_id=14, subject_id=5, section_id=1),
        Assignment(teacher_id=14, subject_id=5, section_id=2),
        Assignment(teacher_id=10, subject_id=6, section_id=0),
        Assignment(teacher_id=10, subject_id=6, section_id=1),
        Assignment(teacher_id=10, subject_id=6, section_id=2),
        Assignment(teacher_id=11, subject_id=7, section_id=0),
        Assignment(teacher_id=11, subject_id=7, section_id=1),
        Assignment(teacher_id=11, subject_id=7, section_id=2),
        Assignment(teacher_id=12, subject_id=8, section_id=0),
        Assignment(teacher_id=12, subject_id=8, section_id=1),
        Assignment(teacher_id=12, subject_id=8, section_id=2),
        Assignment(teacher_id=13, subject_id=9, section_id=0),
        Assignment(teacher_id=13, subject_id=9, section_id=1),
        Assignment(teacher_id=13, subject_id=9, section_id=2),
    ]

    grade8 = Grade(id=0, name="Class 8", subjects=grade8_subjects, sections=grade8_sections, assignments=grade8_assignments)
    grade9 = Grade(id=1, name="Class 9", subjects=grade9_subjects, sections=grade9_sections, assignments=grade9_assignments)

    return Cluster(
        name="Middle School (Grades 8-9)",
        num_days=6,
        num_periods=8,
        grades=[grade8, grade9],
        teachers=teachers,
    )


if __name__ == "__main__":
    data = create_sample_data()
    print(f"Sections: {len(data.sections)}")
    print(f"Subjects: {len(data.subjects)}")
    print(f"Teachers: {len(data.teachers)}")
    print(f"Assignments: {len(data.assignments)}")
    for sec in data.sections:
        total = data.total_periods_for_section(sec.id)
        print(f"  {sec.name}: {total} periods/week (need {data.num_days * data.num_periods})")

    print("\n--- Cluster Data ---")
    cluster = create_sample_cluster_data()
    td = cluster.to_timetable_data()
    print(f"Cluster: {cluster.name}")
    print(f"Grades: {len(cluster.grades)}")
    print(f"Total sections: {len(td.sections)}")
    print(f"Total subjects: {len(td.subjects)}")
    print(f"Total teachers: {len(td.teachers)}")
    print(f"Total assignments: {len(td.assignments)}")
    for sec in td.sections:
        total = td.total_periods_for_section(sec.id)
        print(f"  {sec.name}: {total} periods/week (need {td.num_days * td.num_periods})")
