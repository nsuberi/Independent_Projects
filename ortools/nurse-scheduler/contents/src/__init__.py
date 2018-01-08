import logging
import sys
import pandas as pd
import datetime
import random
import json
from collections import OrderedDict, defaultdict

from ortools.constraint_solver import pywrapcp

### Constants
POSSIBLE_SHIFTS = 'https://docs.google.com/spreadsheets/d/1K6dIZxpEvUcGZ9XxjaHs-_z086qdm6ReTFI9kCxiitQ/export?format=tsv'
REQUESTS_OFF = 'https://docs.google.com/spreadsheets/d/1gK6ETUrM5Ft72iLtACXDtHVWwQgninU63I0JR95ZDCc/export?format=tsv'
LOG_LEVEL = logging.DEBUG
global EMPLOYEES

### Time frame
month = 2
SCHEDULE_START = datetime.datetime(year=2018, month=month, day=1)
SCHEDULE_END = datetime.datetime(year=2018, month=month+1, day=1) - datetime.timedelta(days=1)
WEEKDAYS = ['Sunday','Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

### Schedule features
SHIFTS = OrderedDict([
    ('Off',[0,0]),
    ('10-4',[10,16]),
    ('10-2',[10,14]),
    ('10-5',[10,17]),
    ('10-6',[10,18]),
    ('11-7',[11,19]),
    ('12-5',[12,17]),
    ('12-6',[12,18]),
    ('12-7',[12,19]),
    ('12-8',[12,20]),
    ('1-8',[13,20]),
    ('2-7',[14,19]),
    ('3-7',[15,19]),
    ('3-8',[15,20]),
    ('4-8',[16,20]),
    ('On call',[None, None])
])

SCHEDULE = {
            'Sunday':[{
                    'Hours':'12-5',
                    'Staff':3
                },{
                    'Hours':'On call',
                    'Staff':1
                }],
            'Monday':[{
                    'Hours':'10-4',
                    'Staff':2
                },{
                    'Hours':'11-7',
                    'Staff':1
                },{
                    'Hours':'3-7',
                    'Staff':1
                }],
            'Tuesday':[{
                    'Hours':'10-4',
                    'Staff':2
                },{
                    'Hours':'11-7',
                    'Staff':1
                },{
                    'Hours':'2-7',
                    'Staff':1
                }],
            'Wednesday':[{
                    'Hours':'10-4',
                    'Staff':1
                },{
                    'Hours':'10-6',
                    'Staff':1
                },{
                    'Hours':'11-7',
                    'Staff':1
                },{
                    'Hours':'12-7',
                    'Staff':1
                }],
            'Thursday':[{
                    'Hours':'10-5',
                    'Staff':1
                },{
                    'Hours':'10-6',
                    'Staff':1
                },{
                    'Hours':'11-7',
                    'Staff':1
                },{
                    'Hours':'12-7',
                    'Staff':1
                }],
            'Friday':[{
                    'Hours':'10-4',
                    'Staff':1
                },{
                    'Hours':'10-6',
                    'Staff':1
                },{
                    'Hours':'11-7',
                    'Staff':1
                },{
                    'Hours':'12-8',
                    'Staff':1
                },{
                    'Hours':'3-8',
                    'Staff':1
                }],
            'Saturday':[{
                    'Hours':'10-6',
                    'Staff':2
                },{
                    'Hours':'11-7',
                    'Staff':1
                },{
                    'Hours':'1-8',
                    'Staff':1
                },{
                    'Hours':'4-8',
                    'Staff':1
                },{
                    'Hours':'On call',
                    'Staff':1
                }]
        }

CONSTRAINTS = {
    'Not more than 5 days in a row',
    'Not more than 40 hours a week',
    'Not less than 30 hours a week for full time',
    'Each employee only assigned to one shift a day'
}

###
## Accessing remote data
###

def fetchEmployeeInformation():
    """
    Select the appropriate file from FTP to download data from
    """
    global EMPLOYEES

    ### Possible shifts
    possible_shifts = pd.read_csv(POSSIBLE_SHIFTS, sep="\t", header=0, index_col=[0])
    possible_shifts = possible_shifts.replace(pd.np.nan, '')
    logging.info(possible_shifts)

    #### Requests off
    requests_off = pd.read_csv(REQUESTS_OFF, sep="\t", header=0, index_col=None)
    logging.info(requests_off)

    ### Extract contact info
    contact_info = possible_shifts[['Phone', 'Email']]
    EMPLOYEES = possible_shifts.index.tolist()

    return possible_shifts, requests_off, contact_info

def len_shift(hours):
    try:
        return(hours[1]-hours[0])
    except:
        return('On Call')

def get_weekday(day, start):
    date = start + datetime.timedelta(days=day)
    daynum = date.weekday()
    weekday = WEEKDAYS[daynum]
    return weekday, daynum

def get_date(day, start):
    date = start + datetime.timedelta(days=day)
    return date.strftime('%m-%d-%Y')

def format_days_off(requests_off):
    res = defaultdict(list)
    for _, row in requests_off.iterrows():
        emp = row['Name']
        day_off = datetime.datetime.strptime(row['Date'], '%m/%d/%Y').strftime('%m-%d-%Y')

        if emp == 'ALL':
            for emp_name in EMPLOYEES:
                res[day_off].append(emp_name)
        else:
            res[day_off].append(emp)
    return res

def createPossibleSchedule(possible_shifts, requests_off):
    # Create a calendar representation showing staff and times they state they can/can't work
    start = SCHEDULE_START
    end = SCHEDULE_END
    num_days = (end - start).days

    requested_days_off = format_days_off(requests_off)

    day = 0
    schedule = {}
    while day < num_days:
        day_schedule = defaultdict(list)
        date = get_date(day, start)
        weekday, daynum = get_weekday(day, start)
        logging.info('Processing date {}, a {}'.format(date, weekday))

        ### All necessary shifts are covered
        needed_shifts = SCHEDULE[weekday]
        for shift in needed_shifts:
            hours = shift['Hours']
            staff_needed = shift['Staff']

            for emp in EMPLOYEES:
                # Did employee ask for the day off?
                asked_off = False
                if emp in requested_days_off[date]:
                    asked_off = True

                # Did employee indicate they're available at this time?
                available = False
                employee_availability = possible_shifts.loc[emp, weekday]
                if hours in employee_availability:
                    available = True

                if available and not asked_off:
                    day_schedule[hours].append(emp)

        # Move on to next day
        day += 1
        schedule[' '.join([date,weekday])] = day_schedule

    return schedule

# https://github.com/google/or-tools/blob/master/examples/python/assignment.py
def createScheduleMatrixFromJson():
    x = []
    for day in SCHEDULE:
        t = []
        for shift in SHIFTS:
            shifts = [sft['Hours'] for sft in SCHEDULE[day]]
            if shift in shifts:
                staff_required = SCHEDULE[day][shifts.index(shift)]['Staff']
                t.append(staff_required)
            else:
                t.append(0)
        x.append(t)
    x_flat = [x[i][j] for i in range(len(SCHEDULE)) for j in range(len(SHIFTS))]
    return x, x_flat

def createVariableMatrix(rows, columns, solver, choices=1):
    '''
    Inputs: ranges for rows and columns
    Outputs:
    '''
    all_rows = range(rows)
    all_columns = range(columns)
    x = []
    for i in all_rows:
        t = []
        for j in all_columns:
            # To make into a matrix of decision variables:
            t.append(solver.IntVar(0, choices-1, 'x[%i,%i]' % (i,j) ))
        x.append(t)
    x_flat = [x[i][j] for i in all_rows for j in all_columns]
    x_rows = [x[i] for i in all_rows]
    return x, x_flat, x_rows

def setupAndSolveNSP(possible_shifts, requests_off):
    solver = pywrapcp.Solver("schedule_shifts")

    # Time frame
    start = SCHEDULE_START
    end = SCHEDULE_END
    num_days = (end - start).days + 1
    all_days = range(num_days)

    num_shifts = len(SHIFTS)
    all_shifts = range(num_shifts)

    num_employees = len(EMPLOYEES)
    all_employees = range(num_employees)

    # Create shift variables
    shifts = {}

    # for emp in all_employees:
    #     for day in all_days:
    #         shifts[(emp, day)] = solver.IntVar(0, num_shifts - 1, "Emp %i on day %i" % (emp, day))
    # shifts_flat = [shifts[(emp, day)] for emp in all_employees for day in all_days]

    shifts, shifts_flat, shifts_rows = createVariableMatrix(num_employees, num_days, solver, num_shifts)

    # Create employee variables
    # employees = {}
    #
    # for shift in range(num_shifts):
    #     for day in range(num_days):
    #         employees[(shift, day)] = solver.IntVar(0, num_employees - 1, "shift%d day%d" % (shift,day))

    # Set relationships between shifts and employees.
    # for day in range(num_days):
    #     employees_for_day = [employees[(shift, day)] for shift in range(num_shifts)]
    #     for emp in range(num_employees):
    #         s = shifts[(emp, day)]
    #         solver.Add(s.IndexOf(employees_for_day) == emp)

    # Set up contraints

    ## Each employee works only 1 shift a day
    ### THIS CAUSES NO SOLUTIONS TO BE FOUND... WHY?!
    ### It is unnecessary anyway, because of the dual formulation... no way a nurse can be assigned to more than one shift in a day
    # for day in range(num_days):
    #     for emp in range(num_employees):
    #         solver.Add(solver.Sum([employees[(shift, day)] == emp for shift in range(num_shifts)]) == 1)
    #
    # more compact:
    #[solver.Add(solver.Sum(employees[(shift, day)] == emp for shift in range(num_shifts)) == 1) for emp in range(num_employees) for day in range(num_days)]

    ### Each employee works between 3 and 6 days a week
    # Current formulation assumes 4 weeks in a month
    # for emp in range(num_employees):
    #     # Could include here some measure of a week,
    #     # adding multiple constraints for each employee corresponding to each week they work
    #     # That way would remove the *4 in constraints below
    #     solver.Add(solver.Sum([shifts[(emp, day)] > 0 for day in range(num_days)]) >= 1*4)
    #     solver.Add(solver.Sum([shifts[(emp, day)] > 0 for day in range(num_days)]) <= 6*4)

    ### Constraints based on store needs and staff availability

    ### Not possible to assign staff if they've asked off a particular day
    # for _, row in requests_off.iterrows():
    #     emp_name = row['Name']
    #     day_off = (datetime.datetime.strptime(row['Date'], '%m/%d/%Y') - start).days
    #
    #     if emp_name == 'ALL':
    #         for emp in range(num_employees):
    #             solver.Add(shifts[(emp, day_off)]==0)
    #     else:
    #         emp = EMPLOYEES.index(emp_name)
    #         solver.Add(shifts[(emp, day_off)]==0)

    # ### Not possible to assign staff if they're not available that shift
    # for weekday in WEEKDAYS:
    #     for emp in range(num_employees):
    #         emp_name = EMPLOYEES[emp]
    #         employee_availability = possible_shifts.loc[emp_name, weekday]
    #         logging.debug('Employee availability: {}'.format(employee_availability))
    #         # Don't restrict employees from taking time off, 0 shift
    #         for shift in range(1,num_shifts):
    #             shift_ = list(SHIFTS.keys())[shift]
    #             logging.debug('Adding constraints for emp {} in shift {}'.format(emp, shift_))
    #             if shift_ not in employee_availability:
    #                 # Restrict constraint to only the specific weekdays being considered at moment
    #                 for day in range(num_days):
    #                     if get_weekday(day, start)[0] == weekday:
    #                         logging.debug('Adding constraint: emp {} can\'t work shift {} on {}'.format(emp_name, shift_, weekday))
    #                         solver.Add(shifts[(emp, day)] != shift)

    for day in all_days:
        date = get_date(day, start)
        weekday, daynum = get_weekday(day, start)
        logging.info('Processing day {} of {}, {}, {}'.format(day+1, num_days, weekday, date))

        ### All necessary shifts are covered

        needs, needs_flat = createScheduleMatrixFromJson()
        # This below requires that some people never get assigned to any shift, including the "off" shift
        #[solver.Add(solver.Sum(shifts[emp][day] == shift for emp in all_employees) >= needs[daynum][shift])
        #for shift in all_shifts]

        for shift in all_shifts:
            if needs[daynum][shift]:
                solver.Add(solver.Sum(shifts[emp][day] == shift for emp in all_employees) >= needs[daynum][shift])

        # needed_shifts = SCHEDULE[weekday]
        # for shift in needed_shifts:
        #     hours = shift['Hours']
        #     shift_ = list(SHIFTS.keys()).index(hours)
        #     staff_needed = shift['Staff']
        #
        #     logging.debug('Shift {}, hours {}, {} staff needed'.format(shift_, hours, staff_needed))
        #     #solver.Add(solver.Sum(shifts[(emp, day)] == shift_ for emp in all_employees) >= staff_needed)
        #     solver.Add(solver.Sum(shifts[emp][day] == shift_ for emp in all_employees) >= staff_needed)

    ### Maximize number of people who are off
    # How to do?

    # For each shift (other than 0), at most 2 nurses are assigned to that shift
    # during the week.
    # works_shift = {}
    # for emp in range(num_employees):
    #     for shift in range(num_shifts):
    #         works_shift[(emp, shift)] = solver.BoolVar('shift%d employee%d' % (emp, shift))
    #
    # for emp in range(num_employees):
    #     for shift in range(num_shifts):
    #         solver.Add(works_shift[(emp, shift)] == solver.Max([shifts[(emp, day)] == shift for day in range(num_days)]))
    #
    # for shift in range(1, num_shifts):
    #     solver.Add(solver.Sum([works_shift[(emp, shift)] for emp in range(num_employees)]) <= 2)

    logging.info('Problem setup complete')
    logging.info('Starting to solve')

    db = solver.Phase(shifts_flat,
                        solver.CHOOSE_FIRST_UNBOUND,
                        solver.ASSIGN_MIN_VALUE)

    # Create the solution collector.
    solution = solver.Assignment()
    solution.Add(shifts_flat)
    #solution.Add(shifts_rows)
    #collector = solver.AllSolutionCollector(solution)
    collector = solver.FirstSolutionCollector(solution)

    # http://daft.engineer/hacks-and-kludges/stumbling-through-or-tools/
    # lim = solver.Limit(60000, # time
    #                    123400,  # branches
    #                    567800,  # failures
    #                    10,     # solutions
    #                    True,  # smart_time_check, minimizes calls to walltime()
    #                    True)  # cumulative, i.e. are these global limits?
    solutionsLimit = solver.SolutionsLimit(10)
    timeLimit = solver.TimeLimit(10000)

    logging.info('Trying to solve')
    solver.Solve(db, [collector, solutionsLimit, timeLimit])
    num_solutions = collector.SolutionCount()

    logging.info('Solutions found: {}'.format(num_solutions))
    logging.info('Time: {}'.format(solver.WallTime(), 'ms'))
    logging.info('Failures: {}'.format(solver.Failures()))
    logging.info('Branches: {}'.format(solver.Branches()))
    #logging.info(shifts)

    sol = random.randrange(num_solutions)
    for day in all_days:
        logging.info('Day: {}'.format(day))
        for emp in all_employees:
            shift = collector.Value(sol, shifts[(emp, day)])
            logging.info('Employee {} assigned to task {}'.format(emp, shift))
        logging.info('')

    return collector, num_solutions

def visualizeSchedule(schedule):
    '''
    Loop over solutions, put in a DataFrame with
    columns=days, rows=staff, values=shift
    '''
    logging.info(schedule)
    pass

def promptForEdits(calendar):
    pass

def distributeCalendar(calendar, contacts):
    phones = contacts['Phone']
    emails = contacts['Email']

    for phone in phones:
        logging.info('Sending sms with picture')
    for email in emails:
        logging.info('Sending email with picture')

###
## Application code
###

def main():
    logging.basicConfig(stream=sys.stderr, level=LOG_LEVEL)

    ### 0. Observe schedule
    sched, flat_sched = createScheduleMatrixFromJson()
    logging.info(sched)

    ### 1. Retrieve employee availability
    possible_shifts, requests_off, contacts = fetchEmployeeInformation()

    ### 2. Create a schedule description showing availability
    schedule = createPossibleSchedule(possible_shifts, requests_off)

    with open('data/schedule.json', 'w') as f:
        json.dump(dict(schedule), f, indent=4)

    ### 3. Calculate hours of the schedule


    ### 2. Construct scheduling constraints given availability and schedule timeframe
    solution_collector = setupAndSolveNSP(possible_shifts, requests_off)

    ### 3. Visualize schedule
    #calendar = visualizeSchedule(solution_collector)

    ### 4. Prompt for edits
    #calendar = promptForEdits(calendar)

    ### 5. Send schedule out as email and/or sms, store in Carto table
    #distributeCalendar(calendar, contacts)
