import logging
import sys
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
import datetime
from ortools.constraint_solver import pywrapcp

### Time frame
month = 2
SCHEDULE_START = datetime.datetime(year=2018, month=month, day=1)
SCHEDULE_END = datetime.datetime(year=2018, month=month+1, day=1) - datetime.timedelta(days=1)
WEEKDAYS = ['Sunday','Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
EMPLOYEES = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']

### Schedule features
SHIFTS =['Off','10-4','10-2','10-5','10-6','11-7',
        '12-5','12-6','12-7','12-8','1-8','2-7',
        '3-7','3-8','4-8','On call']

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

def get_weekday(day, start):
    date = start + datetime.timedelta(days=day)
    daynum = date.weekday()
    weekday = WEEKDAYS[daynum]
    return weekday, daynum

def get_date(day, start):
    date = start + datetime.timedelta(days=day)
    return date.strftime('%m-%d-%Y')

def main():

    solver = pywrapcp.Solver("schedule_shifts")

    # Time frame and ranges
    start = SCHEDULE_START
    end = SCHEDULE_END
    num_days = (end - start).days + 1
    all_days = range(num_days)

    num_shifts = len(SHIFTS)
    all_shifts = range(num_shifts)

    num_employees = len(EMPLOYEES)
    all_employees = range(num_employees)

    work = []
    for emp in all_employees:
        t = []
        for day in all_days:
            # To make into a matrix of decision variables:
            t.append(solver.IntVar(0, num_shifts-1, 'work[%i][%i]' % (emp,day)))
        work.append(t)

    # Specify schedule constraints
    needs = []
    for weekday in SCHEDULE:
        t = []
        for shift in SHIFTS:
            shifts = [sft['Hours'] for sft in SCHEDULE[weekday]]
            try:
                ix = shifts.index(shift)
                staff_required = SCHEDULE[weekday][ix]['Staff']
                t.append(staff_required)
            except:
                logging.debug('Shift {} not needed on {}'.format(shift, weekday))
                t.append(0)
        needs.append(t)

    # Add schedule constraints
    for day in all_days:
        date = get_date(day, start)
        weekday, daynum = get_weekday(day, start)
        logging.info('Processing day {}, {}, {}'.format(day+1, weekday, date))

        for shift in all_shifts:
            if needs[daynum][shift]:
                logging.debug('On {} {}, shift {} needs {} staff'.format(weekday, date, shift, needs[daynum][shift]))
                solver.Add(solver.Sum(work[emp][day] == shift for emp in all_employees) == needs[daynum][shift])

    ###

    logging.info('Problem setup complete')
    logging.info('Starting to solve')

    db = solver.Phase([work[i][j] for i in all_employees for j in all_days],
                        solver.CHOOSE_FIRST_UNBOUND,
                        solver.ASSIGN_MIN_VALUE)

    solution = solver.Assignment()
    solution.Add([work[i][j] for i in all_employees for j in all_days])
    collector = solver.AllSolutionCollector(solution)

    solutionsLimit = solver.SolutionsLimit(10)
    timeLimit = solver.TimeLimit(10000)

    logging.info('Trying to solve')
    solver.Solve(db, [collector, solutionsLimit, timeLimit])
    num_solutions = collector.SolutionCount()

    logging.info('Solutions found: {}'.format(num_solutions))
    logging.info('Time: {}'.format(solver.WallTime(), 'ms'))
    logging.info('Failures: {}'.format(solver.Failures()))
    logging.info('Branches: {}'.format(solver.Branches()))

if __name__ == 'main':
    main()
