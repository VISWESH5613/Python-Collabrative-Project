# OptiSchedule - Conflict-Free Campus Timetable & Facility Allocation System
# Course: Computational Thinking and Programming (2026CSAE100)
# Team: Mehul Sharma (Leader, E26EPYU0007), Nannapaneni Guna Sri Sai Viswesh (E26EPYU0002),
#       Adhyyan Sharma (E26EPYU0006), Harsh Verma (E26EPYU0008)

import csv
import os

# ==============================================================================
# SECTION 1: CONSTANTS & CAMPUS CONFIGURATION
# ==============================================================================
DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")

TIME_SLOTS = (
    "09:00-10:00",
    "10:00-11:00",
    "11:00-12:00",
    "12:00-01:00",
    "01:00-02:00",  # Protected Lunch Hour
    "02:00-03:00",
    "03:00-04:00",
    "04:00-05:00",
)

LUNCH_SLOT = "01:00-02:00"
OUTPUT_DIR = "output"

# Block position numbers used to calculate walking distance between buildings
BLOCK_POSITIONS = {
    "Block A": 1,
    "Block B": 2,
    "Block C": 3,
    "Lab Block": 4,
}


# ==============================================================================
# SECTION 2: DATA MODEL CLASSES (NO DECORATORS, SIMPLE & CLEAN OOP)
# ==============================================================================
class Room:
    """Represents a classroom, tutorial room, or specialized lab."""

    def __init__(self, room_id, block, floor, room_type, capacity, equipment_count):
        self.room_id = room_id
        self.block = block
        self.floor = int(floor)
        self.room_type = room_type
        self.capacity = int(capacity)
        self.equipment_count = int(equipment_count)

    def is_lab(self):
        return "lab" in self.room_type.lower()

    def __str__(self):
        return f"{self.room_id} ({self.block}, Fl {self.floor})"


class Course:
    """Represents a course subject with weekly sessions, duration, lab needs, and faculty."""

    def __init__(self, course_code, course_name, session_type, duration_hrs, weekly_sessions, req_equipment, faculty_id):
        self.course_code = course_code
        self.course_name = course_name
        self.session_type = session_type
        self.duration_hrs = int(duration_hrs)
        self.weekly_sessions = int(weekly_sessions)
        self.req_equipment = req_equipment
        self.faculty_id = faculty_id

    def is_lab(self):
        return self.req_equipment.lower() != "none"

    def __str__(self):
        return f"{self.course_code} - {self.course_name} ({self.session_type})"


class Batch:
    """Represents a student section batch (e.g., B1..B24) with student count & roll range."""

    def __init__(self, batch_id, department, student_count, roll_start, roll_end):
        self.batch_id = batch_id
        self.department = department
        self.student_count = int(student_count)
        self.roll_start = roll_start
        self.roll_end = roll_end

    def contains_roll(self, roll_no):
        return self.roll_start <= roll_no <= self.roll_end

    def __str__(self):
        return f"{self.batch_id} ({self.student_count} students)"


class Session:
    """Represents one scheduled class session in the timetable grid."""

    def __init__(self, course, room, score, distance_penalty):
        self.course = course
        self.room = room
        self.score = score
        self.distance_penalty = distance_penalty

    def short_label(self):
        return f"{self.course.course_code}[{self.room.room_id}]"


# ==============================================================================
# SECTION 3: CSV FILE LOADERS (WITH BUILT-IN FALLBACK DEFAULTS)
# ==============================================================================
def load_rooms(filepath="rooms.csv"):
    """Reads campus rooms from rooms.csv into a list of Room objects."""
    rooms = []
    if not os.path.exists(filepath):
        print(f"[!] {filepath} not found. Using built-in sample rooms.")
        return [
            Room("A-101", "Block A", 1, "Lecture Hall", 150, 0),
            Room("A-102", "Block A", 1, "Classroom", 75, 0),
            Room("A-301", "Block A", 3, "Tutorial Room", 40, 0),
            Room("L-101", "Lab Block", 1, "CS Lab", 70, 70),
        ]

    with open(filepath, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rooms.append(
                Room(
                    row["room_id"].strip(),
                    row["block"].strip(),
                    row["floor"].strip(),
                    row["room_type"].strip(),
                    row["capacity"].strip(),
                    row["equipment_count"].strip(),
                )
            )
    return rooms


def load_courses(filepath="courses.csv"):
    """Reads courses from courses.csv into a list of Course objects."""
    courses = []
    if not os.path.exists(filepath):
        print(f"[!] {filepath} not found. Using built-in sample courses.")
        return [
            Course("2026CSAE100", "Computational Thinking", "Lecture", 1, 2, "None", "FAC01"),
            Course("2026CSAE100L", "Computational Thinking Lab", "Lab", 2, 1, "CS Lab", "FAC01"),
            Course("2026MATH102", "Linear Algebra", "Lecture", 1, 2, "None", "FAC03"),
        ]

    with open(filepath, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            courses.append(
                Course(
                    row["course_code"].strip(),
                    row["course_name"].strip(),
                    row["session_type"].strip(),
                    row["duration_hrs"].strip(),
                    row["weekly_sessions"].strip(),
                    row["req_equipment"].strip(),
                    row["faculty_id"].strip(),
                )
            )
    return courses


def load_batches(filepath="batches.csv"):
    """Reads student batches (B1..B24) from batches.csv into a list of Batch objects."""
    batches = []
    if not os.path.exists(filepath):
        print(f"[!] {filepath} not found. Using built-in sample batches.")
        return [
            Batch("B1", "EPY / CSE", 60, "E26STU00001", "E26STU00417"),
            Batch("B4", "EPY / CSE", 35, "E26STU01252", "E26STU01668"),
        ]

    with open(filepath, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            batches.append(
                Batch(
                    row["batch_id"].strip(),
                    row["department"].strip(),
                    row["student_count"].strip(),
                    row["roll_range_start"].strip(),
                    row["roll_range_end"].strip(),
                )
            )
    return batches


# ==============================================================================
# SECTION 4: WALKING DISTANCE & MULTI-FACTOR DECISION POINTER FUNCTIONS
# ==============================================================================
def calculate_distance_penalty(prev_room, next_room):
    """
    Calculates walking penalty between two rooms using Milestone 1 formula:
        Distance Penalty = (Block Difference * 10) + (Floor Difference * 3)
    """
    if prev_room is None:
        return 0
    block1 = BLOCK_POSITIONS.get(prev_room.block, 1)
    block2 = BLOCK_POSITIONS.get(next_room.block, 1)
    block_diff = abs(block1 - block2)
    floor_diff = abs(prev_room.floor - next_room.floor)
    return (block_diff * 10) + (floor_diff * 3)


def score_room_for_session(batch, course, room, prev_room, classes_today):
    """
    Evaluates a candidate room using the 100-Point Multi-Factor Decision Pointer:
      - Returns None if hard constraints fail (capacity too small or wrong lab equipment).
      - Otherwise returns (total_score, distance_penalty).
    """
    # 1. Hard Capacity Check
    if room.capacity < batch.student_count:
        return None

    # 2. Hard Equipment & Room-Type Check
    if course.is_lab():
        if room.room_type.lower() != course.req_equipment.lower():
            return None
        if room.equipment_count < batch.student_count:
            return None
    else:
        # Keep specialized labs free for practical courses
        if room.is_lab():
            return None

    # 3. Factor 1: Walking Distance Proximity (30 Points Max)
    dist_penalty = calculate_distance_penalty(prev_room, room)
    distance_score = max(0, 30 - dist_penalty)

    # 4. Factor 2: Seating Capacity Fit (25 Points Max)
    if room.capacity <= batch.student_count * 1.35:
        capacity_score = 25
    elif room.capacity <= batch.student_count * 2.0:
        capacity_score = 18
    else:
        capacity_score = 10

    # 5. Factor 3: Room Type & Equipment Match (25 Points Max)
    if course.is_lab():
        equipment_score = 25
    elif course.session_type.lower() == "tutorial" and "tutorial" in room.room_type.lower():
        equipment_score = 25
    elif course.session_type.lower() == "lecture" and "tutorial" not in room.room_type.lower():
        equipment_score = 25
    else:
        equipment_score = 18

    # 6. Factor 4: Daily Flow & Sequencing (20 Points Max)
    if classes_today < 4:
        sequence_score = 20
    elif classes_today == 4:
        sequence_score = 12
    else:
        sequence_score = 5

    total_score = distance_score + capacity_score + equipment_score + sequence_score
    return (total_score, dist_penalty)


# ==============================================================================
# SECTION 5: CORE TIMETABLE ENGINE (OPTI-SCHEDULE)
# ==============================================================================
class OptiSchedule:
    """Generates conflict-free timetables, answers queries, and computes analytics."""

    def __init__(self, rooms, courses, batches):
        self.rooms = rooms
        # Schedule heavy 2-hour labs first so specialized labs are secured early
        self.courses = sorted(courses, key=lambda c: c.duration_hrs, reverse=True)
        self.batches = batches
        self.timetable = {}
        self.unscheduled = []

    def generate(self):
        """Allocates all batch sessions without room, teacher, or batch clashes."""
        self.timetable = {}
        for b in self.batches:
            self.timetable[b.batch_id] = {}
            for d in DAYS:
                self.timetable[b.batch_id][d] = {}
                for s in TIME_SLOTS:
                    self.timetable[b.batch_id][d][s] = "LUNCH" if s == LUNCH_SLOT else None

        booked_rooms = set()
        booked_teachers = set()
        self.unscheduled = []

        for batch in self.batches:
            for course in self.courses:
                for s_idx in range(course.weekly_sessions):
                    placed = False
                    # Rotate starting day to spread sessions across Monday-Friday
                    day_order = [(s_idx + offset) % len(DAYS) for offset in range(len(DAYS))]

                    for d_idx in day_order:
                        day = DAYS[d_idx]

                        # Avoid scheduling the same course twice on one day
                        already_today = False
                        for slot_name in TIME_SLOTS:
                            entry = self.timetable[batch.batch_id][day][slot_name]
                            if isinstance(entry, Session) and entry.course.course_code == course.course_code:
                                already_today = True
                                break
                        if already_today:
                            continue

                        # Count existing classes on this day for sequencing score
                        classes_today = 0
                        for slot_name in TIME_SLOTS:
                            if isinstance(self.timetable[batch.batch_id][day][slot_name], Session):
                                classes_today += 1

                        # Try each time slot (checking duration_hrs consecutive slots)
                        for idx in range(len(TIME_SLOTS) - course.duration_hrs + 1):
                            needed_slots = TIME_SLOTS[idx : idx + course.duration_hrs]

                            # Never cross or occupy the protected LUNCH_SLOT
                            if LUNCH_SLOT in needed_slots:
                                continue

                            # Check batch and teacher availability across all needed slots
                            slot_clash = False
                            for sl in needed_slots:
                                if self.timetable[batch.batch_id][day][sl] is not None:
                                    slot_clash = True
                                    break
                                if (day, sl, course.faculty_id) in booked_teachers:
                                    slot_clash = True
                                    break
                            if slot_clash:
                                continue

                            # Find the previous class room on the same day for walking distance
                            prev_room = None
                            for prev_idx in range(idx - 1, -1, -1):
                                prev_sl = TIME_SLOTS[prev_idx]
                                if prev_sl == LUNCH_SLOT:
                                    break  # Lunch break resets rush walking penalty
                                prev_entry = self.timetable[batch.batch_id][day][prev_sl]
                                if isinstance(prev_entry, Session):
                                    prev_room = prev_entry.room
                                    break

                            # Evaluate all free rooms using the Decision Pointer
                            candidates = []
                            for room in self.rooms:
                                room_busy = False
                                for sl in needed_slots:
                                    if (day, sl, room.room_id) in booked_rooms:
                                        room_busy = True
                                        break
                                if room_busy:
                                    continue

                                result = score_room_for_session(batch, course, room, prev_room, classes_today)
                                if result is not None:
                                    score, penalty = result
                                    candidates.append((score, room, penalty))

                            if candidates:
                                # Pick candidate room with highest Decision Pointer score (Lambda #2)
                                best_score, best_room, best_penalty = max(candidates, key=lambda item: item[0])
                                session_obj = Session(course, best_room, best_score, best_penalty)

                                for sl in needed_slots:
                                    self.timetable[batch.batch_id][day][sl] = session_obj
                                    booked_rooms.add((day, sl, best_room.room_id))
                                    booked_teachers.add((day, sl, course.faculty_id))

                                placed = True
                                break

                        if placed:
                            break

                    if not placed:
                        self.unscheduled.append((batch.batch_id, course.course_code))

    def print_grid(self, title, grid_rows):
        """Prints a clean weekly grid for a batch or a faculty member."""
        width = 14 + len(TIME_SLOTS) * 20
        print("\n" + "=" * width)
        print(title.center(width))
        print("=" * width)
        header = f"{'Day':<10} | " + " | ".join(f"{s:<17}" for s in TIME_SLOTS)
        print(header)
        print("-" * width)
        for day in DAYS:
            cells = []
            for sl in TIME_SLOTS:
                val = grid_rows[day][sl]
                if val is None:
                    cells.append(f"{'FREE':<17}")
                elif isinstance(val, Session):
                    cells.append(f"{val.short_label():<17}")
                else:
                    cells.append(f"{str(val):<17}")
            print(f"{day:<10} | " + " | ".join(cells))
        print("=" * width)

    def view_teacher_schedule(self, faculty_id):
        """Builds and prints the weekly schedule for a specific faculty ID."""
        rows = {d: {s: ("LUNCH" if s == LUNCH_SLOT else None) for s in TIME_SLOTS} for d in DAYS}
        for d in DAYS:
            for s in TIME_SLOTS:
                for b in self.batches:
                    entry = self.timetable[b.batch_id][d][s]
                    if isinstance(entry, Session) and entry.course.faculty_id == faculty_id:
                        rows[d][s] = f"{b.batch_id} [{entry.room.room_id}]"
                        break
        self.print_grid(f"FACULTY SCHEDULE: {faculty_id}", rows)

    def find_free_rooms(self, day, slot):
        """Displays occupied and unoccupied rooms for a selected day and time slot."""
        if slot == LUNCH_SLOT:
            print(f"\n[{day} | {slot}] -> Protected Lunch Hour (All rooms free).")
            return

        occupied = set()
        for b in self.batches:
            entry = self.timetable[b.batch_id][day][slot]
            if isinstance(entry, Session):
                occupied.add(entry.room.room_id)

        free_list = []
        for r in self.rooms:
            if r.room_id not in occupied:
                free_list.append(f"{r.room_id} ({r.room_type}, Cap {r.capacity})")

        print(f"\n[{day} | {slot}]")
        print(f"  Occupied : {', '.join(sorted(occupied)) or 'None'}")
        print(f"  Free     : {', '.join(free_list) or 'None available'}")

    def build_report(self):
        """Computes slot utilization, average distance penalty, and pointer score."""
        teach_slots_per_day = len(TIME_SLOTS) - 1
        total_batch_slots = len(self.batches) * len(DAYS) * teach_slots_per_day
        total_room_cap = len(self.rooms) * len(DAYS) * teach_slots_per_day

        filled = 0
        day_counts = {d: 0 for d in DAYS}
        room_usage = {r.room_id: 0 for r in self.rooms}
        scores = []
        penalties = []

        for b in self.batches:
            for d in DAYS:
                for s in TIME_SLOTS:
                    entry = self.timetable[b.batch_id][d][s]
                    if isinstance(entry, Session):
                        filled += 1
                        day_counts[d] += 1
                        if entry.room.room_id in room_usage:
                            room_usage[entry.room.room_id] += 1
                        scores.append(entry.score)
                        penalties.append(entry.distance_penalty)

        # Pick busiest day using simple max
        busiest = DAYS[0]
        for d in DAYS:
            if day_counts[d] > day_counts[busiest]:
                busiest = d

        avg_score = (sum(scores) / len(scores)) if scores else 0.0
        avg_penalty = (sum(penalties) / len(penalties)) if penalties else 0.0
        slot_pct = (filled / total_batch_slots * 100) if total_batch_slots else 0.0
        room_pct = (filled / total_room_cap * 100) if total_room_cap else 0.0

        used_rooms_summary = []
        for r_id, hrs in room_usage.items():
            if hrs > 0:
                used_rooms_summary.append(f"{r_id} ({hrs}h)")

        lines = [
            "=== OPTISCHEDULE ANALYTICS REPORT ===",
            f"Batches Scheduled   : {len(self.batches)} batches",
            f"Teaching Slots Used : {filled}/{total_batch_slots} ({slot_pct:.1f}%)",
            f"Campus Room Usage   : {room_pct:.1f}% across {len(self.rooms)} rooms",
            f"Busiest Day         : {busiest} ({day_counts[busiest]} class-hours)",
            f"Avg Decision Score  : {avg_score:.1f} / 100.0",
            f"Avg Distance Penalty: {avg_penalty:.1f} (lower = closer rooms)",
            f"Unscheduled Sessions: {len(self.unscheduled)}",
            "Active Room Hours   : " + (", ".join(used_rooms_summary) or "None"),
        ]
        return "\n".join(lines)

    def export_files(self):
        """Writes the full schedule to CSV and analytics summary to TXT."""
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        csv_path = os.path.join(OUTPUT_DIR, "master_timetable.csv")
        txt_path = os.path.join(OUTPUT_DIR, "schedule_report.txt")

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Batch", "Day", "Time_Slot", "Course_Code", "Faculty", "Room", "Block", "Floor", "Pointer_Score", "Distance_Penalty"])
            for b in self.batches:
                for d in DAYS:
                    for s in TIME_SLOTS:
                        entry = self.timetable[b.batch_id][d][s]
                        if isinstance(entry, Session):
                            writer.writerow([
                                b.batch_id, d, s,
                                entry.course.course_code,
                                entry.course.faculty_id,
                                entry.room.room_id,
                                entry.room.block,
                                entry.room.floor,
                                entry.score,
                                entry.distance_penalty,
                            ])
                        elif entry == "LUNCH":
                            writer.writerow([b.batch_id, d, s, "LUNCH", "-", "-", "-", "-", "-", "-"])
                        else:
                            writer.writerow([b.batch_id, d, s, "FREE", "-", "-", "-", "-", "-", "-"])

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(self.build_report() + "\n")

        return csv_path, txt_path


# ==============================================================================
# SECTION 6: INTERACTIVE CLI APPLICATION (SIMPLE MENU & INPUT VALIDATION)
# ==============================================================================
class TimetableApp:
    """Manages user menus, CSV loading mode, roll-number lookup, and output display."""

    def __init__(self):
        self.all_batches = []
        self.scheduler = None

    def get_positive_int(self, prompt, default):
        """Safely reads a positive integer, falling back to default on bad input."""
        raw = input(prompt).strip()
        if not raw:
            return default
        try:
            val = int(raw)
            if val > 0:
                return val
            print(f"[!] Number must be positive. Using default ({default}).")
            return default
        except ValueError:
            print(f"[!] Invalid number '{raw}'. Using default ({default}).")
            return default

    def pick_item(self, title, items):
        """Displays numbered items and returns the user's choice, or None if invalid."""
        print(f"\n{title}:")
        for idx in range(len(items)):
            print(f"  {idx + 1}. {items[idx]}")
        choice = input(f"Enter number (1-{len(items)}): ").strip()
        if choice.isdigit():
            num = int(choice)
            if 1 <= num <= len(items):
                return items[num - 1]
        print("[!] Invalid selection.")
        return None

    def setup_scheduler(self):
        """Loads CSV files and lets the user choose Cohort Mode or Full Campus Stress Mode."""
        rooms = load_rooms("rooms.csv")
        courses = load_courses("courses.csv")
        self.all_batches = load_batches("batches.csv")

        print("\n=== OPTISCHEDULE SETUP ===")
        print("1. Standard CSV Cohort (Batches B1-B4, 13 Rooms, 8 Courses) [Default]")
        print("2. Full Campus Stress Test (All 24 Batches B1-B24, ~10k Students)")
        print("3. Custom Batch Count from CSV")
        mode = input("Select setup mode (1-3) [Default: 1]: ").strip()

        if mode == "2":
            selected_batches = list(self.all_batches)
        elif mode == "3":
            count = self.get_positive_int(f"How many batches to schedule (1-{len(self.all_batches)})? ", 4)
            selected_batches = self.all_batches[:min(count, len(self.all_batches))]
        else:
            selected_batches = self.all_batches[:4]

        print(f"-> Loaded {len(rooms)} rooms, {len(courses)} courses, and {len(selected_batches)} batches.")
        scheduler = OptiSchedule(rooms, courses, selected_batches)
        scheduler.generate()
        return scheduler

    def lookup_student_roll(self):
        """Finds which batch a student roll number belongs to (E26STU00001..E26STU10000)."""
        roll = input("Enter Student Roll No (e.g., E26STU00450): ").strip().upper()
        for b in self.all_batches:
            if b.contains_roll(roll):
                print(f"[+] Student {roll} belongs to Batch {b.batch_id} ({b.department}, Size: {b.student_count}).")
                if b.batch_id in self.scheduler.timetable:
                    self.scheduler.print_grid(f"TIMETABLE FOR {roll} (BATCH {b.batch_id})", self.scheduler.timetable[b.batch_id])
                else:
                    print(f"[i] Batch {b.batch_id} is not in the currently active schedule subset.")
                return
        print(f"[!] Roll number '{roll}' not found in batches.csv range (E26STU00001 - E26STU10000).")

    def run(self):
        """Runs the main interactive menu loop."""
        print("OptiSchedule | Computational Thinking & Programming (2026CSAE100)")
        self.scheduler = self.setup_scheduler()
        print(f"[+] Schedule generated! Unscheduled sessions: {len(self.scheduler.unscheduled)}")

        while True:
            print("\n1. View Batch Timetable     2. View All Active Batches   3. Faculty Schedule")
            print("4. Find Free Rooms          5. Student Roll Lookup       6. Analytics Report")
            print("7. Export CSV & TXT         8. Change Setup Mode         9. Exit")
            choice = input("Choice (1-9): ").strip()

            if choice == "1":
                batch_ids = [b.batch_id for b in self.scheduler.batches]
                picked = self.pick_item("Select Batch", batch_ids)
                if picked:
                    self.scheduler.print_grid(f"TIMETABLE: BATCH {picked}", self.scheduler.timetable[picked])

            elif choice == "2":
                for b in self.scheduler.batches:
                    self.scheduler.print_grid(f"TIMETABLE: BATCH {b.batch_id}", self.scheduler.timetable[b.batch_id])

            elif choice == "3":
                faculty_list = sorted({c.faculty_id for c in self.scheduler.courses})
                fac = self.pick_item("Select Faculty", faculty_list)
                if fac:
                    self.scheduler.view_teacher_schedule(fac)

            elif choice == "4":
                day = self.pick_item("Select Day", list(DAYS))
                slot = self.pick_item("Select Time Slot", list(TIME_SLOTS)) if day else None
                if slot:
                    self.scheduler.find_free_rooms(day, slot)

            elif choice == "5":
                self.lookup_student_roll()

            elif choice == "6":
                print("\n" + self.scheduler.build_report())

            elif choice == "7":
                c_path, t_path = self.scheduler.export_files()
                print(f"[+] Exported: {c_path} & {t_path}")

            elif choice == "8":
                self.scheduler = self.setup_scheduler()
                print(f"[+] Regenerated! Unscheduled sessions: {len(self.scheduler.unscheduled)}")

            elif choice == "9":
                print("Goodbye!")
                break

            else:
                print("[!] Enter a valid option (1-9).")


if __name__ == "__main__":
    app = TimetableApp()
    app.run()
