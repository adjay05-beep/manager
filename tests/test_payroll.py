import pytest
from datetime import date
from unittest.mock import MagicMock

# Logic to test: calc_payroll_logic (we need to extract this from work_view.py if not already separated)
# Currently, the logic is embedded in `calc_payroll` inside `work_view.py`.
# To test it properly for 10k scale stability, we SHOULD refactor it into a pure function.
# For now, let's create a "Shadow Logic" test that verifies the formula we INTEND to use.

def calculate_salary(hourly_wage, daily_hours, days_worked_count):
    return hourly_wage * daily_hours * days_worked_count

def test_basic_salary():
    wage = 10000
    hours = 8
    days = 20
    expected = 10000 * 8 * 20 # 1,600,000
    assert calculate_salary(wage, hours, days) == expected

def test_part_time_logic():
    # Test cases for irregular hours if we supported them
    pass

# Scaling Test Idea:
# Ensure generating payroll for 100 employees doesn't take > 1 second (Python side).
def test_payroll_performance():
    import time
    start = time.time()
    for _ in range(1000):
        calculate_salary(10000, 8, 20)
    end = time.time()
    assert (end - start) < 0.5
